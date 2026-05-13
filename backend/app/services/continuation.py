"""Server-side continuation sessions for truncated graph traversals.

A continuation session stores the serialized resume state of a traversal that
hit its node/edge caps. The client receives a ``continuation_id`` and replays
it to fetch the next chunk.
"""

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.models import TraversalSession


async def create_session(session: AsyncSession, state: dict) -> str:
    """Persist a resume state and return its new session id."""
    session_id = uuid.uuid4().hex
    session.add(TraversalSession(id=session_id, state_json=json.dumps(state)))
    await session.commit()
    return session_id


async def load_session(session: AsyncSession, session_id: str) -> dict | None:
    """Return the stored state, or None if missing or expired."""
    row = await session.get(TraversalSession, session_id)
    if row is None:
        return None
    created_at = row.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - created_at).total_seconds()
    if age > row.ttl_seconds:
        return None
    return json.loads(row.state_json)


async def update_session(session: AsyncSession, session_id: str, state: dict) -> None:
    """Replace the stored state for an existing session."""
    row = await session.get(TraversalSession, session_id)
    if row is None:
        return
    row.state_json = json.dumps(state)
    await session.commit()
