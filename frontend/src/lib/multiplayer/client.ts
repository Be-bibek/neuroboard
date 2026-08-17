/**
 * frontend/src/lib/multiplayer/client.ts
 * ========================================
 * NeuroBoardMultiplayerClient — Reactive WebSocket client for the NeuroBoard
 * real-time multiplayer collaboration engine.
 *
 * Usage:
 *   const client = new NeuroBoardMultiplayerClient();
 *   client.onPresenceUpdate = (peers) => { ... };
 *   client.onDeltaReceived  = (delta) => { ... };
 *   await client.joinRoom("my-project", userProfile);
 *   client.sendCursor(120, 85);
 *   client.broadcastDelta("MOVE_COMPONENT", "U1", { x: 120, y: 85 });
 *   await client.acquireLock("U1");   // returns true/false
 *   client.releaseLock("U1");
 */

import type {
  CollaboratorPresence,
  MultiplayerDelta,
  MultiplayerMessage,
  OpType,
  SubCircuitLock,
} from "../../types/multiplayer";
import { userIdToColor } from "../../types/multiplayer";

// ── Config ─────────────────────────────────────────────────────────────────

const WS_BASE = "ws://localhost:8000/api/v1/multiplayer/rooms";
const HEARTBEAT_INTERVAL_MS = 3_000;
const CURSOR_MIN_DELTA_PX = 1; // only send if moved ≥ 1 unit
const CURSOR_THROTTLE_MS = 33; // ~30Hz

// ── Types ──────────────────────────────────────────────────────────────────

export interface UserProfile {
  userId: string;
  displayName: string;
  canvasMode?: CollaboratorPresence["canvasMode"];
}

// ── Client ─────────────────────────────────────────────────────────────────

export class NeuroBoardMultiplayerClient {
  // ── Public Event Callbacks ──────────────────────────────────────────────
  onPresenceUpdate: (peers: Map<string, CollaboratorPresence>) => void = () => {};
  onDeltaReceived:  (delta: MultiplayerDelta) => void = () => {};
  onLockChanged:    (locks: Map<string, SubCircuitLock>) => void = () => {};
  onPeerJoined:     (peer: CollaboratorPresence) => void = () => {};
  onPeerLeft:       (userId: string) => void = () => {};
  onStatusChange:   (status: "OFFLINE" | "CONNECTING" | "CONNECTED") => void = () => {};

  // ── Internal State ──────────────────────────────────────────────────────
  private socket:   WebSocket | null = null;
  private roomId:   string | null = null;
  private profile:  UserProfile | null = null;
  private color:    string = "#818CF8";

  private peers:    Map<string, CollaboratorPresence> = new Map();
  private locks:    Map<string, SubCircuitLock> = new Map();
  private version:  number = 0;

  // Reconnection
  private reconnectAttempt = 0;
  private reconnectTimer:   ReturnType<typeof setTimeout> | null = null;
  private intentionalClose  = false;

  // Cursor throttle
  private lastCursorSent:   number = 0;
  private lastCursorX:      number = -999;
  private lastCursorY:      number = -999;

  // Heartbeat
  private heartbeatTimer:   ReturnType<typeof setInterval> | null = null;

  // Pending lock acquisition promises
  private lockWaiters: Map<string, { resolve: (val: boolean) => void }> = new Map();

  // ── Public API ──────────────────────────────────────────────────────────

  async joinRoom(roomId: string, profile: UserProfile): Promise<void> {
    this.roomId = roomId;
    this.profile = profile;
    this.color = userIdToColor(profile.userId);
    this.intentionalClose = false;
    this.reconnectAttempt = 0;
    this._connect();
  }

