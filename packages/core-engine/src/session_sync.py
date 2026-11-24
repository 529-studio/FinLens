"""
FinTrace Real-Time Collaborative Audit Session Sync Engine
Governed by Sprint 11 Task S11-03, AGENTS.md Rule 1, Rule 2, Rule 13, Rule 15,
module-boundary-and-concurrency, and resilient-networking-and-waf.
Provides concurrency-safe room management, multi-peer presence sync,
spatial annotation broadcasting, and heartbeat vitality tracking over WebSockets.
"""

import re
import time
import json
import uuid
import logging
import asyncio
from typing import Dict, Set, Tuple, Optional, List, Any
from fastapi import WebSocket, WebSocketDisconnect

from contracts import (
    SessionEventType,
    UserPresence,
    AuditAnnotation,
    SessionState,
    CollaborativeMessage,
)

logger = logging.getLogger("fintrace.session_sync")

# Predefined high-contrast, accessible avatar/cursor color palette
AUDITOR_PALETTE = [
    "#4F46E5",  # Indigo
    "#059669",  # Emerald
    "#D97706",  # Amber
    "#DC2626",  # Red
    "#7C3AED",  # Violet
    "#0891B2",  # Cyan
    "#BE185D",  # Pink
    "#2563EB",  # Blue
]


def assign_user_color(user_id: str) -> str:
    """Deterministically maps a user ID to a distinct high-contrast color."""
    val = sum(ord(c) for c in user_id)
    return AUDITOR_PALETTE[val % len(AUDITOR_PALETTE)]


