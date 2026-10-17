import { Component, type ReactNode } from "react";
import { Button, Card, LinkButton, PageHeader } from "./ui";

/** Keep navigation available if an individual screen cannot render. */
export class ScreenBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (!this.state.failed) return this.props.children;
    return <div role="alert"><PageHeader title="This screen could not be displayed" description="Reload the page to try again, or return to your runs." /><Card className="p-5 flex flex-wrap gap-3"><Button onClick={() => window.location.reload()}>Reload page</Button><LinkButton to="/">All runs</LinkButton></Card></div>;
  }
}
