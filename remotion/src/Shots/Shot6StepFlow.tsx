import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";

/* ── Shot 6: Step Flow Diagram + Progress Bar ── */
/* Animated 6-step flow building across screen, then $0 / $2,000 bar */

const COLORS = {
  bg: "#FFFFFF",
  stepBg: "#F8F9FA",
  stepBorder: "#DEE2E6",
  stepActive: "#00B894",
  stepText: "#2D3436",
  arrowGray: "#B2BEC3",
};

const STEPS = [
  { text: "You pledge", icon: "🤝" },
  { text: "Total tracked publicly", icon: "📊" },
  { text: "Hits $2,000", icon: "🎯" },
  { text: "I collect", icon: "💰" },
  { text: "Announced on socials", icon: "📣" },
];

export const Shot6StepFlow: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const centerX = 540;
  const stepHeight = 230;
  const stepGap = 65;
  const stepWidth = 840;

  // ── Title ──
  const titleOpacity = interpolate(frame, [3, 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  // ── Render steps centered vertically ──
  const renderSteps = () => {
    const elements: React.ReactNode[] = [];
    const totalHeight = STEPS.length * (stepHeight + stepGap) - stepGap;
    const startYCentered = (1920 - totalHeight) / 2 - 60; // Center with offset for title

    for (let i = 0; i < STEPS.length; i++) {
      const step = STEPS[i];
      const y = startYCentered + i * (stepHeight + stepGap);

      const appearFrame = 10 + i * 20;
      const local = frame - appearFrame;

      const springScale = spring({ frame: local, fps, config: { damping: 12, stiffness: 150 } });
      const opacity = interpolate(local, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

      // Arrow to next step
      const showArrow = i < STEPS.length - 1 && local > 5;
      const arrowOpacity = showArrow ? interpolate(local - 5, [0, 8], [0, 0.6], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;

      if (local < 0) continue;

      elements.push(
        <React.Fragment key={i}>
          {/* Vertical arrow */}
          {showArrow && arrowOpacity > 0 && (
            <svg style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", pointerEvents: "none" }}>
              <line
                x1={centerX}
                y1={y + stepHeight / 2}
                x2={centerX}
                y2={y + stepHeight / 2 + stepGap}
                stroke={COLORS.arrowGray}
                strokeWidth={5}
                strokeDasharray="12 8"
                opacity={arrowOpacity}
              />
              <polygon
                points={`${centerX - 12},${y + stepHeight / 2 + stepGap - 5} ${centerX + 12},${y + stepHeight / 2 + stepGap - 5} ${centerX},${y + stepHeight / 2 + stepGap + 12}`}
                fill={COLORS.arrowGray}
                opacity={arrowOpacity}
              />
            </svg>
          )}

          {/* Step box */}
          <div
            style={{
              position: "absolute",
              left: centerX - stepWidth / 2,
              top: y,
              width: stepWidth,
              height: stepHeight,
              borderRadius: 22,
              backgroundColor: COLORS.stepBg,
              border: `3px solid ${COLORS.stepBorder}`,
              opacity,
              transform: `scale(${springScale})`,
              display: "flex",
              alignItems: "center",
              gap: 35,
              padding: "0 50px",
              boxShadow: "0 8px 25px rgba(0,0,0,0.15)",
            }}
          >
            <div
              style={{
                width: 72,
                height: 72,
                borderRadius: "50%",
                backgroundColor: COLORS.stepActive,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                fontSize: 30,
                fontWeight: 900,
                color: "#FFFFFF",
                fontFamily: "Helvetica, Arial, sans-serif",
              }}
            >
              {i + 1}
            </div>
            <span style={{ fontSize: 56, lineHeight: 1, flexShrink: 0 }}>{step.icon}</span>
            <span
              style={{
                fontFamily: "Helvetica, Arial, sans-serif",
                fontSize: 42,
                fontWeight: 700,
                color: COLORS.stepText,
                letterSpacing: 0.5,
                lineHeight: 1.3,
              }}
            >
              {step.text}
            </span>
          </div>
        </React.Fragment>
      );
    }
    return elements;
  };

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg, overflow: "hidden" }}>
       {/* Title */}
       <div style={{ position: "absolute", top: 100, left: 0, width: "100%", textAlign: "center", opacity: titleOpacity }}>
         <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 42, fontWeight: 800, color: "#636E72", letterSpacing: 8 }}>
           HOW IT WORKS
         </span>
       </div>

      {/* Steps */}
      {renderSteps()}
    </AbsoluteFill>
  );
};