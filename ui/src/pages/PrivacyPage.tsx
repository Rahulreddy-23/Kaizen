import { GuidePage } from "../components/GuidePage";
import privacy from "../content/privacy.json";

export default function PrivacyPage() {
  return <GuidePage guide={privacy} policy />;
}
