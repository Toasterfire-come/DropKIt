import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from "remotion";

/* ── Shot 5: Bullet Points (fullscreen card) ── */
/* Shorts: 1080×1920 — card fills screen, bullets slide in horizontally only */

const COLORS = { bg: "#FFFFFF", bullet: "#00B894", textPrimary: "#2D3436", textSecondary: "#636E72" };

const BULLETS = [
  { text: "Real project" },
  { text: "Real parts" },
  { text: "Solid plan you can modify" },
];

export const Shot5CardBullets: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const bulletWidth = 960;

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 60 }}>
        {/* Title — always visible, no animation */}
        <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 56, fontWeight: 800, color: "#B2BEC3", letterSpacing: 10 }}>
          WHAT YOU GET
        </span>

        {/* Bullets */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 100 }}>
          {BULLETS.map((bullet, i) => {
          const appearFrame = 8 + i * 25;
          const local = frame - appearFrame;
          const slideX = interpolate(local, [0, 22], [-80, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const opacity = interpolate(local, [0, 15], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

          // Always render to keep flex stack stable — invisible until appearFrame
          const isVisible = local >= 0;

          return (
            <div key={i} style={{ width: bulletWidth, display: "flex", alignItems: "center", gap: 40, opacity: isVisible ? opacity : 0, transform: `translateX(${isVisible ? slideX : -80}px)` }}>
              <div style={{ minWidth: 48, height: 48, borderRadius: "50%", backgroundColor: COLORS.bullet, flexShrink: 0 }} />
              <div style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 80, fontWeight: 800, color: COLORS.textPrimary, letterSpacing: 1, lineHeight: 1.2 }}>
                {bullet.text}
              </div>
            </div>
          );
        })}
      </div>
      </div>
    </AbsoluteFill>
  );
};