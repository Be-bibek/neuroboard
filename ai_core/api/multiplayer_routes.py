"""
ai_core/api/multiplayer_routes.py
====================================
NeuroBoard Real-Time Multiplayer Relay Engine

Mounted on the existing FastAPI app at /api/v1/multiplayer/

Architecture:
  - Pure in-memory room state (dict of rooms, peers, locks, delta history).
  - WebSocket-based delta relay: receives atomic mutation events from one peer
    and broadcasts them to all other peers in the same room.
  - Soft-lock system: component-level exclusive locks with 10s TTL, enforced
    by asyncio tasks. Prevents two engineers from editing the same element.
  - Zero external dependencies beyond FastAPI and asyncio.
"""

import asyncio
import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Any, Deque, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

log = logging.getLogger("multiplayer")

router = APIRouter(prefix="/api/v1/multiplayer", tags=["multiplayer"])

# ── Data Structures ────────────────────────────────────────────────────────

@dataclass
class PeerInfo:
    user_id: str
    display_name: str
    color: str
    canvas_mode: str
    cursor_x: Optional[float]
    cursor_y: Optional[float]
    selected_element_id: Optional[str]
    last_seen: float
    ws: Any = field(repr=False)  # WebSocket — excluded from JSON serialization

    def to_dict(self) -> dict:
        return {
            "userId": self.user_id,
            "displayName": self.display_name,
            "color": self.color,
            "canvasMode": self.canvas_mode,
            "cursor": {"x": self.cursor_x, "y": self.cursor_y}
                       if self.cursor_x is not None else None,
            "selectedElementId": self.selected_element_id,
            "lastSeen": int(self.last_seen * 1000),
        }


@dataclass
class LockRecord:
    element_id: str
    locked_by_user_id: str
    locked_by_name: str
    locked_by_color: str
    locked_at: float
    expires_at: float
    ttl_task: Any = field(repr=False, default=None)  # asyncio.Task

    def to_dict(self) -> dict:
        return {
            "elementId": self.element_id,
            "lockedByUserId": self.locked_by_user_id,
            "lockedByName": self.locked_by_name,
            "lockedByColor": self.locked_by_color,
            "lockedAt": int(self.locked_at * 1000),
            "expiresAt": int(self.expires_at * 1000),
        }


@dataclass
class Room:
    room_id: str
    peers: Dict[str, PeerInfo] = field(default_factory=dict)
    locks: Dict[str, LockRecord] = field(default_factory=dict)
    delta_history: Deque[dict] = field(default_factory=lambda: deque(maxlen=200))


# Global room registry
_rooms: Dict[str, Room] = {}

LOCK_TTL_SECONDS = 10.0


def _get_or_create_room(room_id: str) -> Room:
    if room_id not in _rooms:
        _rooms[room_id] = Room(room_id=room_id)
        log.info(f"[Room] Created room: {room_id}")
    return _rooms[room_id]


# ── Broadcast Helpers ──────────────────────────────────────────────────────

async def _broadcast(room: Room, message: dict, exclude_user: Optional[str] = None):
    """Broadcast a JSON message to all peers in the room, skipping the sender."""
    raw = json.dumps(message)
    dead = []
    for uid, peer in room.peers.items():
        if uid == exclude_user:
            continue
        try:
            await peer.ws.send_text(raw)
        except Exception:
            dead.append(uid)
    for uid in dead:
        await _disconnect_peer(room, uid)


async def _send(ws: WebSocket, message: dict):
    """Send a JSON message to a single WebSocket."""
    try:
        await ws.send_text(json.dumps(message))
    except Exception as e:
        log.warning(f"[WS] Failed to send: {e}")


# ── Lock TTL ───────────────────────────────────────────────────────────────

async def _lock_ttl_task(room: Room, element_id: str):
    """Runs as a background task. Expires a soft lock after LOCK_TTL_SECONDS."""
    await asyncio.sleep(LOCK_TTL_SECONDS)
    if element_id in room.locks:
        log.info(f"[Lock] TTL expired for {element_id} in room {room.room_id}")
        del room.locks[element_id]
        await _broadcast(room, {
            "type": "LOCK_RELEASED",
            "elementId": element_id,
            "reason": "ttl_expired",
        })


# ── Peer Lifecycle ─────────────────────────────────────────────────────────

async def _disconnect_peer(room: Room, user_id: str):
    """Cleanly remove a peer: release all their locks, broadcast PEER_LEFT."""
    if user_id not in room.peers:
        return

    del room.peers[user_id]
    log.info(f"[Room] Peer left: {user_id} from {room.room_id}")

    # Release all locks held by this peer
    released = [eid for eid, lock in room.locks.items()
                if lock.locked_by_user_id == user_id]
    for eid in released:
        lock = room.locks.pop(eid)
        if lock.ttl_task and not lock.ttl_task.done():
            lock.ttl_task.cancel()
        await _broadcast(room, {
            "type": "LOCK_RELEASED",
            "elementId": eid,
            "reason": "peer_disconnected",
        })

    await _broadcast(room, {
        "type": "PEER_LEFT",
        "userId": user_id,
    })

    # Clean up empty rooms
    if not room.peers:
        log.info(f"[Room] Room empty, cleaning up: {room.room_id}")
        _rooms.pop(room.room_id, None)


# ── Message Handlers ───────────────────────────────────────────────────────

