/**
 * frontend/src/components/inspector/CollaboratorPills.tsx
 * =========================================================
 * Top-right avatar pill row showing all live active collaborators in the session.
 *
 * Features:
 *   - Up to 5 avatar circles (initials + collaborator color)
 *   - Green live pulse indicator dot
 *   - "+N more" overflow label when > 5 collaborators
 *   - Tooltip showing full display name on hover
 */

import React, { useState } from "react";
import { Users } from "lucide-react";
import { useNeuroStore } from "../../store/useNeuroStore";
import type { CollaboratorPresence } from "../../types/multiplayer";

const MAX_VISIBLE = 5;

// ── Avatar Pill ─────────────────────────────────────────────────────────────

interface AvatarProps {
  peer: CollaboratorPresence;
}

const AvatarPill: React.FC<AvatarProps> = ({ peer }) => {
  const [hovered, setHovered] = useState(false);
  const initials = peer.displayName
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const isStale = Date.now() - peer.lastSeen > 8_000; // 8s = probably gone

  return (
    <div
      style={{ position: "relative" }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Avatar circle */}
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: "50%",
          backgroundColor: peer.color,
          border: "2px solid rgba(255,255,255,0.15)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "12px",
          fontWeight: 700,
          fontFamily: "Inter, sans-serif",
          color: "#fff",
          cursor: "default",
          userSelect: "none",
          boxShadow: `0 0 8px ${peer.color}66`,
          transition: "transform 0.15s ease",
          transform: hovered ? "scale(1.15)" : "scale(1)",
        }}
      >
        {initials}
      </div>

      {/* Live status dot */}
      {!isStale && (
        <span
          style={{
            position: "absolute",
            bottom: 0,
            right: 0,
            width: 9,
            height: 9,
            borderRadius: "50%",
            backgroundColor: "#22C55E",
            border: "2px solid #0f172a",
            animation: "neuro-live-pulse 2s ease-in-out infinite",
          }}
        />
      )}

      {/* Tooltip */}
      {hovered && (
        <div
          style={{
            position: "absolute",
            bottom: -30,
            left: "50%",
            transform: "translateX(-50%)",
            backgroundColor: "rgba(15,23,42,0.95)",
            color: "#e2e8f0",
            fontSize: "11px",
            fontWeight: 500,
            fontFamily: "Inter, sans-serif",
            padding: "4px 8px",
            borderRadius: "6px",
            whiteSpace: "nowrap",
            border: "1px solid rgba(255,255,255,0.1)",
            pointerEvents: "none",
            zIndex: 100,
          }}
        >
          {peer.displayName}
          <span style={{ color: "#64748b", marginLeft: 4 }}>
            · {peer.canvasMode}
          </span>
        </div>
      )}
    </div>
  );
};

// ── Main Component ──────────────────────────────────────────────────────────

export const CollaboratorPills: React.FC = () => {
  const collaborators = useNeuroStore((s) => s.collaborators);
  const multiplayerStatus = useNeuroStore((s) => s.multiplayerStatus);

  const peers = Array.from(collaborators.values());
  const visible = peers.slice(0, MAX_VISIBLE);
  const overflow = peers.length - MAX_VISIBLE;

  if (multiplayerStatus === "OFFLINE" && peers.length === 0) {
    return null; // nothing to show
  }

  return (
    <>
      <style>{`
        @keyframes neuro-live-pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.7; transform: scale(1.3); }
        }
      `}</style>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "6px",
          padding: "4px 10px",
          backgroundColor: "rgba(15,23,42,0.7)",
          backdropFilter: "blur(8px)",
          border: "1px solid rgba(255,255,255,0.1)",
          borderRadius: "20px",
        }}
      >
        {/* Icon */}
        <Users size={14} style={{ color: "#64748b" }} />

        {/* Connection status dot */}
        <span
          style={{
            width: 7,
            height: 7,
            borderRadius: "50%",
            backgroundColor:
              multiplayerStatus === "CONNECTED"
                ? "#22C55E"
                : multiplayerStatus === "CONNECTING"
                ? "#FBBF24"
                : "#64748b",
            flexShrink: 0,
          }}
        />

        {/* Avatar stack */}
        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          {visible.map((peer) => (
            <AvatarPill key={peer.userId} peer={peer} />
          ))}

          {overflow > 0 && (
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: "50%",
                backgroundColor: "rgba(255,255,255,0.1)",
                border: "2px solid rgba(255,255,255,0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "11px",
                fontWeight: 600,
                color: "#94a3b8",
                fontFamily: "Inter, sans-serif",
              }}
            >
              +{overflow}
            </div>
          )}

          {peers.length === 0 && multiplayerStatus !== "OFFLINE" && (
            <span
              style={{
                fontSize: "11px",
                color: "#64748b",
                fontFamily: "Inter, sans-serif",
                padding: "0 2px",
              }}
            >
              {multiplayerStatus === "CONNECTING" ? "Connecting..." : "Only you"}
            </span>
          )}
        </div>
      </div>
    </>
  );
};

export default CollaboratorPills;
