"""HTTP transport for the shared student file and Cartesia webhook tools.

python -m backend.server --port 8000
Dashboard requests require DOCKET_API_TOKEN. Cartesia uses separate tool tokens.
Bound to localhost by default; put behind HTTPS for remote tools. Synthetic demo only.
"""
from __future__ import annotations
import argparse
import hmac
import json
import os
import re
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from dotenv import load_dotenv
from backend import store

MAX_BODY=2*1024*1024
READS={'profiles:list','profiles:get','dashboard:snapshot','activity:recent','timeline:forProfile','patterns:byEmployer','files:forFlag'}
WRITES={'cases:approve','cases:decline','cases:followUp','cases:setPayrollScript'}

def case_summary(case_id):
    c=store.query('cases:get',{'caseId':case_id})
    if not c: raise ValueError('No case found')
    p=store.query('profiles:get',{'profileId':c['profileId']})
    f=store.query('flags:listByProfile',{'profileId':p['_id']})
    flag=next((x for x in f if x['_id']==c['flagId']),None)
    if not flag or flag['status'] not in ['open','case_opened','resolved']: raise ValueError('Finding is on hold or unavailable')
    source=store.query('sources:get',{'sourceId':flag['sourceId']})
    from rules.quote_checker import check_quote
    if not source or not check_quote(flag['quote'],source['text']).ok: raise ValueError('Source quote cannot be verified; do not proceed')
    # Use the linked finding's totals; never add unrelated paychecks or disclose hours.
    money=lambda n:f'${n/100:,.2f}'
    stubs=store.query('paystubs:listByProfile',{'profileId':p['_id']})
    linked=[s for s in stubs if s['_id'] in flag.get('paystubIds',[])]
    employer=linked[0]['employer'] if linked else p.get('employer','the employer')
    return (f"Case {c['_id']}. State: {c['state']}. Acting with the student's recorded approval, ask {employer} "
            f"to review a potential refund of {money(c['amountCents'])} for {p['name']}. "
            f"Stored finding: {flag['explanation']} Official source: {source['title']}. Exact clause: {flag['quote']} "
            "Ask whether a refund applies, whether future withholding should be corrected, the response date and a reference number. "
            "Do not share work-hours findings, bank information or identity numbers. If the student is needed, record needs_student.")

def student_status():
    # Explicit synthetic demo binding. Never select an arbitrary real caller's profile.
    pid=os.environ.get('DOCKET_DEMO_PROFILE_ID','')
    if not pid or os.environ.get('DOCKET_SYNTHETIC_SUPPORT')!='1': raise ValueError('Synthetic support is not configured')
    snap=store.query('dashboard:snapshot',{'profileId':pid})
    if not snap or not snap['profile'].get('demo'): raise ValueError('Explicit synthetic demo student not found')
    return {'synthetic':True,'student':snap['profile']['name'],
            'preferred_language':snap['profile'].get('preferredLanguage','en'),
            'findings':[{'rule':f['ruleId'],'explanation':f['explanation'],'amount_cents':f['amountCents'],'status':f['status']} for f in snap['flags']],
            'cases':[{'case_id':c['_id'],'state':c['state'],'amount_cents':c['amountCents'],
                      'next_follow_up':c['nextFollowUp'],'confirmed_call_time':None,'call_error':c.get('callError'),
                      'outcome':c.get('outcome'),'calls':[{k:r.get(k) for k in ['at','summary','answeredBy','promisedBy','referenceNo']} for r in c['calls']]} for c in snap['cases']],
            'instruction':'Explain only recorded facts. A follow-up date is not a scheduled call. Do not approve actions or give advice.'}

