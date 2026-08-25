import {
  AbsoluteFill,
  Composition,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const SUBTITLE_LINE_1 = "Devine le prix de cette maison";
const SUBTITLE_LINE_2 = "vendue en deux semaines";

const FPS = 30;
const DURATION_IN_FRAMES = 5 * FPS;
const SUBTITLE_START_FRAME = 15;

export const MyMaisonReveal = () => {
  return (
    <Composition
      id="MaisonReveal"
      component={MaisonRevealVideo}
      durationInFrames={DURATION_IN_FRAMES}
      fps={FPS}
      width={1280}
      height={720}
    />
  );
};

export const MaisonRevealVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = interpolate(frame, [0, DURATION_IN_FRAMES], [1, 1.25], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const subtitleSpring = spring({
    frame: frame - SUBTITLE_START_FRAME,
    fps,
    config: { damping: 200 },
  });
  const subtitleOpacity = interpolate(subtitleSpring, [0, 1], [0, 1]);
  const subtitleTranslateY = interpolate(subtitleSpring, [0, 1], [30, 0]);

  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: "black" }}>
      <Img
        src={staticFile("maison.jpg")}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale})`,
          transformOrigin: "center center",
        }}
      />

      <AbsoluteFill
        style={{
          background:
            "linear-gradient(to top, rgba(0,0,0,0.65) 0%, rgba(0,0,0,0) 35%)",
        }}
      />

      <div
        style={{
          position: "absolute",
          bottom: 70,
          width: "100%",
          textAlign: "center",
          color: "white",
          fontFamily: "Arial, Helvetica, sans-serif",
          fontWeight: 700,
          fontSize: 46,
          lineHeight: 1.3,
          textShadow: "0 2px 8px rgba(0,0,0,0.6)",
          opacity: subtitleOpacity,
          transform: `translateY(${subtitleTranslateY}px)`,
        }}
      >
        <div>{SUBTITLE_LINE_1}</div>
        <div>{SUBTITLE_LINE_2}</div>
      </div>
    </AbsoluteFill>
  );
};
