import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";

/* ── Shot 2: $0 / $5,000 Progress Bar ── */
/* Restored animation: fills, stutters, retracts, red pulse */

const COLORS = {
  bg: "#F8F9FA",
  barBg: "#2D2D44",
  fillStart: "#00B894",
  fillEnd: "#55EFC4",
  label: "#2D3436",
  labelDim: "#636E72",
};

export const Shot2ProgressBar: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const barW = 1000;
  const barH = 80;
  const barX = (1080 - barW) / 2;
  const barY = 880;

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

return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
      {/* Label - centered vertically */}
      <div style={{ position: "absolute", top: "32%", left: 0, width: "100%", display: "flex", justifyContent: "center", alignItems: "center", opacity: labelOpacity, flexDirection: "column", gap: 50 }}>
         <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 50, fontWeight: 800, color: COLORS.labelDim, letterSpacing: 4 }}>
           FUNDRAISING
         </span>
         <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 110, fontWeight: 900, color: COLORS.label, letterSpacing: 5 }}>
           $0 / $2,000
         </span>
       </div>

       {/* Bar - centered */}
       <div style={{ position: "absolute", left: barX, top: "58%", width: barW, height: barH, borderRadius: barH / 2, backgroundColor: COLORS.barBg, overflow: "hidden", transform: `scaleX(${entranceSpring})`, transformOrigin: "left center" }}>
         {/* Fill */}
         <div style={{ 
           width: `${fillProgress * 100}%`, 
           height: "100%", 
           borderRadius: barH / 2, 
           background: `linear-gradient(90deg, ${COLORS.fillStart}, ${COLORS.fillEnd})`,
           transition: "none",
         }} />
       </div>
    </AbsoluteFill>
  );
};