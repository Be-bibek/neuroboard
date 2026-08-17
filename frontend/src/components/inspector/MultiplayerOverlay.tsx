/**
 * frontend/src/components/inspector/MultiplayerOverlay.tsx
 * ==========================================================
 * Absolutely-positioned, pointer-events-none canvas overlay that renders:
 *   1. Live collaborator cursors with name tags (CSS transform animation)
 *   2. Soft-lock bounding boxes around components being edited by peers
 *
 * Mount this inside a `position: relative` PCB canvas container.
 */

import React from "react";
import { Lock } from "lucide-react";
import { useNeuroStore } from "../../store/useNeuroStore";
import type { CollaboratorPresence, SubCircuitLock } from "../../types/multiplayer";

// ── Cursor Component ────────────────────────────────────────────────────────

interface LiveCursorProps {
  peer: CollaboratorPresence;
}

const LiveCursor: React.FC<LiveCursorProps> = ({ peer }) => {
  if (!peer.cursor) return null;
  const { x, y } = peer.cursor;

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        top: 0,
        transform: `translate(${x}px, ${y}px)`,
        transition: "transform 100ms linear",
        pointerEvents: "none",
        zIndex: 50,
      }}
    >
      {/* Cursor arrow */}
      <svg width="16" height="20" viewBox="0 0 16 20" fill="none">
        <path
          d="M0 0L0 16L4.5 11.5L7 18L9 17L6.5 10.5L12 10.5L0 0Z"
          fill={peer.color}
          stroke="rgba(0,0,0,0.4)"
          strokeWidth="1"
        />
      </svg>

      {/* Name tag */}
      <div
        style={{
          position: "absolute",
          top: 18,
          left: 4,
          backgroundColor: peer.color,
          color: "#fff",
          fontSize: "11px",
          fontWeight: 600,
          fontFamily: "Inter, sans-serif",
          padding: "2px 7px",
          borderRadius: "12px",
          whiteSpace: "nowrap",
          boxShadow: `0 2px 8px ${peer.color}55`,
          letterSpacing: "0.02em",
        }}
      >
        {peer.displayName}
      </div>
    </div>
  );
};

// ── Lock Box Component ──────────────────────────────────────────────────────

interface LockBoxProps {
  lock: SubCircuitLock;
  /** Position of the locked element on the canvas in CSS pixels. */
  canvasX: number;
  canvasY: number;
  width?: number;
  height?: number;
}

const LockBox: React.FC<LockBoxProps> = ({
  lock,
  canvasX,
  canvasY,
  width = 80,
  height = 60,
}) => {
  return (
    <div
      style={{
        position: "absolute",
        left: canvasX - width / 2 - 6,
        top: canvasY - height / 2 - 6,
        width: width + 12,
        height: height + 12,
        border: `2px solid ${lock.lockedByColor}`,
        borderRadius: "6px",
        pointerEvents: "none",
        zIndex: 40,
        animation: "neuro-pulse-border 1.5s ease-in-out infinite",
        boxShadow: `0 0 12px ${lock.lockedByColor}44, inset 0 0 12px ${lock.lockedByColor}11`,
      }}
    >
      {/* Label */}
      <div
        style={{
          position: "absolute",
          top: -24,
          left: -2,
          backgroundColor: lock.lockedByColor,
          color: "#fff",
          fontSize: "10px",
          fontWeight: 600,
          fontFamily: "Inter, sans-serif",
          padding: "2px 7px",
          borderRadius: "8px",
          whiteSpace: "nowrap",
          display: "flex",
          alignItems: "center",
          gap: "4px",
        }}
      >
        <Lock size={10} />
        {lock.elementId} · {lock.lockedByName}
      </div>
    </div>
  );
};

// ── Main Overlay ────────────────────────────────────────────────────────────

interface MultiplayerOverlayProps {
  /** Width of the canvas container in CSS pixels. */
  containerWidth?: number;
  /** Height of the canvas container in CSS pixels. */
  containerHeight?: number;
}

export const MultiplayerOverlay: React.FC<MultiplayerOverlayProps> = ({
  containerWidth = 800,
  containerHeight = 600,
}) => {
  const collaborators = useNeuroStore((s) => s.collaborators);
  const activeLocks = useNeuroStore((s) => s.activeLocks);
  const boardPositions = useNeuroStore((s) => s.boardPositions);

  const peers = Array.from(collaborators.values());
  const locks = Array.from(activeLocks.values());

  return (
    <>
      {/* Inject keyframes once */}
      <style>{`
        @keyframes neuro-pulse-border {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>

      <div
        style={{
          position: "absolute",
          inset: 0,
          width: containerWidth,
          height: containerHeight,
          pointerEvents: "none",
          overflow: "hidden",
          zIndex: 30,
        }}
      >
        {/* Live Cursors */}
        {peers.map((peer) => (
          <LiveCursor key={peer.userId} peer={peer} />
        ))}

        {/* Lock Bounding Boxes */}
        {locks.map((lock) => {
          const pos = boardPositions[lock.elementId];
          if (!pos) return null;
          // board positions are in mm; scale to pixels (approx 4px/mm for canvas)
          const SCALE = 4;
          return (
            <LockBox
              key={lock.elementId}
              lock={lock}
              canvasX={pos.x * SCALE}
              canvasY={pos.y * SCALE}
            />
          );
        })}
      </div>
    </>
  );
};

export default MultiplayerOverlay;
