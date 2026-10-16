import { GuidePage } from "../components/GuidePage";
import tutorial from "../content/tutorial.json";

export default function TutorialPage() {
  return <GuidePage guide={tutorial} />;
}
