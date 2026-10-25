"""Shared SQLite student file for every Docket agent. No cloud database required."""
from dotenv import load_dotenv
load_dotenv()
from backend.store import query, mutation

def client():
    """Small compatibility adapter for source collectors using client.query/mutation."""
    from backend import store
    return store

def as_ints(value):
    if isinstance(value,float) and value.is_integer(): return int(value)
    if isinstance(value,list): return [as_ints(v) for v in value]
    if isinstance(value,dict): return {k:as_ints(v) for k,v in value.items()}
    return value

def log(agent, action, detail, **extra):
    mutation('activity:log',dict(agent=agent,action=action,detail=detail,**extra))

def dollars(cents: int) -> str:
    return f'${cents // 100:,}.{cents % 100:02d}'
