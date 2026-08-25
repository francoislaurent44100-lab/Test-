import "./index.css";
import { MyComposition } from "./Composition";
import { MyMaisonReveal } from "./MaisonReveal";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <MyComposition />
      <MyMaisonReveal />
    </>
  );
};
