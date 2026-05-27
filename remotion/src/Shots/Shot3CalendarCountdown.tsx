import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";

/* ── Shot 3: Back-to-School Calendar Countdown ── */
/* August 10 — Calendar only, no number popup */

const COLORS = {
  bg: "#F8F9FA",
  calendarBody: "#FFFFFF",
  calendarBorder: "#DEE2E6",
  calendarHeader: "#E17055",
  circleRed: "#D63031",
  tickGray: "#DFE6E9",
  labelText: "#2D3436",
};

export const Shot3CalendarCountdown: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const centerX = 540;
  const calendarTop = 100;

  // ── Clock ticks ──
  const tickCount = 48;
  const ticks: React.ReactNode[] = [];
  for (let i = 0; i < tickCount; i++) {
    const angle = (i / tickCount) * Math.PI * 2 - Math.PI / 2;
    const outerR = 520;
    const innerR = 495;
    const tickProgress = interpolate(frame, [0, 25], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    const tickThreshold = i / tickCount;
    const showTick = tickProgress > tickThreshold;
    const tickOpacity = showTick ? interpolate(frame - i * 0.5, [0, 12], [0, 0.3], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;

    if (showTick && tickOpacity > 0) {
      const cx = centerX;
      const cy = calendarTop + 250;
      ticks.push(
        <line key={i} x1={cx + Math.cos(angle) * innerR} y1={cy + Math.sin(angle) * innerR} x2={cx + Math.cos(angle) * outerR} y2={cy + Math.sin(angle) * outerR} stroke={COLORS.tickGray} strokeWidth={2.5} opacity={tickOpacity} />
      );
    }
  }

  const calendarSpring = spring({ frame: frame - 5, fps, config: { damping: 14, stiffness: 100 } });
  const calendarOpacity = interpolate(frame - 5, [0, 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg, display: "flex", alignItems: "center", justifyContent: "flex-start", overflow: "hidden" }}>
      <svg style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", pointerEvents: "none" }}>{ticks}</svg>

      {/* BIG Calendar */}
      <div style={{ position: "absolute", left: centerX - 220, top: calendarTop, width: 440, height: 490, borderRadius: 32, backgroundColor: COLORS.calendarBody, border: `3px solid ${COLORS.calendarBorder}`, opacity: calendarOpacity, transform: `scale(${calendarSpring})`, boxShadow: "0 16px 48px rgba(0,0,0,0.08)", overflow: "hidden", display: "flex", flexDirection: "column" }}>
        <div style={{ height: 80, backgroundColor: COLORS.calendarHeader, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 32, fontWeight: 700, color: "#FFFFFF", letterSpacing: 5 }}>AUGUST</span>
        </div>
        <div style={{ padding: "18px 18px 16px", flex: 1, display: "flex", flexDirection: "column" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 4, marginBottom: 10 }}>
            {["S", "M", "T", "W", "T", "F", "S"].map((d, i) => (
              <div key={i} style={{ textAlign: "center", fontSize: 16, fontWeight: 600, color: "#ADB5BD", padding: "4px 0" }}>{d}</div>
            ))}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 4, flex: 1 }}>
            {Array.from({ length: 31 }, (_, i) => {
              const date = i + 1;
              const isCircled = date === 10;
              return (
                <div key={i} style={{ textAlign: "center", fontSize: 17, fontWeight: isCircled ? 800 : 400, color: isCircled ? "#FFFFFF" : "#2D3436", padding: "7px 0", borderRadius: "50%", backgroundColor: isCircled ? COLORS.circleRed : "transparent", width: 42, height: 42, display: "flex", alignItems: "center", justifyContent: "center", margin: "auto" }}>
                  {date}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Tagline */}
      <div style={{ position: "absolute", bottom: 120, left: 0, width: "100%", textAlign: "center", opacity: interpolate(frame, [20, 35], [0, 0.5], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
        <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 20, fontWeight: 400, color: "#636E72", letterSpacing: 4 }}>
          Back-to-School Countdown
        </span>
      </div>
    </AbsoluteFill>
  );
};