import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Sequence,
  Easing,
  Audio,
  staticFile,
} from "remotion";
import React from "react";

// =============================================================================
// BEAT SYNC CONFIGURATION
// =============================================================================
// Using 120 BPM - each beat = 15 frames at 30fps
// 1 bar (4 beats) = 60 frames = 2 seconds
const BPM = 120;
const FRAMES_PER_BEAT = 15; // 30fps / (120bpm / 60)
const FRAMES_PER_BAR = FRAMES_PER_BEAT * 4; // 60 frames

// Helper to get beat pulse (0-1 value that peaks on each beat)
const useBeatPulse = (frame: number, intensity: number = 1) => {
  const beatPosition = (frame % FRAMES_PER_BEAT) / FRAMES_PER_BEAT;
  const pulse = Math.exp(-beatPosition * 6) * intensity;
  return pulse;
};

// Helper to check if we're on a beat
const isOnBeat = (frame: number, tolerance: number = 2) => {
  return (frame % FRAMES_PER_BEAT) < tolerance;
};

// =============================================================================
// STYLES
// =============================================================================
const styles = {
  background: "#09090b",
  white: "#ffffff",
  zinc100: "#f4f4f5",
  zinc400: "#a1a1aa",
  zinc500: "#71717a",
  zinc600: "#52525b",
  zinc800: "#27272a",
  zinc900: "#18181b",
  emerald500: "#10b981",
  accent: "#6366f1",
};

// =============================================================================
// BEAT-REACTIVE PARTICLES BACKGROUND
// =============================================================================
const ParticlesBackground: React.FC = () => {
  const frame = useCurrentFrame();
  const beatPulse = useBeatPulse(frame, 0.5);
  
  const particles = Array.from({ length: 60 }, (_, i) => ({
    id: i,
    x: (i * 47) % 100,
    y: (i * 31) % 100,
    size: 2 + (i % 3),
    speed: 0.3 + (i % 5) * 0.15,
  }));

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      {particles.map((p) => {
        const yOffset = (frame * p.speed) % 120;
        const baseOpacity = interpolate(
          ((p.y + yOffset) % 120),
          [0, 20, 100, 120],
          [0, 0.6, 0.6, 0]
        );
        // Particles pulse brighter on beat
        const opacity = baseOpacity * (0.3 + beatPulse * 0.4);
        const scale = 1 + beatPulse * 0.3;
        
        return (
          <div
            key={p.id}
            style={{
              position: "absolute",
              left: `${p.x}%`,
              top: `${(p.y + yOffset) % 120 - 10}%`,
              width: p.size * scale,
              height: p.size * scale,
              borderRadius: "50%",
              backgroundColor: styles.white,
              opacity,
              transition: "opacity 0.05s",
            }}
          />
        );
      })}
      {/* Beat-reactive grid overlay */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `
            linear-gradient(rgba(255,255,255,${0.03 + beatPulse * 0.02}) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,${0.03 + beatPulse * 0.02}) 1px, transparent 1px)
          `,
          backgroundSize: "60px 60px",
          opacity: 0.5 + beatPulse * 0.3,
        }}
      />
    </AbsoluteFill>
  );
};

// =============================================================================
// BEAT-REACTIVE GRADIENT ORBS
// =============================================================================
const GradientOrbs: React.FC = () => {
  const frame = useCurrentFrame();
  const beatPulse = useBeatPulse(frame, 1);
  const slowPulse = Math.sin(frame * 0.02) * 0.2 + 1;
  const pulse = slowPulse + beatPulse * 0.15;

  return (
    <>
      <div
        style={{
          position: "absolute",
          top: "20%",
          left: "20%",
          width: 500 * pulse,
          height: 500 * pulse,
          background: `rgba(255,255,255,${0.05 + beatPulse * 0.03})`,
          borderRadius: "50%",
          filter: "blur(100px)",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: "20%",
          right: "20%",
          width: 400 * pulse,
          height: 400 * pulse,
          background: `rgba(99,102,241,${0.08 + beatPulse * 0.05})`,
          borderRadius: "50%",
          filter: "blur(80px)",
        }}
      />
    </>
  );
};

