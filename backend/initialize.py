"""Initialize a NEW synthetic SQLite demo, without deleting existing records or calling any APIs.

python -m backend.initialize
Official sources are fetched separately. Agents must run rules and Hearings before opening a case.
"""
from backend import store
from seed.demo_data import paystubs, transactions
from seed.reset import student_profile

def main():
    with store.connection(True) as db:
        if db.rows('profiles',limit=1): raise SystemExit('Student file already exists; initialization did not change it.')
        pid=db.put('profiles',{**student_profile(),'preferredLanguage':'en','demo':True})
        for i,t in enumerate(transactions()): db.mutation('transactions:upsert',{**t,'profileId':pid,'nessieId':f'synthetic-initial-{i}'})
        for stub in paystubs(): db.mutation('paystubs:record',{**stub,'profileId':pid})
        db.log('seed','synthetic_initialized','Initialized synthetic structured paystubs and bank records; no live APIs or PDF extraction used',outputIds=[pid])
    print('Synthetic student initialized:',pid)
    print('Fetch official sources and run the agents to evaluate findings and open the case.')
    print('For synthetic inbound support, set DOCKET_DEMO_PROFILE_ID='+pid)
if __name__=='__main__':main()
