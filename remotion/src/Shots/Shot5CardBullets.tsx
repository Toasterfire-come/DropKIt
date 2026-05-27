import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";

/* ── Shot 5: White Card, Three Bullet Points ── */
/* Shorts: 1080×1920 — EXTRA BIG text */

const COLORS = { bg: "#E9ECEF", card: "#FFFFFF", bullet: "#00B894", textPrimary: "#2D3436", textSecondary: "#636E72", accent: "#0984E3" };

const BULLETS = [
  { text: "Real project", sub: "Built for actual use, not theory" },
  { text: "Real parts", sub: "Every component has purpose" },
  { text: "Solid plan you can modify", sub: "Flexible foundation for your needs" },
];

export const Shot5CardBullets: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const cardSpring = spring({ frame: frame - 5, fps, config: { damping: 12, stiffness: 100 } });
  const cardOpacity = interpolate(frame - 5, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const cardW = 960;
  const cardH = 860;
  const cardX = (1080 - cardW) / 2;
  const cardY = (1920 - cardH) / 2;

  const titleOpacity = interpolate(frame - 5, [0, 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ position: "absolute", top: cardY - 80, left: 0, width: "100%", textAlign: "center", opacity: titleOpacity }}>
        <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 30, fontWeight: 600, color: "#ADB5BD", letterSpacing: 5 }}>WHAT YOU GET</span>
      </div>

      {/* BIG Card */}
      <div style={{ position: "absolute", left: cardX, top: cardY, width: cardW, height: cardH, borderRadius: 48, backgroundColor: COLORS.card, boxShadow: "0 20px 64px rgba(0,0,0,0.06)", opacity: cardOpacity, transform: `scale(${cardSpring})`, display: "flex", flexDirection: "column", justifyContent: "center", padding: "0 80px", overflow: "hidden" }}>
        <div style={{ position: "absolute", left: 0, top: 60, width: 8, height: "calc(100% - 120px)", backgroundColor: COLORS.accent, opacity: 0.12, borderRadius: "0 4px 4px 0" }} />

        {BULLETS.map((bullet, i) => {
          const appearFrame = 15 + i * 30;
          const local = frame - appearFrame;
          const slideX = interpolate(local, [0, 16], [-50, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const opacity = interpolate(local, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const dotScale = spring({ frame: local, fps, config: { damping: 12, stiffness: 180 } });

          if (local < 0) return null;

          return (
            <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 32, marginBottom: i < BULLETS.length - 1 ? 60 : 0, opacity, transform: `translateX(${slideX}px)` }}>
              <div style={{ minWidth: 30, height: 30, borderRadius: "50%", backgroundColor: COLORS.bullet, marginTop: 6, transform: `scale(${dotScale})`, boxShadow: `0 0 18px ${COLORS.bullet}33`, flexShrink: 0 }} />
              <div>
                <div style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 44, fontWeight: 700, color: COLORS.textPrimary, letterSpacing: 0.5, lineHeight: 1.2 }}>
                  {bullet.text}
                </div>
                <div style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 24, fontWeight: 400, color: COLORS.textSecondary, letterSpacing: 0.5, marginTop: 8, lineHeight: 1.4 }}>
                  {bullet.sub}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};