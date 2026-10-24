"""Shared access to the student file on Convex for every agent."""

import os

from convex import ConvexClient
from dotenv import load_dotenv

load_dotenv()

_client: ConvexClient | None = None


def client() -> ConvexClient:
    global _client
    if _client is None:
        _client = ConvexClient(os.environ["CONVEX_URL"])
    return _client


def as_ints(value):
    """Convex returns every number as a float; money and hours are whole numbers in code."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [as_ints(v) for v in value]
    if isinstance(value, dict):
        return {k: as_ints(v) for k, v in value.items()}
    return value


def query(name: str, args: dict | None = None):
    return as_ints(client().query(name, args or {}))


def mutation(name: str, args: dict | None = None):
    return as_ints(client().mutation(name, args or {}))


def log(agent: str, action: str, detail: str, **extra) -> None:
    """One activity row per action, including actions an agent decided not to take."""
    mutation("activity:log", {"agent": agent, "action": action, "detail": detail, **extra})


def dollars(cents: int) -> str:
    return f"${cents // 100:,}.{cents % 100:02d}"