async def _handle_message(room: Room, peer: PeerInfo, raw: str):
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        log.warning(f"[WS] Invalid JSON from {peer.user_id}: {raw[:100]}")
        return

    msg_type = msg.get("type")
    now = time.time()
    peer.last_seen = now

    if msg_type == "CURSOR_MOVE":
        peer.cursor_x = msg.get("x")
        peer.cursor_y = msg.get("y")
        peer.canvas_mode = msg.get("canvasMode", peer.canvas_mode)
        await _broadcast(room, {
            "type": "PRESENCE_UPDATE",
            "peer": peer.to_dict(),
        }, exclude_user=peer.user_id)

    elif msg_type == "DELTA":
        delta = msg.get("delta", {})
        delta["authorId"] = peer.user_id
        delta["timestamp"] = int(now * 1000)
        room.delta_history.append(delta)
        await _broadcast(room, {
            "type": "DELTA",
            "delta": delta,
        }, exclude_user=peer.user_id)

    elif msg_type == "ACQUIRE_LOCK":
        element_id = msg.get("elementId", "")
        if not element_id:
            return

        if element_id in room.locks:
            existing = room.locks[element_id]
            await _send(peer.ws, {
                "type": "LOCK_DENIED",
                "elementId": element_id,
                "lockedBy": existing.locked_by_name,
            })
            return

        # Grant the lock
        lock = LockRecord(
            element_id=element_id,
            locked_by_user_id=peer.user_id,
            locked_by_name=peer.display_name,
            locked_by_color=peer.color,
            locked_at=now,
            expires_at=now + LOCK_TTL_SECONDS,
        )
        lock.ttl_task = asyncio.create_task(
            _lock_ttl_task(room, element_id)
        )
        room.locks[element_id] = lock

        await _broadcast(room, {
            "type": "LOCK_ACQUIRED",
            "lock": lock.to_dict(),
        })

    elif msg_type == "RELEASE_LOCK":
        element_id = msg.get("elementId", "")
        if element_id in room.locks:
            lock = room.locks.pop(element_id)
            if lock.ttl_task and not lock.ttl_task.done():
                lock.ttl_task.cancel()
            await _broadcast(room, {
                "type": "LOCK_RELEASED",
                "elementId": element_id,
            })

    elif msg_type == "HEARTBEAT":
        # Refresh TTL on all locks held by this peer
        for lock in room.locks.values():
            if lock.locked_by_user_id == peer.user_id:
                lock.expires_at = now + LOCK_TTL_SECONDS
                if lock.ttl_task and not lock.ttl_task.done():
                    lock.ttl_task.cancel()
                lock.ttl_task = asyncio.create_task(
                    _lock_ttl_task(room, lock.element_id)
                )

    elif msg_type == "SELECT_ELEMENT":
        peer.selected_element_id = msg.get("elementId")
        await _broadcast(room, {
            "type": "PRESENCE_UPDATE",
            "peer": peer.to_dict(),
        }, exclude_user=peer.user_id)

    else:
        log.debug(f"[WS] Unknown message type from {peer.user_id}: {msg_type}")


# ── WebSocket Endpoint ─────────────────────────────────────────────────────

@router.websocket("/rooms/{room_id}/ws")
async def multiplayer_ws(websocket: WebSocket, room_id: str):
    await websocket.accept()
    room = _get_or_create_room(room_id)

    # Wait for JOIN_ROOM as the first message
    try:
        join_raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        join_msg = json.loads(join_raw)
        assert join_msg.get("type") == "JOIN_ROOM"
        profile = join_msg.get("userProfile", {})
        user_id = profile.get("userId", f"anon_{id(websocket)}")
    except (asyncio.TimeoutError, AssertionError, Exception):
        await websocket.close(code=4000, reason="Expected JOIN_ROOM as first message")
        return

    peer = PeerInfo(
        user_id=user_id,
        display_name=profile.get("displayName", "Unknown"),
        color=profile.get("color", "#818CF8"),
        canvas_mode=profile.get("canvasMode", "2d"),
        cursor_x=None,
        cursor_y=None,
        selected_element_id=None,
        last_seen=time.time(),
        ws=websocket,
    )
    room.peers[user_id] = peer
    log.info(f"[Room] Peer joined: {peer.display_name} ({user_id}) → {room_id}")

    # Send current room state to the new joiner
    await _send(websocket, {
        "type": "ROOM_STATE",
        "peers": [p.to_dict() for uid, p in room.peers.items() if uid != user_id],
        "locks": [lock.to_dict() for lock in room.locks.values()],
    })

    # Notify existing peers
    await _broadcast(room, {
        "type": "PEER_JOINED",
        "peer": peer.to_dict(),
    }, exclude_user=user_id)

    try:
        while True:
            raw = await websocket.receive_text()
            await _handle_message(room, peer, raw)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.error(f"[WS] Unexpected error for {user_id}: {e}")
    finally:
        await _disconnect_peer(room, user_id)


# ── REST Endpoint ──────────────────────────────────────────────────────────

@router.get("/rooms/{room_id}")
async def get_room_state(room_id: str):
    """Inspect active collaborators, locks, and room health."""
    if room_id not in _rooms:
        return JSONResponse({"room_id": room_id, "active": False, "peers": [], "locks": []})

    room = _rooms[room_id]
    return {
        "room_id": room_id,
        "active": True,
        "peer_count": len(room.peers),
        "peers": [p.to_dict() for p in room.peers.values()],
        "locks": [lock.to_dict() for lock in room.locks.values()],
        "delta_history_size": len(room.delta_history),
    }


@router.get("/rooms")
async def list_rooms():
    """List all active rooms."""
    return {
        "rooms": [
            {
                "room_id": rid,
                "peer_count": len(room.peers),
                "lock_count": len(room.locks),
            }
            for rid, room in _rooms.items()
        ]
    }