class AuditSessionManager:
    """
    In-memory, concurrency-safe manager for collaborative audit sessions.
    Protects session state mutations using asyncio.Lock.
    """

    def __init__(self, heartbeat_timeout_seconds: float = 60.0):
        self.sessions: Dict[str, SessionState] = {}
        self.room_connections: Dict[str, Set[WebSocket]] = {}
        self.connection_meta: Dict[WebSocket, Tuple[str, str]] = {}  # ws -> (session_id, user_id)
        self.heartbeat_timeout_seconds = heartbeat_timeout_seconds
        self._lock = asyncio.Lock()

    @staticmethod
    def validate_session_id(session_id: str) -> str:
        """
        Validates session_id against path traversal and SQL/script injection attacks.
        Enforces strict alphanumeric, hyphen, and underscore characters.
        """
        if not session_id or not isinstance(session_id, str):
            raise ValueError("session_id must be a non-empty string")
        if ".." in session_id or "/" in session_id or "\\" in session_id:
            raise ValueError("Access denied: Path traversal detected in session_id")
        if not re.match(r"^[a-zA-Z0-9_\-]{3,64}$", session_id):
            raise ValueError("Invalid session_id: Must be 3-64 alphanumeric, dash, or underscore characters")
        return session_id

    @staticmethod
    def validate_document_id(document_id: str) -> str:
        """Validates document_id against malicious path traversal patterns."""
        if not document_id or not isinstance(document_id, str):
            raise ValueError("document_id must be a non-empty string")
        if ".." in document_id or "/" in document_id or "\\" in document_id:
            raise ValueError("Access denied: Path traversal detected in document_id")
        if not re.match(r"^[a-zA-Z0-9_\-]{1,64}$", document_id):
            raise ValueError("Invalid document_id: Must be 1-64 alphanumeric, dash, or underscore characters")
        return document_id

    async def get_or_create_session(self, session_id: str, document_id: str) -> SessionState:
        """Creates or retrieves an existing collaborative audit session."""
        self.validate_session_id(session_id)
        self.validate_document_id(document_id)

        async with self._lock:
            if session_id not in self.sessions:
                self.sessions[session_id] = SessionState(
                    session_id=session_id,
                    document_id=document_id,
                    created_at=time.time(),
                    active_users={},
                    annotations=[],
                )
                self.room_connections[session_id] = set()
            return self.sessions[session_id]

    async def register_connection(
        self,
        session_id: str,
        document_id: str,
        websocket: WebSocket,
        user_id: str,
        name: str = "FinTrace Auditor",
        role: str = "junior_analyst",
        active_page: int = 1,
    ) -> SessionState:
        """
        Registers an active WebSocket client into a collaborative audit room.
        Updates user presence and associates socket with session metadata.
        """
        self.validate_session_id(session_id)
        self.validate_document_id(document_id)

        async with self._lock:
            if session_id not in self.sessions:
                self.sessions[session_id] = SessionState(
                    session_id=session_id,
                    document_id=document_id,
                    created_at=time.time(),
                    active_users={},
                    annotations=[],
                )
                self.room_connections[session_id] = set()

            session = self.sessions[session_id]
            self.room_connections[session_id].add(websocket)
            self.connection_meta[websocket] = (session_id, user_id)

            # Record or update user presence
            presence = UserPresence(
                user_id=user_id,
                name=name,
                role=role,
                color=assign_user_color(user_id),
                active_page=max(1, active_page),
                cursor_x=None,
                cursor_y=None,
                last_seen=time.time(),
            )
            session.active_users[user_id] = presence
            return session

    async def disconnect(self, websocket: WebSocket) -> Optional[Tuple[str, str, SessionState, bool]]:
        """
        Removes a WebSocket client from a session.
        If user has no other active sockets in this session, removes them from active_users.
        Returns (session_id, user_id, updated_session, user_removed_completely).
        """
        async with self._lock:
            meta = self.connection_meta.pop(websocket, None)
            if not meta:
                return None

            session_id, user_id = meta
            if session_id in self.room_connections:
                self.room_connections[session_id].discard(websocket)

            session = self.sessions.get(session_id)
            if not session:
                return None

            # Check if user has other connections in this room
            remaining_user_connections = [
                ws for ws in self.room_connections.get(session_id, set())
                if self.connection_meta.get(ws) == (session_id, user_id)
            ]

            user_removed = False
            if not remaining_user_connections:
                if user_id in session.active_users:
                    del session.active_users[user_id]
                    user_removed = True

            return session_id, user_id, session, user_removed

    async def broadcast(self, session_id: str, message: dict, exclude: Optional[WebSocket] = None) -> None:
        """
        Broadcasts a JSON message to all active WebSocket clients in a session.
        Handles client disconnects gracefully during broadcast.
        """
        sockets = list(self.room_connections.get(session_id, set()))
        if not sockets:
            return

        payload = json.dumps(message)
        dead_sockets: List[WebSocket] = []

        for ws in sockets:
            if ws is exclude:
                continue
            try:
                await ws.send_text(payload)
            except Exception as e:
                logger.warning("Failed to send WebSocket message to client in %s: %s", session_id, e)
                dead_sockets.append(ws)

        if dead_sockets:
            for dead_ws in dead_sockets:
                await self.disconnect(dead_ws)

    async def handle_message(
        self,
        websocket: WebSocket,
        raw_text: str,
    ) -> Optional[dict]:
        """
        Processes an incoming collaborative WebSocket frame.
        Updates internal session state under lock and returns the broadcast message (if applicable).
        """
        meta = self.connection_meta.get(websocket)
        if not meta:
            return {"event": SessionEventType.ERROR.value, "error": "Unregistered connection"}

        session_id, user_id = meta

        try:
            data = json.loads(raw_text)
        except Exception:
            return {"event": SessionEventType.ERROR.value, "error": "Invalid JSON format"}

        event_str = data.get("event")
        payload = data.get("payload", {})

        async with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return {"event": SessionEventType.ERROR.value, "error": f"Session '{session_id}' not found"}

            user_presence = session.active_users.get(user_id)
            if user_presence:
                user_presence.last_seen = time.time()

            # 1. Cursor Move & Presence Update
            if event_str in (SessionEventType.CURSOR_MOVE.value, SessionEventType.PRESENCE.value):
                if user_presence:
                    if "active_page" in payload:
                        user_presence.active_page = max(1, int(payload["active_page"]))
                    if "cursor_x" in payload and payload["cursor_x"] is not None:
                        user_presence.cursor_x = max(0.0, min(1000.0, float(payload["cursor_x"])))
                    if "cursor_y" in payload and payload["cursor_y"] is not None:
                        user_presence.cursor_y = max(0.0, min(1000.0, float(payload["cursor_y"])))

                broadcast_msg = {
                    "event": SessionEventType.PRESENCE.value,
                    "session_id": session_id,
                    "user_id": user_id,
                    "payload": user_presence.model_dump() if user_presence else {},
                    "timestamp": time.time(),
                }
                return broadcast_msg

            # 2. Add Visual Audit Annotation
            elif event_str == SessionEventType.ANNOTATION_ADD.value:
                page_number = int(payload.get("page_number", 1))
                bounding_box = payload.get("bounding_box", [0.0, 0.0, 1000.0, 1000.0])
                comment = str(payload.get("comment", "")).strip()

                if not comment:
                    return {"event": SessionEventType.ERROR.value, "error": "Annotation comment cannot be empty"}

                if len(bounding_box) != 4:
                    return {"event": SessionEventType.ERROR.value, "error": "Bounding box must contain exactly 4 coordinates"}

                # Clamp bounding box coordinates to [0, 1000]
                clamped_bbox = [max(0.0, min(1000.0, float(c))) for c in bounding_box]

                annotation_id = payload.get("annotation_id") or str(uuid.uuid4())
                annotation = AuditAnnotation(
                    annotation_id=annotation_id,
                    document_id=session.document_id,
                    page_number=page_number,
                    bounding_box=clamped_bbox,
                    comment=comment,
                    author_id=user_id,
                    author_name=user_presence.name if user_presence else user_id,
                    created_at=time.time(),
                    resolved=False,
                )
                session.annotations.append(annotation)

                broadcast_msg = {
                    "event": SessionEventType.ANNOTATION_ADD.value,
                    "session_id": session_id,
                    "user_id": user_id,
                    "payload": annotation.model_dump(),
                    "timestamp": time.time(),
                }
                return broadcast_msg

            # 3. Resolve Visual Audit Annotation
            elif event_str == SessionEventType.ANNOTATION_RESOLVE.value:
                annotation_id = str(payload.get("annotation_id", ""))
                target = next((a for a in session.annotations if a.annotation_id == annotation_id), None)
                if not target:
                    return {"event": SessionEventType.ERROR.value, "error": f"Annotation '{annotation_id}' not found"}

                target.resolved = True
                target.resolved_by = user_id

                broadcast_msg = {
                    "event": SessionEventType.ANNOTATION_RESOLVE.value,
                    "session_id": session_id,
                    "user_id": user_id,
                    "payload": target.model_dump(),
                    "timestamp": time.time(),
                }
                return broadcast_msg

            # 4. Delete Visual Audit Annotation
            elif event_str == SessionEventType.ANNOTATION_DELETE.value:
                annotation_id = str(payload.get("annotation_id", ""))
                target = next((a for a in session.annotations if a.annotation_id == annotation_id), None)
                if not target:
                    return {"event": SessionEventType.ERROR.value, "error": f"Annotation '{annotation_id}' not found"}

                session.annotations = [a for a in session.annotations if a.annotation_id != annotation_id]

                broadcast_msg = {
                    "event": SessionEventType.ANNOTATION_DELETE.value,
                    "session_id": session_id,
                    "user_id": user_id,
                    "payload": {"annotation_id": annotation_id},
                    "timestamp": time.time(),
                }
                return broadcast_msg

            # 5. Heartbeat Ping / Pong
            elif event_str == SessionEventType.HEARTBEAT.value:
                return {
                    "event": SessionEventType.HEARTBEAT.value,
                    "session_id": session_id,
                    "user_id": user_id,
                    "payload": {"status": "pong", "active_users_count": len(session.active_users)},
                    "timestamp": time.time(),
                }

            else:
                return {"event": SessionEventType.ERROR.value, "error": f"Unknown event type: '{event_str}'"}

    async def prune_stale_users(self, session_id: str) -> List[str]:
        """
        Removes users from active_users whose last_seen timestamp exceeds heartbeat_timeout_seconds.
        Returns list of pruned user IDs.
        """
        async with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return []

            now = time.time()
            stale_users: List[str] = []
            for uid, presence in list(session.active_users.items()):
                if now - presence.last_seen > self.heartbeat_timeout_seconds:
                    stale_users.append(uid)

            for uid in stale_users:
                del session.active_users[uid]

            return stale_users

    def get_session_snapshot(self, session_id: str) -> Optional[dict]:
        """Returns read-only dictionary snapshot of session state."""
        session = self.sessions.get(session_id)
        if not session:
            return None
        return session.model_dump()
