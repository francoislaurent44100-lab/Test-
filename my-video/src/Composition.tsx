import {
  AbsoluteFill,
  Composition,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const COMPANY_NAME = "Nestenn";
const SLOGAN = "Le plaisir c'est vous, le reste c'est nous";
const TURQUOISE = "#0FB9B1";

const FPS = 30;
const DURATION_IN_FRAMES = 10 * FPS;
const SLOGAN_START_FRAME = 100;

export const MyComposition = () => {
  return (
    <Composition
      id="Intro"
      component={IntroVideo}
      durationInFrames={DURATION_IN_FRAMES}
      fps={FPS}
      width={1280}
      height={720}
    />
  );
};

const Letter: React.FC<{ char: string; index: number }> = ({
  char,
  index,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progress = spring({
    frame: frame - index * 3,
    fps,
    config: { damping: 200 },
  });

  return (
    <span
      style={{
        display: "inline-block",
        opacity: progress,
        transform: `translateY(${interpolate(progress, [0, 1], [20, 0])}px)`,
      }}
    >
      {char === " " ? " " : char}
    </span>
  );
};

export const IntroVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, height } = useVideoConfig();

  const sloganSpring = spring({
    frame: frame - SLOGAN_START_FRAME,
    fps,
    config: { damping: 200 },
  });
  const sloganTranslateY = interpolate(sloganSpring, [0, 1], [height, 0]);
  const sloganOpacity = interpolate(
    frame,
    [SLOGAN_START_FRAME, SLOGAN_START_FRAME + 15],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <AbsoluteFill
      style={{
        backgroundColor: TURQUOISE,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        style={{
          fontSize: 110,
          fontWeight: 700,
          color: "white",
          fontFamily: "Arial, Helvetica, sans-serif",
          letterSpacing: 4,
        }}
      >
        {COMPANY_NAME.split("").map((char, i) => (
          <Letter key={i} char={char} index={i} />
        ))}
      </div>

      <div
        style={{
          position: "absolute",
          bottom: 110,
          width: "100%",
          textAlign: "center",
          fontSize: 38,
          color: "white",
          fontFamily: "Arial, Helvetica, sans-serif",
          opacity: sloganOpacity,
          transform: `translateY(${sloganTranslateY}px)`,
        }}
      >
        {SLOGAN}
      </div>
    </AbsoluteFill>
  );
};

export const MyComponent = IntroVideo;