// =============================================================================
// BEAT VISUALIZER (audio waveform style)
// =============================================================================
const BeatVisualizer: React.FC<{ position?: "bottom" | "top" }> = ({ position = "bottom" }) => {
  const frame = useCurrentFrame();
  const beatPulse = useBeatPulse(frame, 1);
  const bars = 40;

  return (
    <div
      style={{
        position: "absolute",
        [position]: 0,
        left: 0,
        right: 0,
        height: 60,
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "center",
        gap: 4,
        padding: "0 100px",
        opacity: 0.3,
      }}
    >
      {Array.from({ length: bars }).map((_, i) => {
        const offset = Math.sin(i * 0.5 + frame * 0.1) * 0.5 + 0.5;
        const height = 10 + offset * 30 + beatPulse * 20;
        return (
          <div
            key={i}
            style={{
              width: 3,
              height,
              backgroundColor: styles.white,
              borderRadius: 2,
              opacity: 0.5 + beatPulse * 0.5,
            }}
          />
        );
      })}
    </div>
  );
};

// =============================================================================
// LOGO COMPONENT
// =============================================================================
const Logo: React.FC<{ scale?: number; pulse?: number }> = ({ scale = 1, pulse = 0 }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 16 * scale }}>
    <div
      style={{
        width: 48 * scale * (1 + pulse * 0.1),
        height: 48 * scale * (1 + pulse * 0.1),
        borderRadius: 12 * scale,
        background: "linear-gradient(135deg, #f4f4f5, #a1a1aa)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        boxShadow: `0 0 ${20 + pulse * 30}px rgba(255,255,255,${0.2 + pulse * 0.3})`,
      }}
    >
      <svg
        width={28 * scale}
        height={28 * scale}
        viewBox="0 0 24 24"
        fill="none"
        stroke="#09090b"
        strokeWidth="2"
      >
        <path d="M3 21h18M5 21V7l8-4 8 4v14M9 21v-6h6v6" />
      </svg>
    </div>
    <span
      style={{
        fontSize: 28 * scale,
        fontWeight: 600,
        color: styles.white,
        fontFamily: "system-ui, sans-serif",
        letterSpacing: "-0.02em",
      }}
    >
      LandRegistry.io
    </span>
  </div>
);

// =============================================================================
// SCENE 1: LOGO REVEAL (Bars 1-2.5 = 0-150 frames)
// Beat drops: Logo appears on beat 1, tagline on beat 5, badge on beat 9
// =============================================================================
const Scene1LogoReveal: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const beatPulse = useBeatPulse(frame, 1);

  // Logo appears with impact on first beat (frame 0)
  const logoScale = spring({
    frame,
    fps,
    config: { damping: 10, stiffness: 150 },
  });

  const logoOpacity = interpolate(frame, [0, 10], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Tagline on beat 4 (frame 45)
  const taglineOpacity = interpolate(frame, [45, 60], [0, 1], {
    extrapolateRight: "clamp",
  });
  const taglineY = interpolate(frame, [45, 60], [40, 0], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.back(1.5)),
  });

  // Badge on beat 7 (frame 90)
  const badgeScale = spring({
    frame: frame - 90,
    fps,
    config: { damping: 12, stiffness: 200 },
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        gap: 40,
      }}
    >
      <div
        style={{
          transform: `scale(${logoScale * 1.5 * (1 + beatPulse * 0.05)})`,
          opacity: logoOpacity,
        }}
      >
        <Logo scale={1.5} pulse={beatPulse} />
      </div>

      <div
        style={{
          opacity: taglineOpacity,
          transform: `translateY(${taglineY}px) scale(${1 + beatPulse * 0.02})`,
          textAlign: "center",
        }}
      >
        <p
          style={{
            fontSize: 36,
            color: styles.zinc400,
            fontFamily: "system-ui, sans-serif",
            fontWeight: 300,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
          }}
        >
          Corporate Land Registry
        </p>
      </div>

      <div
        style={{
          transform: `scale(${Math.max(0, badgeScale)})`,
          opacity: badgeScale > 0 ? 1 : 0,
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "12px 24px",
          border: `1px solid rgba(255,255,255,${0.1 + beatPulse * 0.1})`,
          borderRadius: 50,
          background: `rgba(255,255,255,${0.05 + beatPulse * 0.05})`,
        }}
      >
        <div
          style={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            backgroundColor: styles.emerald500,
            boxShadow: `0 0 ${10 + beatPulse * 10}px ${styles.emerald500}`,
          }}
        />
        <span
          style={{
            fontSize: 14,
            color: styles.zinc400,
            fontFamily: "system-ui, sans-serif",
            textTransform: "uppercase",
            letterSpacing: "0.25em",
          }}
        >
          Official UK Data Source
        </span>
      </div>
      
      <BeatVisualizer position="bottom" />
    </AbsoluteFill>
  );
};

