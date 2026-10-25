"""The historical file-helper module now stores private bytes locally."""
from pathlib import Path
from agents.convex_files import upload_and_attach
from backend import store

def test_local_file_attach_and_receipt(tmp_path,monkeypatch):
    monkeypatch.setenv('DOCKET_DB_PATH',str(tmp_path/'d.sqlite3'))
    with store.connection(True) as db:
        pid=db.put('profiles',{'name':'Synthetic'})
        stub=db.put('paystubs',{'profileId':pid,'sourceFile':'p.pdf'})
        flag=db.put('flags',{'profileId':pid,'paystubIds':[stub]})
    pdf=tmp_path/'p.pdf';pdf.write_bytes(b'%PDF synthetic')
    id=upload_and_attach(pdf,'paystub',agent='ledger',paystubId=stub)
    assert id
    receipt=store.query('files:forFlag',{'flagId':flag})
    assert receipt['paystubs'][0]['filename']=='p.pdf'
    with store.connection() as db: row=db.get(id)
    assert (store.files_path()/row['storageId']).read_bytes()==pdf.read_bytes()
    assert store.query('activity:recent')[0]['action']=='file_uploaded'

def test_failure_is_logged(tmp_path,monkeypatch):
    monkeypatch.setenv('DOCKET_DB_PATH',str(tmp_path/'d.sqlite3'))
    assert upload_and_attach(tmp_path/'missing.pdf','paystub',agent='ledger') is None
    assert store.query('activity:recent')[0]['action']=='file_upload_failed'
