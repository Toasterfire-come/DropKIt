import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";

/* ── Shot: Nintendo-style Logo Startup ── */
/* 1080×1920 portrait · 3 seconds · Logo2.png jumps, "DropKIt" slides out */

const COLORS = {
  bg: "#F8F9FA",
  brandDark: "#2D3436",
  orange: "#E8510A",
};

export const LogoIntro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // ── Phase 1: Logo bounce (frames 0–22) ──
  const logoSpring = spring({
    frame: frame,
    fps,
    config: { damping: 8, stiffness: 140, mass: 0.6 },
  });

  // Logo drops from slightly above screen, bounces to center
  const logoY = interpolate(logoSpring, [0, 1], [-120, 0]);
  const logoScale = interpolate(logoSpring, [0, 0.7, 1], [0.3, 1.15, 1], {
    extrapolateRight: "clamp",
  });

  // ── Phase 2: "DropKIt" slides out (frames 20–42) ──
  const textAppearFrame = 20;
  const textLocal = frame - textAppearFrame;

  const textSlide = spring({
    frame: Math.max(0, textLocal),
    fps,
    config: { damping: 14, stiffness: 180, mass: 0.8 },
  });

  // Each letter cascades slightly
  const letterDelay = (idx: number) =>
    interpolate(
      Math.max(0, textLocal - idx * 2),
      [0, 10],
      [0, 1],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );

  // ── Phase 3: Hold with subtle glow pulse (frames 42–90) ──
  const glowOpacity = interpolate(
    Math.sin(frame * 0.08) * 0.5 + 0.5,
    [0, 1],
    [0.15, 0.4]
  );
  const showGlow = frame >= 40;

  const letters = [
    { char: "D", color: COLORS.brandDark },
    { char: "r", color: COLORS.brandDark },
    { char: "o", color: COLORS.brandDark },
    { char: "p", color: COLORS.brandDark },
    { char: "K", color: COLORS.orange },
    { char: "i", color: COLORS.orange },
    { char: "t", color: COLORS.orange },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg, overflow: "hidden" }}>
      {/* ── Centered content ── */}
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "50%",
          transform: `translate(-50%, -50%)`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 30,
        }}
      >
        {/* Logo2.png — bounces in */}
        <div
          style={{
            transform: `translateY(${logoY}px) scale(${logoScale})`,
          }}
        >
          <Img
            src={staticFile("Logo2.png")}
            style={{
              width: 480,
              height: "auto",
              objectFit: "contain",
              display: "block",
            }}
          />
        </div>

        {/* ── "DropKIt" text — slides out from under logo ── */}
        <div
          style={{
            overflow: "hidden",
            height: 90,
            transform: `translateY(${interpolate(textSlide, [0, 1], [-10, 0])}px)`,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              opacity: textSlide,
            }}
          >
            {letters.map((l, i) => (
              <span
                key={i}
                style={{
                  fontFamily: "'Space Grotesk', 'Helvetica', 'Arial', sans-serif",
                  fontSize: 78,
                  fontWeight: i === 4 ? 900 : 700,
                  color: l.color,
                  letterSpacing: 2,
                  lineHeight: 1,
                  display: "inline-block",
                  transform: `translateY(${interpolate(
                    letterDelay(i),
                    [0, 1],
                    [40, 0]
                  )}px)`,
                  opacity: letterDelay(i),
                }}
              >
                {l.char}
              </span>
            ))}
          </div>
        </div>

        {/* Thin underline accent */}
        <div
          style={{
            width: 240,
            height: 4,
            backgroundColor: COLORS.orange,
            borderRadius: 2,
            opacity: textSlide,
            marginTop: 4,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};