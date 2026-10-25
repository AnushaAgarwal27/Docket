import json
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
import pytest
import requests
from backend import store
from backend.server import Handler,student_status

@pytest.fixture
def records(tmp_path,monkeypatch):
    monkeypatch.setenv('DOCKET_DB_PATH',str(tmp_path/'test.sqlite3'))
    with store.connection(True) as db:
        pid=db.put('profiles',{'name':'Synthetic Priya','demo':True})
        source=db.put('sources',{'url':'https://www.irs.gov/publications/p519','title':'Test source','text':'This is a synthetic source sentence for endpoint validation only.'})
        fid=db.put('flags',{'profileId':pid,'ruleId':'FICA_EXEMPT_F1','amountCents':44064,'status':'open','sourceId':source,'quote':'This is a synthetic source sentence for endpoint validation only.','explanation':'Synthetic finding'})
    cid=store.mutation('cases:open',dict(profileId=pid,flagId=fid,amountCents=44064,draft='Synthetic request'))
    return pid,fid,cid

def test_atomic_claim_and_duplicate_outcome(records):
    pid,fid,cid=records
    assert store.mutation('cases:claimCall',{'caseId':cid}) is False
    store.mutation('cases:approve',{'caseId':cid})
    with ThreadPoolExecutor(max_workers=8) as pool:
        claims=list(pool.map(lambda _:store.mutation('cases:claimCall',{'caseId':cid}),range(8)))
    assert sum(claims)==1
    args=dict(caseId=cid,result='stalled',summary='No date promised',answeredBy='Test payroll')
    first=store.mutation('cases:logCallOutcome',args)
    assert store.mutation('cases:logCallOutcome',args)==first
    assert store.query('cases:get',{'caseId':cid})['state']=='written_request'
    assert len(store.query('dashboard:snapshot',{'profileId':pid})['cases'][0]['calls'])==1
    store.mutation('cases:recordWrittenRequest',{'caseId':cid,'text':'Draft only'})
    store.mutation('cases:followUp',{'caseId':cid})
    assert store.mutation('cases:claimCall',{'caseId':cid}) is True
    assert store.mutation('cases:logCallOutcome',{**args,'result':'promised','promisedBy':'2026-11-07'})!=first
    with store.connection(True) as db:
        tx=db.put('transactions',dict(profileId=pid,amountCents=44064,kind='deposit',counterparty='Test payroll'))
    store.mutation('cases:refundReceived',{'caseId':cid,'transactionId':tx})
    assert store.query('cases:get',{'caseId':cid})['outcome']=='refunded'
    assert store.query('flags:listByProfile',{'profileId':pid})[0]['status']=='resolved'

def test_invalid_outcome_rolls_back(records):
    pid,fid,cid=records
    with pytest.raises(ValueError):store.mutation('cases:logCallOutcome',dict(caseId=cid,result='promised',summary='bad',answeredBy='test'))
    assert store.query('dashboard:snapshot',{'profileId':pid})['cases'][0]['calls']==[]
    store.mutation('cases:approve',{'caseId':cid});store.mutation('cases:claimCall',{'caseId':cid})
    with pytest.raises(ValueError):store.mutation('cases:logCallOutcome',dict(caseId=cid,result='promised',summary='bad',answeredBy='test',promisedBy='next Tuesday'))
    assert store.query('dashboard:snapshot',{'profileId':pid})['cases'][0]['calls']==[]

def test_persistence_dedup_and_integer_money(records):
    pid,_,_=records
    tx=dict(profileId=pid,nessieId='bank-1',amountCents=100,kind='deposit')
    one=store.mutation('transactions:upsert',tx)
    assert store.mutation('transactions:upsert',tx)=={'id':one['id'],'created':False}
    with pytest.raises(ValueError):store.mutation('transactions:upsert',{**tx,'nessieId':'bank2','amountCents':1.5})
    assert len(store.query('transactions:listByProfile',{'profileId':pid}))==1

def test_http_auth_tools_and_private_files(records,monkeypatch):
    pid,_,cid=records
    monkeypatch.setenv('DOCKET_API_TOKEN','test-dashboard')
    monkeypatch.setenv('CARTESIA_TOOL_TOKEN','test-office')
    monkeypatch.setenv('CARTESIA_SUPPORT_TOOL_TOKEN','test-student')
    monkeypatch.setenv('DOCKET_SYNTHETIC_SUPPORT','1')
    monkeypatch.setenv('DOCKET_DEMO_PROFILE_ID',pid)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    dashboard={'Authorization':'Bearer test-dashboard'};office={'Authorization':'Bearer test-office'}
    try:
        assert requests.post(base+'/cartesia/case-summary',json={'case_id':cid}).status_code==401
        r=requests.post(base+'/cartesia/case-summary',headers=office,json={'case_id':cid})
        assert r.status_code==200 and '$440.64' in r.text
        assert requests.post(base+'/api/mutation',headers=office,json={'name':'cases:approve','args':{'caseId':cid}}).status_code==401
        assert requests.post(base+'/api/mutation',headers=dashboard,json={'name':'seed:resetDemo','args':{}}).status_code==403
        assert requests.post(base+'/api/mutation',headers=dashboard,json={'name':'cases:approve','args':{'caseId':cid}}).status_code==200
        assert store.mutation('cases:claimCall',{'caseId':cid})
        body={'case_id':cid,'result':'promised','answered_by':'Payroll','summary':'Review pending','promised_by':'2026-11-07','reference_number':'TEST1'}
        assert requests.post(base+'/cartesia/call-outcome',headers=office,json=body).status_code==200
        r=requests.post(base+'/cartesia/student-case-status',headers={'Authorization':'Bearer test-student'},json={})
        assert r.status_code==200 and r.json()['cases'][0]['calls'][0]['referenceNo']=='TEST1'
        storage=requests.post(base+'/api/files',headers=dashboard,data=b'%PDF test').json()['storageId']
        assert requests.get(base+'/api/files/'+storage).status_code==401
        assert requests.get(base+'/api/files/'+storage,headers=dashboard).content==b'%PDF test'
        assert requests.post(base+'/api/query',headers=dashboard,data='bad json').status_code==400
    finally:server.shutdown();server.server_close();thread.join()

def test_student_support_requires_explicit_demo_binding(records,monkeypatch):
    monkeypatch.delenv('DOCKET_DEMO_PROFILE_ID',raising=False)
    with pytest.raises(ValueError):student_status()

def test_held_flag_cannot_be_approved(records):
    _,fid,cid=records
    store.mutation('flags:setStatus',{'flagId':fid,'status':'on_hold'})
    with pytest.raises(ValueError):store.mutation('cases:approve',{'caseId':cid})
    assert store.query('cases:get',{'caseId':cid})['state']=='awaiting_approval'
