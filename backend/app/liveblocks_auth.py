"""Backend auth endpoint for the lecturers' chat (Liveblocks Feeds --
see https://liveblocks.io/docs/use-cases/chat and
frontend/src/components/TeacherChat.tsx). Liveblocks has no official Python
SDK, so this calls its REST auth endpoint directly with the account's
secret key: https://liveblocks.io/docs/api-reference/rest-api-endpoints#post-authorize-user
(the same request `Liveblocks.prepareSession(...).authorize()` makes in the
Node SDK).

Access tokens, not ID tokens: the app has exactly one shared Liveblocks room
(`ROOM_ID`) with no per-room permission bookkeeping to offload onto
Liveblocks -- every authenticated teacher gets the same fixed grant for that
one room, minted fresh on each request (see
https://liveblocks.io/docs/api-reference/authentication/access-token for why
that's the recommended choice absent per-room permissions).
"""
import os

import httpx
from fastapi import HTTPException

# Every lecturer chats in this one Liveblocks room -- see TeacherChat.tsx's
# "shared staff room" scope decision. Access-token permissions require a
# base `*:read`/`*:write` grant -- a granular scope like `feeds:write` only
# works as a modifier on top of one, not standalone (confirmed against the
# live API: a `{"feeds:write"}`-only grant is rejected with
# UNPROCESSABLE_ENTITY). `*:write` also covers Storage/Comments, but this
# room never uses either, so in practice it's equivalent to feeds-only access.
ROOM_ID = "lecturers-chat"


def authorize(user: dict) -> dict:
    response = httpx.post(
        "https://api.liveblocks.io/v2/authorize-user",
        headers={"Authorization": f"Bearer {os.environ['LIVEBLOCKS_API_KEY']}"},
        json={
            "userId": user["id"],
            "userInfo": {"name": user["name"]},
            "permissions": {ROOM_ID: ["*:write"]},
        },
        timeout=10,
    )
    if response.status_code != 200:
        raise HTTPException(response.status_code, f"Liveblocks authorization failed: {response.text}")
    return response.json()