// =============================================================================
// SCENE 2: PROBLEM (Bars 2.5-5 = 150-300 frames)
// Pain points appear on beats
// =============================================================================
const Scene2Problem: React.FC = () => {
  const frame = useCurrentFrame();
  const beatPulse = useBeatPulse(frame, 1);

  const titleOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });
  const titleScale = interpolate(frame, [0, 15], [0.8, 1], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.back(1.5)),
  });

  const problems = [
    { text: "Hours of manual research", beat: 2 },
    { text: "Scattered data sources", beat: 4 },
    { text: "Incomplete information", beat: 6 },
  ];

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        gap: 50,
        padding: 100,
      }}
    >
      <h2
        style={{
          fontSize: 72,
          color: styles.white,
          fontFamily: "system-ui, sans-serif",
          fontWeight: 600,
          textAlign: "center",
          opacity: titleOpacity,
          transform: `scale(${titleScale * (1 + beatPulse * 0.02)})`,
          letterSpacing: "-0.02em",
        }}
      >
        Who owns that property?
      </h2>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 28,
          alignItems: "center",
        }}
      >
        {problems.map((item, i) => {
          const startFrame = item.beat * FRAMES_PER_BEAT;
          const itemOpacity = interpolate(frame, [startFrame, startFrame + 10], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const itemX = interpolate(frame, [startFrame, startFrame + 10], [-50, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.out(Easing.back(1.2)),
          });

          return (
            <div
              key={i}
              style={{
                opacity: itemOpacity,
                transform: `translateX(${itemX}px) scale(${1 + (frame > startFrame && frame < startFrame + 5 ? 0.05 : 0)})`,
                display: "flex",
                alignItems: "center",
                gap: 20,
              }}
            >
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 10,
                  backgroundColor: "rgba(239,68,68,0.2)",
                  border: "1px solid rgba(239,68,68,0.3)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <span style={{ fontSize: 22, color: "#ef4444" }}>✕</span>
              </div>
              <span
                style={{
                  fontSize: 32,
                  color: styles.zinc400,
                  fontFamily: "system-ui, sans-serif",
                }}
              >
                {item.text}
              </span>
            </div>
          );
        })}
      </div>
      
      <BeatVisualizer position="bottom" />
    </AbsoluteFill>
  );
};

