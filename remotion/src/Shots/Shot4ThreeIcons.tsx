import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";

/* ── Shot 4: Three Icons Sequence ── */
/* Shorts: 1080×1920 — BIG vertical layout, capitalized labels */

const COLORS = { bg: "#F8F9FA", crown: "#FDCB6E", mask: "#6C5CE7", money: "#00B894", labelText: "#2D3436", labelLight: "#636E72" };

interface IconDef {
  label: string; sublabel: string; color: string; iconBg: string; drawIcon: (size: number) => React.ReactNode;
}

const ICONS_DATA: IconDef[] = [
  { label: "The Wins", sublabel: "celebrate success", color: COLORS.crown, iconBg: "#FFF3D6",
    drawIcon: (size) => (
      <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
        <path d="M12 48 L8 20 L20 30 L32 16 L44 30 L56 20 L52 48 Z" fill={COLORS.crown} stroke="#E0A800" strokeWidth={2} strokeLinejoin="round" />
        <circle cx={32} cy={38} r={7} fill="#E0A800" />
      </svg>
    ) },
  { label: "The Embarrassments", sublabel: "lessons learned", color: COLORS.mask, iconBg: "#EEEBFF",
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
  { label: "The Money", sublabel: "make it count", color: COLORS.money, iconBg: "#D4FAED",
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

  const rowGap = 340;
  const startY = 300;
  const iconSize = 130;

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg, display: "flex", alignItems: "center", justifyContent: "flex-start", paddingTop: startY }}>
      {ICONS_DATA.map((icon, i) => {
        const appearFrame = i * 35;
        const local = frame - appearFrame;
        const bounce = spring({ frame: local, fps, config: { damping: 10, stiffness: 150, mass: 0.8 } });
        const opacity = interpolate(local, [0, 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        const labelOpacity = interpolate(local, [6, 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        const labelSlide = interpolate(local - 6, [0, 12], [20, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

        if (local < 0) return null;

        return (
          <div key={i} style={{ display: "flex", flexDirection: "row", alignItems: "center", gap: 60, height: rowGap, opacity, transform: `scale(${bounce})` }}>
            <div style={{ width: iconSize + 40, height: iconSize + 40, borderRadius: 36, backgroundColor: icon.iconBg, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 8px 28px rgba(0,0,0,0.06)", flexShrink: 0 }}>
              {icon.drawIcon(iconSize)}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, opacity: labelOpacity, transform: `translateY(${labelSlide}px)` }}>
              <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 42, fontWeight: 700, color: COLORS.labelText, letterSpacing: 1 }}>
                {icon.label}
              </span>
              <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 24, fontWeight: 400, color: COLORS.labelLight, letterSpacing: 2 }}>
                {icon.sublabel}
              </span>
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};