import React from "react";
import { Box } from "@chakra-ui/react";

// CSS animations as strings
const floatAnimation = `
  @keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-2px); }
  }
`;

const pulseAnimation = `
  @keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.02); }
  }
`;

const waveAnimation = `
  @keyframes wave {
    0%, 100% { transform: scaleY(0.5); opacity: 0.8; }
    50% { transform: scaleY(1.0); opacity: 1; }
  }
`;

const circularWaveAnimation = `
  @keyframes circularWave {
    0% { transform: scaleY(0.2) scaleX(1); opacity: 0.5; }
    25% { transform: scaleY(1.6) scaleX(0.8); opacity: 0.9; }
    50% { transform: scaleY(0.8) scaleX(1.1); opacity: 1; }
    75% { transform: scaleY(1.4) scaleX(0.9); opacity: 0.8; }
    100% { transform: scaleY(0.2) scaleX(1); opacity: 0.5; }
  }
`;

const rippleAnimation = `
  @keyframes ripple {
    0% { transform: scale(0.8) rotate(0deg); opacity: 1; }
    50% { transform: scale(1.2) rotate(180deg); opacity: 0.6; }
    100% { transform: scale(0.8) rotate(360deg); opacity: 1; }
  }
`;

const glowAnimation = `
  @keyframes glow {
    0%, 100% { box-shadow: 0 0 8px rgba(59, 130, 246, 0.3); }
    50% { box-shadow: 0 0 15px rgba(59, 130, 246, 0.5); }
  }
`;

const screenGlowAnimation = `
  @keyframes screenGlow {
    0%, 100% { box-shadow: 0 0 6px rgba(16, 185, 129, 0.2); }
    50% { box-shadow: 0 0 12px rgba(16, 185, 129, 0.4); }
  }
`;

const scanlineAnimation = `
  @keyframes scanline {
    0% { transform: translateY(-100%); opacity: 0; }
    50% { opacity: 1; }
    100% { transform: translateY(400%); opacity: 0; }
  }
`;

// Inject CSS animations into the document head
const injectAnimations = () => {
  if (typeof document !== "undefined") {
    const styleId = "animated-icons-styles";
    if (!document.getElementById(styleId)) {
      const style = document.createElement("style");
      style.id = styleId;
      style.textContent =
        floatAnimation +
        pulseAnimation +
        waveAnimation +
        circularWaveAnimation +
        rippleAnimation +
        glowAnimation +
        screenGlowAnimation +
        scanlineAnimation;
      document.head.appendChild(style);
    }
  }
};

interface AnimatedIconProps {
  isActive: boolean;
  size?: number;
}

export const AnimatedScreenIcon: React.FC<AnimatedIconProps> = ({
  isActive,
  size = 40,
}) => {
  // Inject animations on component mount
  React.useEffect(() => {
    injectAnimations();
  }, []);

  return (
    <Box
      position="relative"
      width={`${size}px`}
      height={`${size * 0.8}px`}
      style={{
        animation: isActive
          ? "float 4s ease-in-out infinite"
          : "float 6s ease-in-out infinite",
      }}
    >
      {/* Monitor Base */}
      <Box
        position="absolute"
        bottom="0"
        left="50%"
        transform="translateX(-50%)"
        width="80%"
        height="6px"
        background="linear-gradient(135deg, #4a5568 0%, #2d3748 100%)"
        borderRadius="3px"
      />

      {/* Monitor Stand */}
      <Box
        position="absolute"
        bottom="6px"
        left="50%"
        transform="translateX(-50%)"
        width="3px"
        height="12px"
        background="linear-gradient(135deg, #4a5568 0%, #2d3748 100%)"
        borderRadius="2px"
      />

      {/* Monitor Screen */}
      <Box
        position="absolute"
        top="0"
        left="0"
        width="100%"
        height={`${size * 0.65}px`}
        background={
          isActive
            ? "linear-gradient(135deg, #1f2937 0%, #111827 100%)"
            : "linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%)"
        }
        borderRadius="4px"
        border="2px solid"
        borderColor={isActive ? "#374151" : "#6b7280"}
        overflow="hidden"
        style={{
          animation: isActive
            ? "screenGlow 3s ease-in-out infinite"
            : undefined,
        }}
      >
        {/* Screen Content */}
        {isActive ? (
          <>
            {/* Active screen with content */}
            <Box
              position="absolute"
              top="15%"
              left="10%"
              width="80%"
              height="3px"
              background="#10b981"
              borderRadius="1px"
              style={{
                animation: "pulse 3s ease-in-out infinite",
                animationDelay: "0s",
              }}
            />
            <Box
              position="absolute"
              top="30%"
              left="10%"
              width="60%"
              height="2px"
              background="#34d399"
              borderRadius="1px"
              style={{
                animation: "pulse 3s ease-in-out infinite",
                animationDelay: "0.4s",
              }}
            />
            <Box
              position="absolute"
              top="45%"
              left="10%"
              width="70%"
              height="2px"
              background="#6ee7b7"
              borderRadius="1px"
              style={{
                animation: "pulse 3s ease-in-out infinite",
                animationDelay: "0.8s",
              }}
            />
            <Box
              position="absolute"
              top="60%"
              left="10%"
              width="50%"
              height="2px"
              background="#a7f3d0"
              borderRadius="1px"
              style={{
                animation: "pulse 3s ease-in-out infinite",
                animationDelay: "1.2s",
              }}
            />

            {/* Scanning line effect */}
            <Box
              position="absolute"
              top="0"
              left="0"
              width="100%"
              height="2px"
              background="linear-gradient(90deg, transparent 0%, #10b981 50%, transparent 100%)"
              style={{
                animation: "scanline 4s ease-in-out infinite",
              }}
            />
          </>
        ) : (
          <>
            {/* Inactive screen */}
            <Box
              position="absolute"
              top="50%"
              left="50%"
              transform="translate(-50%, -50%)"
              width="60%"
              height="60%"
              background="radial-gradient(circle, rgba(107,114,128,0.3) 0%, transparent 70%)"
              borderRadius="50%"
            />
          </>
        )}
      </Box>

      {/* Share indicator */}
      {isActive && (
        <Box
          position="absolute"
          top="-5px"
          right="-5px"
          width="12px"
          height="12px"
          background="#10b981"
          borderRadius="50%"
          border="2px solid white"
          style={{
            animation: "pulse 2.5s ease-in-out infinite",
          }}
        />
      )}
    </Box>
  );
};