// =============================================================================
// SCENE 3: SOLUTION (Bars 5-7.5 = 300-450 frames)
// Search interface with typing synced to beats
// =============================================================================
const Scene3Solution: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const beatPulse = useBeatPulse(frame, 1);

  const titleOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });
  const titleY = interpolate(frame, [0, 15], [30, 0], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  const cardScale = spring({
    frame: frame - 30,
    fps,
    config: { damping: 12, stiffness: 100 },
  });

  // Typing synced to beats - each character on a beat subdivision
  const typingText = "TESCO PLC";
  const charsPerBeat = 2;
  const typingStartFrame = 60;
  const typedLength = Math.min(
    Math.floor((frame - typingStartFrame) / (FRAMES_PER_BEAT / charsPerBeat)),
    typingText.length
  );
  const displayText = frame > typingStartFrame ? typingText.slice(0, Math.max(0, typedLength)) : "";

  const cursorOpacity = frame > typingStartFrame ? (Math.floor(frame / 8) % 2 === 0 ? 1 : 0) : 0;

  // Results appear on beat after typing complete
  const resultsOpacity = interpolate(frame, [120, 135], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        gap: 50,
      }}
    >
      <h2
        style={{
          fontSize: 64,
          color: styles.white,
          fontFamily: "system-ui, sans-serif",
          fontWeight: 600,
          textAlign: "center",
          opacity: titleOpacity,
          transform: `translateY(${titleY}px) scale(${1 + beatPulse * 0.02})`,
          letterSpacing: "-0.02em",
        }}
      >
        One search. Complete answers.
      </h2>

      <div
        style={{
          transform: `scale(${Math.min(cardScale, 1)})`,
          opacity: cardScale > 0 ? 1 : 0,
          background: "rgba(24,24,27,0.9)",
          backdropFilter: "blur(20px)",
          border: `1px solid rgba(255,255,255,${0.1 + beatPulse * 0.05})`,
          borderRadius: 24,
          padding: 40,
          width: 750,
          boxShadow: `0 0 ${40 + beatPulse * 20}px rgba(0,0,0,0.5)`,
        }}
      >
        <div
          style={{
            background: "rgba(0,0,0,0.4)",
            borderRadius: 16,
            padding: 24,
            border: "1px solid rgba(255,255,255,0.05)",
            marginBottom: 24,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <svg
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke={styles.zinc500}
              strokeWidth="2"
            >
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.35-4.35" />
            </svg>
            <span
              style={{
                fontSize: 24,
                color: displayText ? styles.white : styles.zinc500,
                fontFamily: "monospace",
                letterSpacing: "0.05em",
              }}
            >
              {displayText || "Search company name..."}
              <span style={{ opacity: cursorOpacity, color: styles.accent }}>
                █
              </span>
            </span>
          </div>
        </div>

        {/* Search results preview */}
        <div style={{ opacity: resultsOpacity }}>
          <div
            style={{
              fontSize: 12,
              color: styles.zinc500,
              textTransform: "uppercase",
              letterSpacing: "0.2em",
              marginBottom: 16,
            }}
          >
            Found 847 properties
          </div>
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              style={{
                background: "rgba(255,255,255,0.03)",
                borderRadius: 8,
                padding: 12,
                marginBottom: 8,
                border: "1px solid rgba(255,255,255,0.05)",
              }}
            >
              <div
                style={{
                  width: `${70 - i * 15}%`,
                  height: 12,
                  background: "rgba(255,255,255,0.1)",
                  borderRadius: 4,
                }}
              />
            </div>
          ))}
        </div>
      </div>
      
      <BeatVisualizer position="bottom" />
    </AbsoluteFill>
  );
};

// =============================================================================
// SCENE 4: FEATURES (Bars 7.5-10 = 450-600 frames)
// Cards drop in on beats
// =============================================================================
const Scene4Features: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const beatPulse = useBeatPulse(frame, 1);

  const features = [
    { icon: "🏢", title: "Company Search", desc: "Find all corporate properties", beat: 1 },
    { icon: "📍", title: "Address Lookup", desc: "Reverse search by location", beat: 3 },
    { icon: "📊", title: "Export Data", desc: "CSV & JSON formats", beat: 5 },
  ];

  const titleOpacity = interpolate(frame, [0, 15], [0, 1]);
  const titleScale = interpolate(frame, [0, 15], [0.9, 1], {
    easing: Easing.out(Easing.back(1.5)),
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        gap: 60,
      }}
    >
      <h2
        style={{
          fontSize: 56,
          color: styles.white,
          fontFamily: "system-ui, sans-serif",
          fontWeight: 600,
          letterSpacing: "-0.02em",
          opacity: titleOpacity,
          transform: `scale(${titleScale * (1 + beatPulse * 0.02)})`,
        }}
      >
        Powerful Search Tools
      </h2>

      <div style={{ display: "flex", gap: 40 }}>
        {features.map((feature, i) => {
          const startFrame = feature.beat * FRAMES_PER_BEAT;
          const cardSpring = spring({
            frame: frame - startFrame,
            fps,
            config: { damping: 10, stiffness: 150 },
          });
          
          // Extra pop on the beat it appears
          const isAppearingBeat = frame >= startFrame && frame < startFrame + 5;
          const popScale = isAppearingBeat ? 1.1 : 1;

          return (
            <div
              key={i}
              style={{
                transform: `scale(${Math.min(cardSpring, 1) * popScale}) translateY(${(1 - Math.min(cardSpring, 1)) * 80}px)`,
                opacity: cardSpring,
                background: "rgba(24,24,27,0.7)",
                backdropFilter: "blur(20px)",
                border: `1px solid rgba(255,255,255,${0.08 + (isAppearingBeat ? 0.1 : 0)})`,
                borderRadius: 24,
                padding: 40,
                width: 280,
                textAlign: "center",
                boxShadow: isAppearingBeat ? "0 0 40px rgba(99,102,241,0.3)" : "none",
              }}
            >
              <div
                style={{
                  fontSize: 56,
                  marginBottom: 20,
                  transform: `scale(${1 + beatPulse * 0.1})`,
                }}
              >
                {feature.icon}
              </div>
              <h3
                style={{
                  fontSize: 24,
                  color: styles.white,
                  fontFamily: "system-ui, sans-serif",
                  fontWeight: 500,
                  marginBottom: 12,
                }}
              >
                {feature.title}
              </h3>
              <p
                style={{
                  fontSize: 16,
                  color: styles.zinc500,
                  fontFamily: "system-ui, sans-serif",
                }}
              >
                {feature.desc}
              </p>
            </div>
          );
        })}
      </div>
      
      <BeatVisualizer position="bottom" />
    </AbsoluteFill>
  );
};

