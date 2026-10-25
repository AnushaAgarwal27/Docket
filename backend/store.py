"""Transactional student file; operation names remain stable for existing agents.

One SQLite database, JSON documents with indexed relation keys, WAL and BEGIN IMMEDIATE
for atomic case claims, idempotent writes and state transitions across agent processes.
"""
from __future__ import annotations
import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

TABLES = {'profiles','transactions','paystubs','sources','flags','hearings','cases','calls','activity','files'}
NEXT = {'open':['awaiting_approval'], 'awaiting_approval':['contacting_employer','closed'],
        'contacting_employer':['awaiting_response','written_request','escalate_irs'],
        'written_request':['contacting_employer','escalate_irs','closed'],
        'awaiting_response':['refund_received','contacting_employer','escalate_irs'],
        'refund_received':['closed'], 'escalate_irs':['closed'], 'closed':[]}

def now(): return datetime.now(timezone.utc).isoformat()
def in_days(n): return (date.today()+timedelta(days=n)).isoformat()
def db_path(): return Path(os.environ.get('DOCKET_DB_PATH','data/docket.sqlite3')).resolve()
def files_path():
    p = db_path().parent / 'files'
    p.mkdir(parents=True, exist_ok=True)
    return p

@contextmanager
def connection(write=False):
    path=db_path(); path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=15)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS documents (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, collection TEXT NOT NULL, profile_id TEXT, relation TEXT, body TEXT NOT NULL)')
    db.execute('CREATE INDEX IF NOT EXISTS profile_lookup ON documents(collection,profile_id,seq)')
    db.execute('CREATE INDEX IF NOT EXISTS relation_lookup ON documents(collection,relation,seq)')
    db.commit()
    try:
        db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
        yield Store(db)
        db.commit()
    except Exception:
        db.rollback(); raise
    finally: db.close()

