import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";

/* ── Shot 1: DROP KIT Logo → Three Brand Lines ── */
/* Shorts format: 1080×1920 — No community, no wallet — DROP KIT branded */

const COLORS = {
  brand: "#2D3436",
  brandColors: ["#0984E3", "#6C5CE7", "#FD79A8"],
};

export const Shot1WalletCommunity: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const centerX = 540;

  // Brand positions — larger fan spread around center
  const brands = [
    { x: 200, y: 320, color: COLORS.brandColors[0], label: "BRAND A" },
    { x: 880, y: 320, color: COLORS.brandColors[1], label: "BRAND B" },
    { x: 540, y: 1200, color: COLORS.brandColors[2], label: "BRAND C" },
  ];

  // ── DROP KIT Logo entrance ──
  const logoSpring = spring({
    frame: frame - 8,
    fps,
    config: { damping: 12, stiffness: 100 },
  });
  const logoOpacity = interpolate(frame - 8, [0, 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // ── Brand connector lines (staggered) ──
  const brandStartFrames = [30, 60, 90];

  const renderBrand = (startFrame: number, brandIdx: number) => {
    const local = frame - startFrame;
    const brand = brands[brandIdx];

    const lineProgress = interpolate(local, [0, 18], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    const lx = interpolate(lineProgress, [0, 1], [centerX, brand.x]);
    const ly = interpolate(lineProgress, [0, 1], [780, brand.y]);

    const lineOpacity = interpolate(local, [0, 5, 22, 32], [0, 1, 1, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

    const glowOpacity = interpolate(local, [18, 24, 30], [0, 0.5, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

    const squareSpring = spring({
      frame: local - 18,
      fps,
      config: { damping: 10, stiffness: 120 },
    });
    const squareOpacity = interpolate(local - 18, [0, 8], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

    const labelOpacity = interpolate(local - 25, [0, 10], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

    if (local < 0) return null;

    // Brand logo designs
    const renderBrandLogo = (idx: number) => {
      switch(idx) {
        case 0:
          return (
            <svg width="100" height="100" viewBox="0 0 100 100" fill="none">
              <rect x="15" y="15" width="70" height="70" rx="12" fill={brand.color} opacity="0.2" />
              <rect x="25" y="25" width="50" height="50" rx="10" fill="none" stroke={brand.color} strokeWidth="4" />
              <circle cx="50" cy="50" r="14" fill={brand.color} />
            </svg>
          );
        case 1:
          return (
            <svg width="100" height="100" viewBox="0 0 100 100" fill="none">
              <path d="M50 8 L70 28 L70 52 L50 72 L30 52 L30 28 Z" fill={brand.color} opacity="0.2" />
              <path d="M50 18 L62 32 L62 48 L50 62 L38 48 L38 32 Z" fill="none" stroke={brand.color} strokeWidth="4" />
            </svg>
          );
        case 2:
          return (
            <svg width="100" height="100" viewBox="0 0 100 100" fill="none">
              <circle cx="50" cy="50" r="36" fill={brand.color} opacity="0.2" />
              <circle cx="50" cy="50" r="30" fill="none" stroke={brand.color} strokeWidth="4" />
              <path d="M50 30 L60 50 L50 70 L40 50 Z" fill={brand.color} />
            </svg>
          );
        default:
          return null;
      }
    };

    return (
      <React.Fragment key={brandIdx}>
        {lineOpacity > 0 && (
          <svg
            style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", pointerEvents: "none" }}
          >
            <line
              x1={centerX}
              y1={780}
              x2={lx}
              y2={ly}
              stroke={brand.color}
              strokeWidth={5}
              strokeDasharray="12 8"
              opacity={lineOpacity}
            />
          </svg>
        )}
        {glowOpacity > 0 && (
            <div
              style={{
                position: "absolute",
                left: brand.x - 100,
                top: brand.y - 100,
                width: 200,
                height: 200,
                borderRadius: 100,
                backgroundColor: brand.color,
                opacity: glowOpacity,
                filter: "blur(45px)",
                pointerEvents: "none",
              }}
            />
          )}
          <div
            style={{
              position: "absolute",
              left: brand.x - 100,
              top: brand.y - 100,
              width: 200,
              height: 200,
              border: `7px solid ${brand.color}`,
              borderRadius: 35,
              backgroundColor: `${brand.color}12`,
              opacity: squareOpacity,
              transform: `scale(${squareSpring})`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: `0 10px 40px ${brand.color}22`,
            }}
          >
            {renderBrandLogo(brandIdx)}
          </div>
          <div
            style={{
              position: "absolute",
              left: brand.x - 110,
              top: brand.y + 110,
              width: 220,
              textAlign: "center",
              opacity: labelOpacity,
            }}
          >
            <span style={{ fontSize: 36, fontWeight: 900, color: brand.color, fontFamily: "Helvetica, Arial, sans-serif", letterSpacing: 3 }}>
              {brand.label}
            </span>
          </div>
      </React.Fragment>
    );
  };

  return (
    <AbsoluteFill style={{ backgroundColor: "#FFFFFF", overflow: "hidden" }}>
      {/* Title bar */}
      <div style={{ position: "absolute", top: 100, left: 0, width: "100%", textAlign: "center", opacity: interpolate(frame - 3, [0, 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
        <span style={{ fontSize: 40, fontWeight: 800, color: "#636E72", letterSpacing: 10, fontFamily: "Helvetica, Arial, sans-serif" }}>
          FUNDING PARTNERS
        </span>
      </div>

      {/* ── DROP KIT Logo ── centered */}
      <div
        style={{
          position: "absolute",
          left: centerX,
          top: 640,
          transform: `translate(-50%, -50%) scale(${logoSpring})`,
          opacity: logoOpacity,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 24,
        }}
      >
         {/* Logo2.png image */}
         <Img
           src={staticFile("Logo2.png")}
           style={{ width: 340, height: "auto", objectFit: "contain" }}
         />
         {/* DropKIt name underneath */}
         <div style={{ display: "flex", alignItems: "baseline", gap: 0 }}>
           <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 88, fontWeight: 900, color: COLORS.brand, letterSpacing: 5, lineHeight: 1 }}>
             DROP
           </span>
           <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 88, fontWeight: 300, color: COLORS.brand, letterSpacing: 5, lineHeight: 1, marginLeft: 16 }}>
             KIT
           </span>
         </div>
         {/* Underline accent */}
         <div style={{ width: 300, height: 8, backgroundColor: "#00B894", borderRadius: 4, marginTop: 4 }} />
      </div>

      {/* ── Brand Connectors ── */}
      {renderBrand(brandStartFrames[0], 0)}
      {renderBrand(brandStartFrames[1], 1)}
      {renderBrand(brandStartFrames[2], 2)}
    </AbsoluteFill>
  );
};