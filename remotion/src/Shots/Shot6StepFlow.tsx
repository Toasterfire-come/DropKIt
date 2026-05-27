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
  barBg: "#2D2D44",
  fillStart: "#00B894",
  fillEnd: "#55EFC4",
  label: "#FFFFFF",
  labelDim: "#636E72",
  redPulse: "#D63031",
};

const STEPS = [
  { text: "You pledge", icon: "🤝" },
  { text: "Total tracked publicly", icon: "📊" },
  { text: "Hits $2,000", icon: "🎯" },
  { text: "I collect", icon: "💰" },
  { text: "Announced on socials", icon: "📣" },
  { text: "I build out production", icon: "🔧" },
];

export const Shot6StepFlow: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const centerX = 540;
  const startY = 220;
  const stepHeight = 110;
  const stepGap = 20;
  const stepWidth = 380;

  // Steps build one by one
  const stepsPerRow = 2;
  const rows = Math.ceil(STEPS.length / stepsPerRow);

  // ── Title ──
  const titleOpacity = interpolate(frame, [3, 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  // ── Build steps ──
  const renderSteps = () => {
    const elements: React.ReactNode[] = [];

    for (let i = 0; i < STEPS.length; i++) {
      const step = STEPS[i];
      const row = Math.floor(i / stepsPerRow);
      const col = i % stepsPerRow;
      const rowTotal = row === 0 ? 2 : row === 1 && STEPS.length % 2 === 1 && col === 1 ? 1 : 2;
      const rowWidth = rowTotal * (stepWidth + stepGap) - stepGap;
      const rowX = centerX - rowWidth / 2;

      const x = rowX + col * (stepWidth + stepGap);
      const y = startY + row * (stepHeight + 60) + (row > 0 ? 40 : 0);

      const appearFrame = 15 + i * 20;
      const local = frame - appearFrame;

      const springScale = spring({ frame: local, fps, config: { damping: 12, stiffness: 150 } });
      const opacity = interpolate(local, [0, 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

      // Arrow between steps horizontally
      const showArrowHoriz = col === 0 && rowTotal > 1 && local > 5;
      const arrowOpacityH = showArrowHoriz ? interpolate(local - 5, [0, 8], [0, 0.6], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;

      // Arrow between rows vertically
      const showArrowVert = row > 0 && local > 5;
      const arrowOpacityV = showArrowVert ? interpolate(local - 5, [0, 8], [0, 0.6], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;

      // Step number
      const stepNum = local > 0;

      elements.push(
        <React.Fragment key={i}>
          {/* Vertical arrow from previous row */}
          {row > 0 && col === 0 && arrowOpacityV > 0 && (
            <svg style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", pointerEvents: "none" }}>
              <line
                x1={x + stepWidth / 2}
                y1={y - 45}
                x2={x + stepWidth / 2}
                y2={y}
                stroke={COLORS.arrowGray}
                strokeWidth={2.5}
                strokeDasharray="6 4"
                opacity={arrowOpacityV}
              />
              <polygon
                points={`${x + stepWidth / 2 - 6},${y - 4} ${x + stepWidth / 2 + 6},${y - 4} ${x + stepWidth / 2},${y + 4}`}
                fill={COLORS.arrowGray}
                opacity={arrowOpacityV}
              />
            </svg>
          )}

          {/* Horizontal arrow */}
          {showArrowHoriz && arrowOpacityH > 0 && col === 0 && (
            <svg style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", pointerEvents: "none" }}>
              <line
                x1={x + stepWidth + 4}
                y1={y + stepHeight / 2}
                x2={x + stepWidth + stepGap - 4}
                y2={y + stepHeight / 2}
                stroke={COLORS.arrowGray}
                strokeWidth={2.5}
                strokeDasharray="6 4"
                opacity={arrowOpacityH}
              />
              <polygon
                points={`${x + stepWidth + stepGap - 6},${y + stepHeight / 2 - 6} ${x + stepWidth + stepGap - 6},${y + stepHeight / 2 + 6} ${x + stepWidth + stepGap + 2},${y + stepHeight / 2}`}
                fill={COLORS.arrowGray}
                opacity={arrowOpacityH}
              />
            </svg>
          )}

          {/* Step box */}
          {stepNum && (
            <div
              style={{
                position: "absolute",
                left: x,
                top: y,
                width: stepWidth,
                height: stepHeight,
                borderRadius: 16,
                backgroundColor: COLORS.stepBg,
                border: `2px solid ${COLORS.stepBorder}`,
                opacity,
                transform: `scale(${springScale})`,
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "0 20px",
                boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
              }}
            >
              {/* Step number badge */}
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: "50%",
                  backgroundColor: COLORS.stepActive,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                  fontSize: 14,
                  fontWeight: 800,
                  color: "#FFFFFF",
                  fontFamily: "Helvetica, Arial, sans-serif",
                }}
              >
                {i + 1}
              </div>
              {/* Icon */}
              <span style={{ fontSize: 26, lineHeight: 1, flexShrink: 0 }}>{step.icon}</span>
              {/* Text */}
              <span
                style={{
                  fontFamily: "Helvetica, Arial, sans-serif",
                  fontSize: 18,
                  fontWeight: 600,
                  color: COLORS.stepText,
                  letterSpacing: 0.3,
                  lineHeight: 1.2,
                }}
              >
                {step.text}
              </span>
            </div>
          )}
        </React.Fragment>
      );
    }
    return elements;
  };

  // ── Progress bar section (appears after all steps) ──
  const fillStartFrame = 15 + STEPS.length * 20 + 15;
  const barAppearFrame = fillStartFrame - 10;

  const barSpring = spring({ frame: frame - barAppearFrame, fps, config: { damping: 14, stiffness: 90 } });
  const barOpacity = interpolate(frame - barAppearFrame, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  // Fill → stutter → retract → red pulse
  const fill1 = interpolate(frame, [fillStartFrame, fillStartFrame + 25], [0, 0.7], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  let fillProgress: number;
  if (frame < fillStartFrame) {
    fillProgress = 0;
  } else if (frame < fillStartFrame + 25) {
    fillProgress = fill1;
  } else if (frame < fillStartFrame + 60) {
    const stutterFrame = frame - (fillStartFrame + 25);
    if (stutterFrame < 8) fillProgress = interpolate(stutterFrame, [0, 8], [0.7, 0.5], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    else if (stutterFrame < 15) fillProgress = interpolate(stutterFrame, [8, 15], [0.5, 0.6], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    else if (stutterFrame < 25) fillProgress = interpolate(stutterFrame, [15, 25], [0.6, 0.2], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    else fillProgress = interpolate(stutterFrame, [25, 35], [0.2, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  } else {
    fillProgress = 0;
  }

  const pulseLocal = frame - (fillStartFrame + 65);
  const pulseOpacity = interpolate(pulseLocal, [0, 10, 20, 30, 35], [0, 0.4, 0, 0.3, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const barW = 860;
  const barH = 44;
  const barX = (1080 - barW) / 2;
  const barY = startY + rows * (stepHeight + 60) + 80;

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg, overflow: "hidden" }}>
      {/* Title */}
      <div style={{ position: "absolute", top: 80, left: 0, width: "100%", textAlign: "center", opacity: titleOpacity }}>
        <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 24, fontWeight: 700, color: "#B2BEC3", letterSpacing: 5 }}>
          HOW IT WORKS
        </span>
      </div>

      {/* Steps */}
      {renderSteps()}

      {/* Progress Bar Section */}
      <div style={{ position: "absolute", top: barY - 30, left: 0, width: "100%", opacity: barOpacity }}>
        <div style={{ textAlign: "center", marginBottom: 20 }}>
          <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 20, fontWeight: 600, color: "#B2BEC3", letterSpacing: 3 }}>
            CURRENT PROGRESS
          </span>
        </div>

        {/* Label */}
        <div style={{ position: "absolute", top: 30, left: barX, width: barW, display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 16, fontWeight: 500, color: COLORS.labelDim, letterSpacing: 1 }}>Total</span>
          <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 44, fontWeight: 800, color: "#1E1E2E", letterSpacing: 1 }}>
            $0 / $2,000
          </span>
        </div>

        {/* Bar */}
        <div style={{ position: "absolute", left: barX, top: 90, width: barW, height: barH, borderRadius: barH / 2, backgroundColor: COLORS.barBg, overflow: "hidden", transform: `scaleX(${barSpring})`, transformOrigin: "left center" }}>
          <div style={{ width: `${fillProgress * 100}%`, height: "100%", borderRadius: barH / 2, background: `linear-gradient(90deg, ${COLORS.fillStart}, ${COLORS.fillEnd})` }} />
          {pulseOpacity > 0 && (
            <div style={{ position: "absolute", left: 0, top: 0, width: "100%", height: "100%", borderRadius: barH / 2, background: `radial-gradient(ellipse at 50% 50%, ${COLORS.redPulse}88 0%, transparent 70%)`, opacity: pulseOpacity }} />
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};