class Store:
    def __init__(self, db): self.db=db
    def get(self, id):
        row=self.db.execute('SELECT body FROM documents WHERE id=?',(id,)).fetchone()
        return json.loads(row[0]) if row else None
    def require(self,id,table=None):
        row=self.get(id)
        if row is None or (table and not id.startswith(table+'_')): raise ValueError('Record not found')
        return row
    def rows(self, table, *, profile=None, relation=None, reverse=False, limit=1000):
        if table not in TABLES: raise ValueError('Unknown collection')
        sql='SELECT body FROM documents WHERE collection=?'; params=[table]
        for key,value in [('profile_id',profile),('relation',relation)]:
            if value is not None: sql+=f' AND {key}=?'; params.append(value)
        sql+=' ORDER BY seq '+('DESC' if reverse else 'ASC')+' LIMIT ?'; params.append(min(max(int(limit),0),5000))
        return [json.loads(r[0]) for r in self.db.execute(sql,params)]
    def put(self,table,data,id=None):
        if table not in TABLES: raise ValueError('Unknown collection')
        data=dict(data)
        for key,value in data.items():
            if key.endswith('Cents') and (type(value) is not int): raise ValueError(f'{key} must be integer cents')
        if id:
            old=self.require(id,table); data={'_id':id,'_creationTime':old['_creationTime'],**data}
        else: id=table+'_'+uuid.uuid4().hex; data={**data,'_id':id,'_creationTime':int(time.time()*1000)}
        relation={'sources':'url','transactions':'nessieId','paystubs':'sourceFile','cases':'flagId','calls':'caseId','hearings':'flagId','files':'storageId'}.get(table)
        self.db.execute('INSERT INTO documents(id,collection,profile_id,relation,body) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET profile_id=excluded.profile_id,relation=excluded.relation,body=excluded.body',
                        (id,table,data.get('profileId'),data.get(relation) if relation else None,json.dumps(data)))
        return id
    def patch(self,id,**fields):
        old=self.require(id); return self.put(id.split('_')[0],{**old,**fields},id)
    def log(self,agent,action,detail,**extra): return self.put('activity',dict(agent=agent,action=action,detail=detail,at=now(),**extra))
    def transition(self,c,to,detail,**fields):
        if to not in NEXT.get(c['state'],[]): raise ValueError(f"Cannot move case from {c['state']} to {to}")
        self.patch(c['_id'],state=to,**fields)
        self.log('caseworker','case_'+to,detail,inputIds=[c['_id']])
    def snapshot(self,pid):
        p=self.get(pid)
        if p is None: return None
        flags=[]
        for f in self.rows('flags',profile=pid,limit=50):
            source=self.get(f['sourceId']) or {}
            flags.append({**f,'sourceTitle':source.get('title'),'sourceUrl':source.get('url'),'sourceFetchedAt':source.get('fetchedAt'),'sourceHash':source.get('hash')})
        cases=[{**c,'calls':self.rows('calls',relation=c['_id'],reverse=True,limit=10)} for c in self.rows('cases',profile=pid,limit=50)]
        return dict(profile=p,flags=flags,cases=cases,paystubs=self.rows('paystubs',profile=pid,limit=100),transactions=self.rows('transactions',profile=pid,reverse=True,limit=50))
    def file_url(self,f): return {**f,'url':'/api/files/'+f['storageId']}
    def receipt(self,fid):
        flag=self.get(fid)
        if not flag: return None
        own=[f for f in self.rows('files') if f.get('flagId')==fid]
        stubs=[]
        for pid in flag.get('paystubIds',[]):
            p=self.get(pid) or {}
            stubs += [{**self.file_url(f),'periodStart':p.get('periodStart')} for f in self.rows('files') if f.get('paystubId')==pid]
        return {'letters':[self.file_url(f) for f in own if f['kind']=='letter'], 'forms':[self.file_url(f) for f in own if f['kind']=='form'], 'paystubs':sorted(stubs,key=lambda x:x.get('periodStart') or '')}
    def query(self,name,a):
        table,op=name.split(':',1)
        if name=='dashboard:snapshot': return self.snapshot(a['profileId'])
        if name=='files:forFlag': return self.receipt(a['flagId'])
        if name=='activity:recent': return self.rows('activity',reverse=True,limit=a.get('limit',50))
        if name=='sources:getByUrl': return next(iter(self.rows('sources',relation=a['url'])),None)
        if name=='sources:cite':
            s=self.get(a['sourceId']); return {k:s[k] for k in ['title','url']} if s else None
        if name=='hearings:latestForProfile': return self.rows('hearings',profile=a['profileId'],reverse=True,limit=a.get('limit',10))
        if name=='hearings:latestForFlag': return next(iter(self.rows('hearings',relation=a['flagId'],reverse=True,limit=1)),None)
        if name=='cases:awaitingCall': return [c for c in self.rows('cases') if c['state']=='contacting_employer' and not c.get('callRequestedAt')][:20]
        if name=='cases:awaitingLetter': return [c for c in self.rows('cases') if c['state']=='written_request' and not c.get('writtenRequest')][:20]
        if name=='timeline:forProfile': return self.timeline(a['profileId'],a['today'])
        if name=='patterns:byEmployer': return self.patterns()
        if op=='get' and table in TABLES: return self.get(a[{'profiles':'profileId','cases':'caseId','sources':'sourceId'}[table]])
        if op=='list' and table=='profiles': return self.rows('profiles',limit=50)
        if op=='listByProfile' and table in TABLES: return self.rows(table,profile=a['profileId'])
        raise ValueError('Unknown query '+name)
    def mutation(self,name,a):
        table,op=name.split(':',1)
        if name=='activity:log': return self.log(**a)
        if name=='seed:resetDemo':
            for t in TABLES-{'sources'}: self.db.execute('DELETE FROM documents WHERE collection=?',(t,))
            pid=self.put('profiles',a['profile']); self.log('seed','reset_demo','Synthetic student file initialized',outputIds=[pid]); return pid
        if name=='seed:addSimulatedStudent': return self.put('profiles',{**a['profile'],'simulated':True})
        if name=='profiles:updateFromForm':
            fields={k:v for k,v in a.items() if k!='profileId'}
            allowed={'arrivalDate','visa','employer','employmentType','employerIsSchool','enrolled','preferredLanguage'}
            if set(fields)-allowed: raise ValueError('Unsupported profile field')
            self.patch(a['profileId'],**fields); self.log('coordinator','profile_updated','Profile updated',inputIds=[a['profileId']]); return list(fields)
        if name in {'sources:upsert','transactions:upsert','paystubs:record','flags:upsert'}:
            if table=='sources': match=self.rows(table,relation=a['url'])
            elif table=='transactions': match=self.rows(table,relation=a['nessieId'])
            else: match=[r for r in self.rows(table,profile=a['profileId']) if r['sourceFile' if table=='paystubs' else 'ruleId']==a['sourceFile' if table=='paystubs' else 'ruleId']]
            old=next(iter(match),None)
            if table=='transactions' and old: return {'id':old['_id'],'created':False}
            data={**a}
            if old and table=='flags': data['status']=old['status']
            id=self.put(table,data,old['_id'] if old else None)
            return {'id':id,'created':True} if table=='transactions' else id
        if name=='flags:setStatus': self.patch(a['flagId'],status=a['status']); return None
        if name=='hearings:record':
            hid=self.put('hearings',{**a,'createdAt':now()})
            f=self.get(a.get('flagId',''))
            if f and f['status'] in ['contested','open','needs_student_ok','needs_review','defeated']:
                self.patch(f['_id'],status={'upheld':'open','downgraded':'needs_student_ok','needs_human':'needs_review','defeated':'defeated'}[a['verdict']])
            self.log('auditor','verdict_'+a['verdict'],a['reason'],outputIds=[hid]); return hid
        if name=='files:attach':
            storage=a['storageId']
            if not (files_path()/storage).is_file(): raise ValueError('Stored file not found')
            if a['kind'] not in ['paystub','letter','form']: raise ValueError('Invalid file kind')
            for f in self.rows('files'):
                if f['kind']==a['kind'] and any(a.get(k) and f.get(k)==a[k] for k in ['flagId','paystubId']): self.db.execute('DELETE FROM documents WHERE id=?',(f['_id'],))
            return self.put('files',{**a,'createdAt':now()})
        if name=='cases:open':
            existing=self.rows('cases',relation=a['flagId'])
            if existing: return existing[0]['_id']
            f=self.require(a['flagId'],'flags'); self.require(a['profileId'],'profiles')
            if f['profileId']!=a['profileId'] or f['status']!='open' or f['amountCents']!=a['amountCents']: raise ValueError('Flag is not eligible for a case')
            cid=self.put('cases',{**a,'state':'open','nextFollowUp':in_days(1)})
            self.patch(a['flagId'],status='case_opened');self.transition(self.require(cid),'awaiting_approval','Request ready for review'); return cid
        if table=='cases': return self.case_mutation(op,a)
        raise ValueError('Unknown mutation '+name)
    def case_mutation(self,op,a):
        c=self.require(a['caseId'],'cases'); cid=c['_id']
        if op in ['approve','decline']:
            if c['state']!='awaiting_approval': raise ValueError('Case is not awaiting approval')
            if op=='approve':
                f=self.require(c['flagId'],'flags')
                if f['status'] not in ['open','case_opened']: raise ValueError('Finding is on hold or not actionable')
                self.patch(cid,approvedAt=now()); self.transition(c,'contacting_employer','Student approved; contacting payroll',nextFollowUp=in_days(1))
            else: self.transition(c,'closed','Student declined contact',outcome='declined_by_student')
        elif op=='claimCall':
            if c['state']!='contacting_employer' or c.get('callRequestedAt'): return False
            f=self.require(c['flagId'],'flags')
            if f['status'] not in ['open','case_opened']: return False
            self.patch(cid,callRequestedAt=now(),callAttempts=c.get('callAttempts',0)+1); return True
        elif op=='recordCallStart':
            if a.get('error'): self.patch(cid,callError=a['error'])
            else: self.patch(cid,callRequestId=a.get('callRequestId'))
            self.log('voice','call_failed' if a.get('error') else 'call_placed',a.get('error') or ('Rehearsal: no phone call placed' if a.get('simulated') else 'Cartesia call started'),inputIds=[cid])
        elif op=='setPayrollScript':
            if a['script'] not in ['cooperate','stall_once','refuse_once']: raise ValueError('Invalid script')
            self.patch(cid,payrollScript=a['script'])
        elif op=='recordWrittenRequest':
            if c['state']!='written_request': raise ValueError('Not awaiting a written request')
            if not c.get('writtenRequest'):
                self.patch(cid,writtenRequest=a['text'],writtenRequestAt=now()); self.log('caseworker','written_request_prepared','Written request prepared for student to send',inputIds=[cid])
        elif op=='followUp':
            if c['state']!='written_request' or not c.get('writtenRequest'): raise ValueError('No written request to follow up')
            self.patch(cid,callRequestedAt=None,callRequestId=None,callError=None)
            self.transition(c,'contacting_employer','Student requested phone follow-up',nextFollowUp=in_days(1))
        elif op=='logCallOutcome':
            result=a['result']
            if result not in ['promised','stalled','refused','needs_student']: raise ValueError('Invalid outcome')
            # Repeated tool submissions never create duplicate outcomes or callbacks.
            request=c.get('callRequestId') or c.get('callRequestedAt')
            previous=[r for r in self.rows('calls',relation=cid) if r.get('requestKey')==request]
            if previous: return previous[0]['_id']
            if c['state']!='contacting_employer' or not request: raise ValueError('No active approved call')
            if not isinstance(a.get('summary'),str) or not a['summary'].strip(): raise ValueError('Summary required')
            if a.get('promisedBy'): date.fromisoformat(a['promisedBy'])
            call={k:v for k,v in a.items() if k!='caseId'}
            callid=self.put('calls',{**call,'caseId':cid,'requestKey':request,'at':now()})
            if result in ['stalled','refused']:
                to='written_request' if c.get('callAttempts',1)<2 else 'escalate_irs'
                self.transition(c,to,'Payroll '+result+'; student review required for next steps',nextFollowUp=in_days(3))
            else: self.transition(c,'awaiting_response','Payroll '+result,nextFollowUp=a.get('promisedBy') or in_days(2 if result=='needs_student' else 14))
            return callid
        elif op=='refundReceived':
            t=self.require(a['transactionId'],'transactions')
            if t['profileId']!=c['profileId'] or abs(t['amountCents']-c['amountCents'])>100 or t['kind']!='deposit': raise ValueError('Refund does not match case')
            self.transition(c,'refund_received','Refund deposit matched')
            self.patch(c['flagId'],status='resolved');self.transition(self.require(cid),'closed','Refund recorded; case closed',outcome='refunded')
        else: raise ValueError('Unknown case operation '+op)
        return None
    def timeline(self,pid,today):
        snap=self.snapshot(pid)
        if not snap: return None
        p=snap['profile']; year=int(today[:4]); arrival=int(p['arrivalDate'][:4]); events=[]
        def event(d,t,detail,tone='info',up=False): events.append(dict(date=d,title=t,detail=detail,tone=tone,upcoming=up))
        event(p['arrivalDate'],'Student file begins',p['visa']+' arrival date on record')
        for filing in p.get('filings',[]): event(f"{filing['year']}-12-31",'Form '+filing['form']+' on record','Filing year '+str(filing['year']),'done')
        for f in snap['flags']: event(datetime.fromtimestamp(f['_creationTime']/1000,timezone.utc).isoformat(),f['ruleId'],f['explanation'],'done' if f['status']=='resolved' else 'warn')
        for c in snap['cases']:
            for call in c['calls']: event(call['at'],'Office call',call['summary'])
            if c.get('writtenRequestAt'): event(c['writtenRequestAt'],'Written request prepared','For the student to review and send')
            if c['state'] not in ['closed','escalate_irs']: event(c['nextFollowUp'],'Case follow-up','Recorded next step; not a confirmed call appointment','next',True)
        next_season=dict(date=f'{year+1}-01-01',title='Review next season',detail='Confirm changed facts and applicable official filing instructions before setting deadlines.')
        return dict(events=sorted(events,key=lambda x:x['date']),nextSeason=next_season,calendarYear=year-arrival+1,lastExemptYear=arrival+4)
    def patterns(self):
        groups={}
        for p in self.rows('profiles',limit=50):
            stubs=self.rows('paystubs',profile=p['_id']); flags=self.rows('flags',profile=p['_id']); f=next((f for f in flags if f['ruleId']=='FICA_EXEMPT_F1'),None)
            for employer in set(s['employer'] for s in stubs):
                g=groups.setdefault(employer,dict(employer=employer,students=0,flagged=0,withheldCents=0,simulated=0))
                g['students']+=1;g['simulated']+=int(bool(p.get('simulated')))
                if f: g['flagged']+=1;g['withheldCents']+=f['amountCents']
        rows=sorted([{**g,'pattern':g['flagged']>=3} for g in groups.values()],key=lambda x:-x['flagged'])
        return dict(employers=rows,minForPattern=3,anySimulated=any(r['simulated'] for r in rows))

def query(name,args=None):
    with connection() as db: return db.query(name,args or {})
def mutation(name,args=None):
    with connection(True) as db: return db.mutation(name,args or {})