class Handler(BaseHTTPRequestHandler):
    server_version='Docket/1.0'
    def log_message(self,fmt,*args):
        # Do not log paths, tokens or bodies (file URLs may carry short-lived access tickets).
        pass
    def authorized(self,key):
        expected=os.environ.get(key,''); actual=self.headers.get('Authorization','')
        return bool(expected) and hmac.compare_digest(actual,'Bearer '+expected)
    def send(self,status,body,kind='application/json'):
        data=json.dumps(body).encode() if kind=='application/json' else body.encode() if isinstance(body,str) else body
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_GET(self):
        path=urlsplit(self.path).path
        if path=='/health': return self.send(200,{'status':'ok','storage':'sqlite'})
        if not self.authorized('DOCKET_API_TOKEN'): return self.send(401,{'error':'Unauthorized'})
        if path.startswith('/api/files/'):
            id=path.rsplit('/',1)[-1]
            if not re.fullmatch(r'[a-f0-9]{32}',id): return self.send(404,{'error':'File not found'})
            p=store.files_path()/id
            if p.is_file(): return self.send(200,p.read_bytes(),'application/pdf')
        self.send(404,{'error':'Not found'})
    def do_POST(self):
        path=urlsplit(self.path).path
        token='CARTESIA_SUPPORT_TOOL_TOKEN' if path=='/cartesia/student-case-status' else 'CARTESIA_TOOL_TOKEN' if path.startswith('/cartesia/') else 'DOCKET_API_TOKEN'
        if not self.authorized(token): return self.send(401,{'error':'Unauthorized'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<0 or length>MAX_BODY: return self.send(413,{'error':'Request too large'})
            raw=self.rfile.read(length)
            if path=='/api/files':
                id=secrets.token_hex(16); (store.files_path()/id).write_bytes(raw); return self.send(200,{'storageId':id})
            a=json.loads(raw or b'{}')
            if not isinstance(a,dict): raise ValueError('Expected JSON object')
            if path in ['/api/query','/api/mutation']:
                name=a.get('name'); args=a.get('args',{})
                if not isinstance(name,str) or not isinstance(args,dict): raise ValueError('Invalid request')
                if path.endswith('query'):
                    if name not in READS: return self.send(403,{'error':'Query not exposed'})
                    result=store.query(name,args)
                else:
                    if name not in WRITES: return self.send(403,{'error':'Mutation not exposed'})
                    result=store.mutation(name,args)
                return self.send(200,{'value':result})
            if path=='/cartesia/student-case-status': return self.send(200,student_status())
            if path=='/cartesia/case-summary':
                cid=a.get('case_id',a.get('caseId'))
                if not isinstance(cid,str): raise ValueError('case_id required')
                return self.send(200,case_summary(cid),'text/plain; charset=utf-8')
            if path=='/cartesia/call-outcome':
                args={'caseId':a.get('case_id',a.get('caseId')),'result':a.get('result'),
                      'answeredBy':a.get('answered_by',a.get('answeredBy','Payroll office')),'summary':a.get('summary')}
                for source,target in [('promised_by','promisedBy'),('reference_number','referenceNo')]:
                    value=a.get(source,a.get(target))
                    if value is not None:
                        if not isinstance(value,str): raise ValueError('Invalid '+source)
                        args[target]=value
                if any(not isinstance(args[k],str) for k in ['caseId','result','answeredBy','summary']): raise ValueError('Missing outcome fields')
                id=store.mutation('cases:logCallOutcome',args)
                return self.send(200,'Recorded call outcome '+id,'text/plain; charset=utf-8')
            self.send(404,{'error':'Not found'})
        except (ValueError,KeyError,TypeError) as e: self.send(400,{'error':str(e)})
        except Exception: self.send(500,{'error':'Backend operation failed; review the local service logs'})

def main():
    load_dotenv()
    ap=argparse.ArgumentParser();ap.add_argument('--host',default='127.0.0.1');ap.add_argument('--port',type=int,default=8000);a=ap.parse_args()
    if not os.environ.get('DOCKET_API_TOKEN'): raise SystemExit('Set DOCKET_API_TOKEN before starting the server')
    print(f'Docket backend: http://{a.host}:{a.port}; SQLite: {store.db_path()}')
    ThreadingHTTPServer((a.host,a.port),Handler).serve_forever()
if __name__=='__main__': main()
