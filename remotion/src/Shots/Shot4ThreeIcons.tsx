import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";

/* ── Shot 4: Three Icons Sequence ── */
/* Shorts: 1080×1920 — BIG vertical layout, capitalized labels */

const COLORS = { bg: "#F8F9FA", crown: "#FDCB6E", mask: "#6C5CE7", money: "#00B894", labelText: "#2D3436", labelLight: "#636E72" };

interface IconDef {
  label: string; color: string; iconBg: string; drawIcon: (size: number) => React.ReactNode;
}

const ICONS_DATA: IconDef[] = [
  { label: "The Wins", color: COLORS.crown, iconBg: "#FFF3D6",
    drawIcon: (size) => (
      <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
        <path d="M12 48 L8 20 L20 30 L32 16 L44 30 L56 20 L52 48 Z" fill={COLORS.crown} stroke="#E0A800" strokeWidth={2} strokeLinejoin="round" />
        <circle cx={32} cy={38} r={7} fill="#E0A800" />
      </svg>
    ) },
  { label: "The Embarrassments", color: COLORS.mask, iconBg: "#EEEBFF",
    drawIcon: (size) => (
      <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
        <ellipse cx={22} cy={30} rx={15} ry={17} fill={COLORS.mask} opacity={0.85} />
        <ellipse cx={42} cy={30} rx={15} ry={17} fill={COLORS.mask} opacity={0.85} />
        <circle cx={18} cy={26} r={5} fill="#FFFFFF" /><circle cx={18} cy={26} r={2.5} fill="#2D3436" />
        <circle cx={38} cy={26} r={5} fill="#FFFFFF" /><circle cx={38} cy={26} r={2.5} fill="#2D3436" />
        <path d="M14 34 Q22 40 30 34" stroke="#FFFFFF" strokeWidth={2.5} fill="none" strokeLinecap="round" />
        <path d="M34 34 Q42 44 50 34" stroke="#FFFFFF" strokeWidth={2.5} fill="none" strokeLinecap="round" />
      </svg>
    ) },
  { label: "The Money", color: COLORS.money, iconBg: "#D4FAED",
    drawIcon: (size) => (
      <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
        <path d="M24 20 Q20 32 20 40 Q20 52 32 52 Q44 52 44 40 Q44 32 40 20 Z" fill={COLORS.money} stroke="#009874" strokeWidth={2} />
        <path d="M24 20 L28 12 L36 12 L40 20" fill={COLORS.money} stroke="#009874" strokeWidth={2} />
        <text x={32} y={39} textAnchor="middle" fill="#FFFFFF" fontSize={14} fontWeight={900} fontFamily="Helvetica">$</text>
      </svg>
    ) },
];

export const Shot4ThreeIcons: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const centerX = 540;
  const stepHeight = 170;
  const stepGap = 50;
  const stepWidth = 700;
  const horPadding = 50;
  const totalHeight = ICONS_DATA.length * (stepHeight + stepGap) - stepGap;
  const startY = (1920 - totalHeight) / 2 - 80;

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg, overflow: "hidden" }}>
      {ICONS_DATA.map((icon, i) => {
        const appearFrame = i * 30;
        const local = frame - appearFrame;
        const bounce = spring({ frame: local, fps, config: { damping: 10, stiffness: 150, mass: 0.8 } });
        const opacity = interpolate(local, [0, 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

        if (local < 0) return null;

        const y = startY + i * (stepHeight + stepGap);

        return (
          <div key={i} style={{ position: "absolute", left: centerX - stepWidth / 2, top: y, width: stepWidth, display: "flex", flexDirection: "row", alignItems: "center", gap: 50, height: stepHeight, padding: `0 ${horPadding}px`, opacity, transform: `scale(${bounce})` }}>
            <div style={{ width: 70, height: 70, borderRadius: 35, backgroundColor: icon.iconBg, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 12px 35px rgba(0,0,0,0.15)", flexShrink: 0 }}>
              {icon.drawIcon(56)}
            </div>
            <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 48, fontWeight: 800, color: COLORS.labelText, letterSpacing: 1, textWrap: "balance" }}>
              {icon.label}
            </span>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};