// =============================================================================
// SCENE 5: STATS (Bars 10-12.5 = 600-750 frames)
// Numbers count up with beat emphasis
// =============================================================================
const Scene5Stats: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const beatPulse = useBeatPulse(frame, 1);

  const stats = [
    { value: "3.8M+", label: "Property Records", beat: 1 },
    { value: "Daily", label: "Data Updates", beat: 3 },
    { value: "99%", label: "Accuracy Rate", beat: 5 },
  ];

  const titleOpacity = interpolate(frame, [0, 15], [0, 1]);
  const titleY = interpolate(frame, [0, 15], [30, 0], {
    easing: Easing.out(Easing.cubic),
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        gap: 80,
      }}
    >
      <h2
        style={{
          fontSize: 56,
          color: styles.white,
          fontFamily: "system-ui, sans-serif",
          fontWeight: 600,
          letterSpacing: "-0.02em",
          opacity: titleOpacity,
          transform: `translateY(${titleY}px) scale(${1 + beatPulse * 0.02})`,
        }}
      >
        Trusted Official Data
      </h2>

      <div style={{ display: "flex", gap: 120 }}>
        {stats.map((stat, i) => {
          const startFrame = stat.beat * FRAMES_PER_BEAT;
          const statSpring = spring({
            frame: frame - startFrame,
            fps,
            config: { damping: 10, stiffness: 150 },
          });
          
          const isAppearingBeat = frame >= startFrame && frame < startFrame + 5;

          return (
            <div
              key={i}
              style={{
                textAlign: "center",
                transform: `scale(${statSpring * (isAppearingBeat ? 1.15 : 1)})`,
                opacity: statSpring,
              }}
            >
              <div
                style={{
                  fontSize: 90,
                  color: styles.white,
                  fontFamily: "system-ui, sans-serif",
                  fontWeight: 700,
                  letterSpacing: "-0.03em",
                  marginBottom: 12,
                  textShadow: isAppearingBeat ? `0 0 40px rgba(255,255,255,0.5)` : "none",
                }}
              >
                {stat.value}
              </div>
              <div
                style={{
                  fontSize: 16,
                  color: styles.zinc500,
                  fontFamily: "system-ui, sans-serif",
                  textTransform: "uppercase",
                  letterSpacing: "0.25em",
                }}
              >
                {stat.label}
              </div>
            </div>
          );
        })}
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          opacity: interpolate(frame, [105, 120], [0, 1]),
          padding: "18px 36px",
          background: `rgba(16,185,129,${0.1 + beatPulse * 0.05})`,
          borderRadius: 14,
          border: `1px solid rgba(16,185,129,${0.2 + beatPulse * 0.1})`,
        }}
      >
        <svg
          width="28"
          height="28"
          viewBox="0 0 24 24"
          fill="none"
          stroke={styles.emerald500}
          strokeWidth="2"
        >
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <path d="m9 12 2 2 4-4" />
        </svg>
        <span
          style={{
            fontSize: 20,
            color: styles.emerald500,
            fontFamily: "system-ui, sans-serif",
            fontWeight: 500,
          }}
        >
          Official HM Land Registry Data
        </span>
      </div>
      
      <BeatVisualizer position="bottom" />
    </AbsoluteFill>
  );
};