export const AnimatedMicIcon: React.FC<AnimatedIconProps> = ({
  isActive,
  size = 40,
}) => {
  // Inject animations on component mount
  React.useEffect(() => {
    injectAnimations();
  }, []);

  // Generate circular waveform bars
  const generateCircularWaveform = () => {
    const bars = [];
    const barCount = 7; // Fewer bars for traditional waveform look
    const barSpacing = size * 0.12; // Space between bars
    const totalWidth = (barCount - 1) * barSpacing;
    const startX = (size - totalWidth) / 2; // Center the waveform

    // Predefined heights for a more natural waveform pattern
    const baseHeights = [0.3, 0.7, 0.9, 1.0, 0.8, 0.6, 0.4]; // Varying heights

    for (let i = 0; i < barCount; i++) {
      const x = startX + i * barSpacing;
      const centerY = size / 2;

      // Calculate bar height with animation multiplier
      const baseHeight = baseHeights[i];
      const animationMultiplier = isActive
        ? Math.sin(Date.now() / 200 + i * 2.5) * 0.5 + 1.2 // Dynamic animation
        : Math.sin(Date.now() / 800 + i * 1.5) * 0.2 + 0.6; // Subtle ripple when inactive

      const barHeight = baseHeight * animationMultiplier * size * 0.6;
      const barWidth = size * 0.08; // Thinner bars for traditional look

      // Color gradient - center bars more vibrant
      const distanceFromCenter = Math.abs(i - (barCount - 1) / 2);
      const colorIntensity = 1 - distanceFromCenter / ((barCount - 1) / 2);
      const hue = 220 + colorIntensity * 40;
      const saturation = 70 + colorIntensity * 20;
      const lightness = 50 + colorIntensity * 30;

      const barColor = isActive
        ? `hsl(${hue}, ${saturation}%, ${lightness}%)`
        : `hsl(220, 15%, ${25 + colorIntensity * 10}%)`; // Darker, less saturated when inactive

      bars.push(
        <Box
          key={i}
          position="absolute"
          left={`${x - barWidth / 2}px`}
          top={`${centerY - barHeight / 2}px`}
          width={`${barWidth}px`}
          height={`${barHeight}px`}
          background={barColor}
          borderRadius="2px"
          style={{
            animation: isActive ? "wave 1.2s ease-in-out infinite" : undefined,
            animationDelay: `${i * 0.15}s`, // Staggered animation
            boxShadow: isActive ? `0 0 4px ${barColor}40` : "none",
            transition: "all 0.4s ease",
          }}
        />
      );
    }
    return bars;
  };

  return (
    <Box
      position="relative"
      width={`${size}px`}
      height={`${size}px`}
      style={{
        animation: isActive
          ? "float 4s ease-in-out infinite"
          : "float 6s ease-in-out infinite",
      }}
    >
      {/* Waveform Background with ripple effect */}
      <Box
        position="absolute"
        top="0"
        left="0"
        width="100%"
        height="100%"
        background={
          isActive
            ? "radial-gradient(ellipse 80% 60%, rgba(59, 130, 246, 0.15) 0%, rgba(59, 130, 246, 0.05) 50%, transparent 80%)"
            : "radial-gradient(ellipse 80% 60%, rgba(75, 85, 99, 0.12) 0%, rgba(75, 85, 99, 0.04) 50%, transparent 80%)"
        }
        borderRadius="12px"
        style={{
          animation: isActive
            ? "pulse 3s ease-in-out infinite"
            : "pulse 6s ease-in-out infinite",
        }}
      />

      {/* Additional background layer for depth */}
      {isActive && (
        <Box
          position="absolute"
          top="20%"
          left="10%"
          width="80%"
          height="60%"
          background="linear-gradient(90deg, transparent 0%, rgba(59, 130, 246, 0.08) 50%, transparent 100%)"
          borderRadius="8px"
          style={{
            animation: "glow 2.5s ease-in-out infinite",
          }}
        />
      )}

      {/* Linear Waveform Bars */}
      {generateCircularWaveform()}

      {/* Recording indicator */}
      {isActive && (
        <Box
          position="absolute"
          top="2px"
          right="2px"
          width="8px"
          height="8px"
          background="#ef4444"
          borderRadius="50%"
          border="1px solid white"
          style={{
            animation: "pulse 1.5s ease-in-out infinite",
          }}
        />
      )}

      {/* Sound wave indicators - horizontal lines */}
      {isActive && (
        <>
          <Box
            position="absolute"
            top="20%"
            left="15%"
            width="70%"
            height="1px"
            background="rgba(59, 130, 246, 0.4)"
            style={{
              animation: "pulse 2.5s ease-in-out infinite",
              animationDelay: "0s",
            }}
          />
          <Box
            position="absolute"
            bottom="20%"
            left="15%"
            width="70%"
            height="1px"
            background="rgba(59, 130, 246, 0.4)"
            style={{
              animation: "pulse 2.5s ease-in-out infinite",
              animationDelay: "0.8s",
            }}
          />
        </>
      )}
    </Box>
  );
};
