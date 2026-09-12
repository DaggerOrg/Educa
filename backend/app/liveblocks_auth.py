"""Backend auth endpoint for every Liveblocks-backed feature in Studio (the
lecturers' chat and the collaborative knowledge-graph boards). Liveblocks has
no official Python SDK, so this calls its REST auth endpoint directly with
the account's secret key:
https://liveblocks.io/docs/api-reference/rest-api-endpoints#post-authorize-user
(the same request `Liveblocks.prepareSession(...).authorize()` makes in the
Node SDK).

Access tokens, not ID tokens: every authenticated teacher gets the exact same
grant, minted fresh on each request -- the fixed chat room, plus every
`kg-board:*` room (one per collaborative graph board, see kg_boards.py). No
per-room permission bookkeeping to offload onto Liveblocks, since there's no
concept of a private room yet -- any teacher can join any room (see
https://liveblocks.io/docs/api-reference/authentication/access-token for why
that's the recommended choice absent per-room permissions).
"""
import hashlib
import os

import httpx
from fastapi import HTTPException

CHAT_ROOM_ID = "lecturers-chat"
# Every collaborative knowledge-graph board is its own room, named
# `kg-board:{board.id}` (board.id comes from kg_boards.py's Postgres row) --
# the wildcard below grants write access to all of them at once, so a new
# board never needs a fresh token.
KG_BOARD_ROOM_PATTERN = "kg-board:*"

# A small fixed palette for multiplayer cursors (@liveblocks/react-flow's
# `Cursors`) -- deterministic per user so the same teacher always gets the
# same color across sessions, without a "pick a color" setting anywhere.
_CURSOR_COLORS = ["#F97066", "#F79009", "#EAAA08", "#66C61C", "#22CCB2", "#2E90FA", "#7A5AF8", "#EE46BC"]


def _cursor_color(user_id: str) -> str:
    digest = hashlib.sha256(user_id.encode()).digest()
    return _CURSOR_COLORS[digest[0] % len(_CURSOR_COLORS)]


def authorize(user: dict) -> dict:
    response = httpx.post(
        "https://api.liveblocks.io/v2/authorize-user",
        headers={"Authorization": f"Bearer {os.environ['LIVEBLOCKS_API_KEY']}"},
        json={
            "userId": user["id"],
            "userInfo": {"name": user["name"], "color": _cursor_color(user["id"])},
            "permissions": {
                CHAT_ROOM_ID: ["*:write"],
                KG_BOARD_ROOM_PATTERN: ["*:write"],
            },
        },
        timeout=10,
    )
    if response.status_code != 200:
        raise HTTPException(response.status_code, f"Liveblocks authorization failed: {response.text}")
    return response.json()