// =============================================================================
// SCENE 6: CTA (Bars 12.5-15 = 750-900 frames)
// Final call to action with beat-synced pulse
// =============================================================================
const Scene6CTA: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const beatPulse = useBeatPulse(frame, 1);

  const logoSpring = spring({
    frame,
    fps,
    config: { damping: 10, stiffness: 120 },
  });

  const titleOpacity = interpolate(frame, [30, 45], [0, 1]);
  const titleY = interpolate(frame, [30, 45], [40, 0], {
    easing: Easing.out(Easing.back(1.5)),
  });

  const buttonSpring = spring({
    frame: frame - 60,
    fps,
    config: { damping: 10, stiffness: 150 },
  });

  const urlOpacity = interpolate(frame, [90, 105], [0, 1]);
  const urlScale = interpolate(frame, [90, 105], [0.9, 1], {
    easing: Easing.out(Easing.back(1.2)),
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        gap: 40,
      }}
    >
      <div
        style={{
          transform: `scale(${logoSpring * 1.3 * (1 + beatPulse * 0.05)})`,
          opacity: logoSpring,
        }}
      >
        <Logo scale={1.3} pulse={beatPulse} />
      </div>

      <h2
        style={{
          fontSize: 80,
          color: styles.white,
          fontFamily: "system-ui, sans-serif",
          fontWeight: 700,
          textAlign: "center",
          letterSpacing: "-0.02em",
          opacity: titleOpacity,
          transform: `translateY(${titleY}px) scale(${1 + beatPulse * 0.02})`,
        }}
      >
        Start Searching Today
      </h2>

      <p
        style={{
          fontSize: 28,
          color: styles.zinc400,
          fontFamily: "system-ui, sans-serif",
          fontWeight: 300,
          textAlign: "center",
          opacity: titleOpacity,
          letterSpacing: "0.02em",
        }}
      >
        Free to use • Instant results
      </p>

      <div
        style={{
          transform: `scale(${Math.max(0, buttonSpring) * (1 + beatPulse * 0.08)})`,
          opacity: buttonSpring,
          background: styles.white,
          borderRadius: 60,
          padding: "28px 70px",
          boxShadow: `0 0 ${60 + beatPulse * 40}px rgba(255,255,255,${0.25 + beatPulse * 0.15})`,
        }}
      >
        <span
          style={{
            fontSize: 22,
            color: styles.background,
            fontFamily: "system-ui, sans-serif",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.15em",
          }}
        >
          Search Registry →
        </span>
      </div>

      <div
        style={{
          opacity: urlOpacity,
          transform: `scale(${urlScale})`,
          marginTop: 20,
        }}
      >
        <span
          style={{
            fontSize: 36,
            color: styles.accent,
            fontFamily: "system-ui, sans-serif",
            fontWeight: 500,
            letterSpacing: "0.05em",
          }}
        >
          landregistry.io
        </span>
      </div>
      
      <BeatVisualizer position="bottom" />
    </AbsoluteFill>
  );
};

// =============================================================================
// MAIN COMPOSITION
// =============================================================================
export const LandRegistryPromo: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: styles.background }}>
      {/* Audio Track - Using a royalty-free electronic track */}
      <Audio
        src={staticFile("music.mp3")}
        volume={0.6}
        startFrom={0}
      />

      {/* Background layers */}
      <ParticlesBackground />
      <GradientOrbs />

      {/* Scenes - each scene is 2.5 bars (150 frames / 5 seconds) */}
      <Sequence from={0} durationInFrames={150}>
        <Scene1LogoReveal />
      </Sequence>

      <Sequence from={150} durationInFrames={150}>
        <Scene2Problem />
      </Sequence>

      <Sequence from={300} durationInFrames={150}>
        <Scene3Solution />
      </Sequence>

      <Sequence from={450} durationInFrames={150}>
        <Scene4Features />
      </Sequence>

      <Sequence from={600} durationInFrames={150}>
        <Scene5Stats />
      </Sequence>

      <Sequence from={750} durationInFrames={150}>
        <Scene6CTA />
      </Sequence>
    </AbsoluteFill>
  );
};
