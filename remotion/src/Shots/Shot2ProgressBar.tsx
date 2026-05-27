import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";

/* ── Shot 2: $0 / $5,000 Progress Bar ── */
/* Restored animation: fills, stutters, retracts, red pulse */

const COLORS = {
  bg: "#1E1E2E",
  barBg: "#2D2D44",
  fillStart: "#00B894",
  fillEnd: "#55EFC4",
  label: "#FFFFFF",
  labelDim: "#636E72",
  redPulse: "#D63031",
};

export const Shot2ProgressBar: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const barW = 920;
  const barH = 56;
  const barX = (1080 - barW) / 2;
  const barY = 900;

  const entranceSpring = spring({ frame: frame - 5, fps, config: { damping: 14, stiffness: 90 } });
  const labelOpacity = interpolate(frame - 3, [0, 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  // Phase 1: Fill up (frames 10-40)
  const fill1 = interpolate(frame, [10, 40], [0, 0.7], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Phase 2: Stutter and retract (frames 45-80)
  let fillProgress: number;
  
  if (frame < 45) {
    fillProgress = fill1;
  } else if (frame < 80) {
    const stutterFrame = frame - 45;
    if (stutterFrame < 8) {
      fillProgress = interpolate(stutterFrame, [0, 8], [0.7, 0.5], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
    } else if (stutterFrame < 15) {
      fillProgress = interpolate(stutterFrame, [8, 15], [0.5, 0.6], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
    } else if (stutterFrame < 25) {
      fillProgress = interpolate(stutterFrame, [15, 25], [0.6, 0.2], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
    } else {
      fillProgress = interpolate(stutterFrame, [25, 35], [0.2, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
    }
  } else {
    fillProgress = 0;
  }

  // Red pulse on empty bar (frames 85-120)
  const pulseFrame = frame - 85;
  const redPulseOpacity = interpolate(
    pulseFrame,
    [0, 10, 20, 30, 35],
    [0, 0.4, 0, 0.3, 0],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
      {/* Title */}
      <div style={{ position: "absolute", top: 220, left: 0, width: "100%", textAlign: "center", opacity: labelOpacity }}>
        <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 30, fontWeight: 700, color: COLORS.labelDim, letterSpacing: 6 }}>
          FUNDRAISING
        </span>
      </div>

      {/* Label */}
      <div style={{ position: "absolute", top: barY - 130, left: barX, width: barW, display: "flex", justifyContent: "space-between", alignItems: "flex-end", opacity: labelOpacity }}>
        <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 22, fontWeight: 500, color: COLORS.labelDim, letterSpacing: 2 }}>
          Current
        </span>
        <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 68, fontWeight: 800, color: COLORS.label, letterSpacing: 2 }}>
          $0 / $2,000
        </span>
      </div>

      {/* Bar */}
      <div style={{ position: "absolute", left: barX, top: barY, width: barW, height: barH, borderRadius: barH / 2, backgroundColor: COLORS.barBg, overflow: "hidden", transform: `scaleX(${entranceSpring})`, transformOrigin: "left center" }}>
        {/* Fill */}
        <div style={{ 
          width: `${fillProgress * 100}%`, 
          height: "100%", 
          borderRadius: barH / 2, 
          background: `linear-gradient(90deg, ${COLORS.fillStart}, ${COLORS.fillEnd})`,
          transition: "none",
        }} />
        
        {/* Red pulse overlay */}
        {redPulseOpacity > 0 && (
          <div
            style={{
              position: "absolute",
              left: 0,
              top: 0,
              width: "100%",
              height: "100%",
              borderRadius: barH / 2,
              background: `radial-gradient(ellipse at 50% 50%, ${COLORS.redPulse}88 0%, ${COLORS.redPulse}44 40%, transparent 70%)`,
              opacity: redPulseOpacity,
            }}
          />
        )}
      </div>

      {/* Subtitle */}
      <div style={{ position: "absolute", top: barY + 100, left: 0, width: "100%", textAlign: "center", opacity: interpolate(frame, [12, 22], [0, 0.6], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
        <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 22, fontWeight: 400, color: COLORS.labelDim, letterSpacing: 3 }}>
          Help us reach our goal
        </span>
      </div>
    </AbsoluteFill>
  );
};