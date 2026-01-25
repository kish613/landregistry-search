import { Composition } from "remotion";
import { LandRegistryPromo } from "./LandRegistryPromo";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="LandRegistryPromo"
        component={LandRegistryPromo}
        durationInFrames={900} // 30 seconds at 30fps
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