  leaveRoom(): void {
    this.intentionalClose = true;
    this._stopHeartbeat();
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.socket) {
      this._sendRaw({ type: "LEAVE_ROOM", roomId: this.roomId!, senderId: this.profile!.userId, timestamp: Date.now() });
      this.socket.close();
      this.socket = null;
    }
    this.peers.clear();
    this.locks.clear();
    this.roomId = null;
    this.profile = null;
  }

  /**
   * Broadcast the local cursor position. Throttled to 30Hz.
   * Skips send if cursor hasn't moved at least 1 unit.
   */
  sendCursor(x: number, y: number, canvasMode?: CollaboratorPresence["canvasMode"]): void {
    const now = Date.now();
    if (
      now - this.lastCursorSent < CURSOR_THROTTLE_MS ||
      (Math.abs(x - this.lastCursorX) < CURSOR_MIN_DELTA_PX &&
       Math.abs(y - this.lastCursorY) < CURSOR_MIN_DELTA_PX)
    ) {
      return;
    }
    this.lastCursorSent = now;
    this.lastCursorX = x;
    this.lastCursorY = y;
    this._sendRaw({
      type: "CURSOR_MOVE",
      roomId: this.roomId!,
      senderId: this.profile!.userId,
      timestamp: now,
      x,
      y,
      canvasMode: canvasMode ?? this.profile?.canvasMode ?? "2d",
    });
  }

  /**
   * Broadcast an atomic mutation delta to all room peers.
   */
  broadcastDelta(opType: OpType, targetId: string, payload: Record<string, unknown>): void {
    if (!this.roomId || !this.profile) return;
    const delta: MultiplayerDelta = {
      roomId: this.roomId,
      authorId: this.profile.userId,
      version: ++this.version,
      opType,
      targetId,
      payload,
      timestamp: Date.now(),
    };
    this._sendRaw({
      type: "DELTA",
      roomId: this.roomId,
      senderId: this.profile.userId,
      timestamp: Date.now(),
      delta,
    });
  }

  /**
   * Request a soft lock on an element. Returns true if granted, false if denied.
   */
  acquireLock(elementId: string): Promise<boolean> {
    if (!this.roomId || !this.profile) return Promise.resolve(false);
    return new Promise((resolve) => {
      this.lockWaiters.set(elementId, { resolve });
      this._sendRaw({
        type: "ACQUIRE_LOCK",
        roomId: this.roomId!,
        senderId: this.profile!.userId,
        timestamp: Date.now(),
        elementId,
      });
      // Timeout after 3s if no server response
      setTimeout(() => {
        if (this.lockWaiters.has(elementId)) {
          this.lockWaiters.delete(elementId);
          resolve(false);
        }
      }, 3000);
    });
  }

  releaseLock(elementId: string): void {
    if (!this.roomId || !this.profile) return;
    this._sendRaw({
      type: "RELEASE_LOCK",
      roomId: this.roomId!,
      senderId: this.profile!.userId,
      timestamp: Date.now(),
      elementId,
    });
  }

  get currentPeers(): Map<string, CollaboratorPresence> {
    return this.peers;
  }

  get currentLocks(): Map<string, SubCircuitLock> {
    return this.locks;
  }

  get isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }

  // ── Internal Connection ─────────────────────────────────────────────────

  private _connect(): void {
    if (!this.roomId || !this.profile) return;
    this.onStatusChange("CONNECTING");

    const url = `${WS_BASE}/${this.roomId}/ws`;
    const ws = new WebSocket(url);
    this.socket = ws;

    ws.onopen = () => {
      this.reconnectAttempt = 0;
      // Send JOIN_ROOM as the very first message
      this._sendRaw({
        type: "JOIN_ROOM",
        roomId: this.roomId!,
        senderId: this.profile!.userId,
        timestamp: Date.now(),
        userProfile: {
          userId: this.profile!.userId,
          displayName: this.profile!.displayName,
          color: this.color,
          canvasMode: this.profile!.canvasMode ?? "2d",
        },
      });
      this._startHeartbeat();
      this.onStatusChange("CONNECTED");
    };

    ws.onmessage = (e) => this._handleMessage(e.data);

    ws.onerror = () => {
      // onclose will fire after this
    };

    ws.onclose = () => {
      this._stopHeartbeat();
      this.onStatusChange("OFFLINE");
      if (!this.intentionalClose) {
        this._scheduleReconnect();
      }
    };
  }

  private _scheduleReconnect(): void {
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempt), 30_000);
    this.reconnectAttempt++;
    console.log(`[Multiplayer] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempt})...`);
    this.reconnectTimer = setTimeout(() => this._connect(), delay);
  }

  private _sendRaw(msg: unknown): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(msg));
    }
  }

  private _startHeartbeat(): void {
    this._stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      this._sendRaw({
        type: "HEARTBEAT",
        roomId: this.roomId!,
        senderId: this.profile!.userId,
        timestamp: Date.now(),
      });
    }, HEARTBEAT_INTERVAL_MS);
  }

  private _stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  // ── Message Handling ────────────────────────────────────────────────────

  private _handleMessage(raw: string): void {
    let msg: MultiplayerMessage;
    try {
      msg = JSON.parse(raw) as MultiplayerMessage;
    } catch {
      console.warn("[Multiplayer] Invalid JSON from server:", raw.slice(0, 100));
      return;
    }

    switch (msg.type) {
      case "ROOM_STATE": {
        this.peers.clear();
        this.locks.clear();
        for (const peer of msg.peers) this.peers.set(peer.userId, peer);
        for (const lock of msg.locks) this.locks.set(lock.elementId, lock);
        this.onPresenceUpdate(new Map(this.peers));
        this.onLockChanged(new Map(this.locks));
        break;
      }

      case "PEER_JOINED": {
        this.peers.set(msg.peer.userId, msg.peer);
        this.onPresenceUpdate(new Map(this.peers));
        this.onPeerJoined(msg.peer);
        break;
      }

      case "PEER_LEFT": {
        this.peers.delete(msg.userId);
        this.onPresenceUpdate(new Map(this.peers));
        this.onPeerLeft(msg.userId);
        break;
      }

      case "PRESENCE_UPDATE": {
        this.peers.set(msg.peer.userId, msg.peer);
        this.onPresenceUpdate(new Map(this.peers));
        break;
      }

      case "DELTA": {
        this.onDeltaReceived(msg.delta as unknown as MultiplayerDelta);
        break;
      }

      case "LOCK_ACQUIRED": {
        this.locks.set(msg.lock.elementId, msg.lock);
        this.onLockChanged(new Map(this.locks));
        // Resolve waiter if this is our own lock
        const waiter = this.lockWaiters.get(msg.lock.elementId);
        if (waiter && msg.lock.lockedByUserId === this.profile?.userId) {
          this.lockWaiters.delete(msg.lock.elementId);
          waiter.resolve(true);
        }
        break;
      }

      case "LOCK_DENIED": {
        const waiter = this.lockWaiters.get(msg.elementId);
        if (waiter) {
          this.lockWaiters.delete(msg.elementId);
          waiter.resolve(false);
        }
        break;
      }

      case "LOCK_RELEASED": {
        this.locks.delete(msg.elementId);
        this.onLockChanged(new Map(this.locks));
        break;
      }
    }
  }
}

// ── Singleton ──────────────────────────────────────────────────────────────

/** Global singleton client. Import this directly in components or the store. */
export const multiplayerClient = new NeuroBoardMultiplayerClient();
