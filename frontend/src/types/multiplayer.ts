/**
 * frontend/src/types/multiplayer.ts
 * =====================================
 * All shared TypeScript types for the NeuroBoard real-time multiplayer
 * collaboration engine. Defines the wire protocol, presence model, delta
 * mutation schema, and sub-circuit soft-lock structures.
 */

// ── Op Types ───────────────────────────────────────────────────────────────

export type OpType =
  | "MOVE_COMPONENT"
  | "ROUTE_TRACE"
  | "DELETE_ELEMENT"
  | "ADD_WIRE"
  | "UPDATE_VALUE"
  | "ADD_COMPONENT"
  | "DELETE_WIRE";

// ── Presence ───────────────────────────────────────────────────────────────

export interface CursorPosition {
  x: number;
  y: number;
}

export interface CollaboratorPresence {
  userId: string;
  displayName: string;
  /** Hex color string, e.g. "#818CF8". Assigned deterministically from userId. */
  color: string;
  cursor: CursorPosition | null;
  /** Which canvas the collaborator is currently viewing. */
  canvasMode: "2d" | "3d" | "schematic";
  /** Reference of the currently selected/editing element, e.g. "U1", "net:GND". */
  selectedElementId: string | null;
  /** Unix timestamp ms of last received heartbeat. */
  lastSeen: number;
}

// ── Delta Mutations ────────────────────────────────────────────────────────

export interface MultiplayerDelta {
  roomId: string;
  authorId: string;
  /** Monotonically increasing per-client version counter. */
  version: number;
  opType: OpType;
  /** Component reference, net name, or element ID being mutated. */
  targetId: string;
  /** Op-specific data (coordinates, values, net names, etc.) */
  payload: Record<string, unknown>;
  timestamp: number;
}

// ── Sub-Circuit Soft Locks ─────────────────────────────────────────────────

export interface SubCircuitLock {
  elementId: string;
  lockedByUserId: string;
  lockedByName: string;
  lockedByColor: string;
  lockedAt: number;
  /** Unix timestamp ms after which the lock automatically expires. */
  expiresAt: number;
}

// ── Wire Protocol Messages (Discriminated Union) ───────────────────────────

interface BaseMsg {
  roomId: string;
  senderId: string;
  timestamp: number;
}

export interface JoinRoomMsg extends BaseMsg {
  type: "JOIN_ROOM";
  userProfile: Pick<CollaboratorPresence, "userId" | "displayName" | "color" | "canvasMode">;
}

export interface LeaveRoomMsg extends BaseMsg {
  type: "LEAVE_ROOM";
}

export interface CursorMoveMsg extends BaseMsg {
  type: "CURSOR_MOVE";
  x: number;
  y: number;
  canvasMode: CollaboratorPresence["canvasMode"];
}

export interface DeltaMsg extends BaseMsg {
  type: "DELTA";
  delta: MultiplayerDelta;
}

export interface AcquireLockMsg extends BaseMsg {
  type: "ACQUIRE_LOCK";
  elementId: string;
}

export interface ReleaseLockMsg extends BaseMsg {
  type: "RELEASE_LOCK";
  elementId: string;
}

export interface HeartbeatMsg extends BaseMsg {
  type: "HEARTBEAT";
}

// ── Server → Client Broadcast Messages ────────────────────────────────────

export interface PeerJoinedMsg {
  type: "PEER_JOINED";
  peer: CollaboratorPresence;
}

export interface PeerLeftMsg {
  type: "PEER_LEFT";
  userId: string;
}

export interface PresenceUpdateMsg {
  type: "PRESENCE_UPDATE";
  peer: CollaboratorPresence;
}

export interface LockAcquiredMsg {
  type: "LOCK_ACQUIRED";
  lock: SubCircuitLock;
}

export interface LockDeniedMsg {
  type: "LOCK_DENIED";
  elementId: string;
  lockedBy: string;
}

export interface LockReleasedMsg {
  type: "LOCK_RELEASED";
  elementId: string;
}

/** Initial state snapshot sent to newly joined peer. */
export interface RoomStateMsg {
  type: "ROOM_STATE";
  peers: CollaboratorPresence[];
  locks: SubCircuitLock[];
}

// ── Union of all message types ─────────────────────────────────────────────

export type MultiplayerMessage =
  | JoinRoomMsg
  | LeaveRoomMsg
  | CursorMoveMsg
  | DeltaMsg
  | AcquireLockMsg
  | ReleaseLockMsg
  | HeartbeatMsg
  | PeerJoinedMsg
  | PeerLeftMsg
  | PresenceUpdateMsg
  | LockAcquiredMsg
  | LockDeniedMsg
  | LockReleasedMsg
  | RoomStateMsg;

// ── Utility ────────────────────────────────────────────────────────────────

/**
 * Deterministically assigns a color to a userId so the same person always
 * appears in the same color across all sessions.
 */
export function userIdToColor(userId: string): string {
  const palette = [
    "#818CF8", // indigo
    "#34D399", // emerald
    "#F472B6", // pink
    "#FBBF24", // amber
    "#60A5FA", // blue
    "#A78BFA", // violet
    "#F87171", // red
    "#2DD4BF", // teal
  ];
  let hash = 0;
  for (let i = 0; i < userId.length; i++) {
    hash = (hash * 31 + userId.charCodeAt(i)) >>> 0;
  }
  return palette[hash % palette.length];
}
