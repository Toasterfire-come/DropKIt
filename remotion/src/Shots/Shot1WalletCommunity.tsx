import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";

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
  const centerY = 780;

  // Brand positions — larger fan spread around center
  const brands = [
    { x: 280, y: 440, color: COLORS.brandColors[0], label: "BRAND A" },
    { x: 800, y: 440, color: COLORS.brandColors[1], label: "BRAND B" },
    { x: 540, y: 1080, color: COLORS.brandColors[2], label: "BRAND C" },
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
  const brandStartFrames = [60, 90, 120];

  const renderBrand = (startFrame: number, brandIdx: number) => {
    const local = frame - startFrame;
    const brand = brands[brandIdx];

    const lineProgress = interpolate(local, [0, 18], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    const lx = interpolate(lineProgress, [0, 1], [centerX, brand.x]);
    const ly = interpolate(lineProgress, [0, 1], [centerY + 50, brand.y]);

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
            <svg width="70" height="70" viewBox="0 0 70 70" fill="none">
              <rect x="15" y="15" width="40" height="40" rx="8" fill={brand.color} opacity="0.2" />
              <rect x="20" y="20" width="30" height="30" rx="6" fill="none" stroke={brand.color} strokeWidth="3" />
              <circle cx="35" cy="35" r="8" fill={brand.color} />
            </svg>
          );
        case 1:
          return (
            <svg width="70" height="70" viewBox="0 0 70 70" fill="none">
              <path d="M35 10 L50 25 L50 45 L35 60 L20 45 L20 25 Z" fill={brand.color} opacity="0.2" />
              <path d="M35 20 L45 30 L45 40 L35 50 L25 40 L25 30 Z" fill="none" stroke={brand.color} strokeWidth="3" />
            </svg>
          );
        case 2:
          return (
            <svg width="70" height="70" viewBox="0 0 70 70" fill="none">
              <circle cx="35" cy="35" r="25" fill={brand.color} opacity="0.2" />
              <circle cx="35" cy="35" r="20" fill="none" stroke={brand.color} strokeWidth="3" />
              <path d="M35 25 L42 35 L35 45 L28 35 Z" fill={brand.color} />
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
              y1={centerY + 50}
              x2={lx}
              y2={ly}
              stroke={brand.color}
              strokeWidth={4}
              strokeDasharray="10 6"
              opacity={lineOpacity}
            />
          </svg>
        )}
        {glowOpacity > 0 && (
          <div
            style={{
              position: "absolute",
              left: brand.x - 65,
              top: brand.y - 65,
              width: 130,
              height: 130,
              borderRadius: 65,
              backgroundColor: brand.color,
              opacity: glowOpacity,
              filter: "blur(30px)",
              pointerEvents: "none",
            }}
          />
        )}
        <div
          style={{
            position: "absolute",
            left: brand.x - 65,
            top: brand.y - 65,
            width: 130,
            height: 130,
            border: `4px solid ${brand.color}`,
            borderRadius: 22,
            backgroundColor: `${brand.color}12`,
            opacity: squareOpacity,
            transform: `scale(${squareSpring})`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: `0 4px 24px ${brand.color}22`,
          }}
        >
          {renderBrandLogo(brandIdx)}
        </div>
        <div
          style={{
            position: "absolute",
            left: brand.x - 80,
            top: brand.y + 80,
            width: 160,
            textAlign: "center",
            opacity: labelOpacity,
          }}
        >
          <span style={{ fontSize: 20, fontWeight: 700, color: brand.color, fontFamily: "Helvetica, Arial, sans-serif", letterSpacing: 2 }}>
            {brand.label}
          </span>
        </div>
      </React.Fragment>
    );
  };

  return (
    <AbsoluteFill style={{ backgroundColor: "#FFFFFF", overflow: "hidden" }}>
      {/* Title bar */}
      <div style={{ position: "absolute", top: 80, left: 0, width: "100%", textAlign: "center", opacity: interpolate(frame - 3, [0, 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
        <span style={{ fontSize: 22, fontWeight: 600, color: "#B2BEC3", letterSpacing: 5, fontFamily: "Helvetica, Arial, sans-serif" }}>
          FUNDING PARTNERS
        </span>
      </div>

      {/* ── DROP KIT Logo ── centered */}
      <div
        style={{
          position: "absolute",
          left: centerX,
          top: centerY,
          transform: `translate(-50%, -50%) scale(${logoSpring})`,
          opacity: logoOpacity,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 0,
        }}
      >
        {/* Drop Kit styled text logo */}
        <div style={{ display: "flex", alignItems: "baseline", gap: 0 }}>
          <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 72, fontWeight: 900, color: COLORS.brand, letterSpacing: 2, lineHeight: 1 }}>
            DROP
          </span>
          <span style={{ fontFamily: "Helvetica, Arial, sans-serif", fontSize: 72, fontWeight: 300, color: COLORS.brand, letterSpacing: 2, lineHeight: 1, marginLeft: 8 }}>
            KIT
          </span>
        </div>
        {/* Underline accent */}
        <div style={{ width: 220, height: 4, backgroundColor: "#00B894", borderRadius: 2, marginTop: 8 }} />
      </div>

      {/* ── Brand Connectors ── */}
      {renderBrand(brandStartFrames[0], 0)}
      {renderBrand(brandStartFrames[1], 1)}
      {renderBrand(brandStartFrames[2], 2)}
    </AbsoluteFill>
  );
};