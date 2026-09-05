import { HashRouter, Link, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ReviewerProvider } from "./lib/reviewer";
import ActionItemsPage from "./pages/ActionItemsPage";
import BusinessCasePage from "./pages/BusinessCasePage";
import DashboardPage from "./pages/DashboardPage";
import DiffPage from "./pages/DiffPage";
import DocumentPage from "./pages/DocumentPage";
import DocumentsPage from "./pages/DocumentsPage";
import EvidencePage from "./pages/EvidencePage";
import MiningPage from "./pages/MiningPage";
import ReviewQueuePage from "./pages/ReviewQueuePage";
import RunsPage from "./pages/RunsPage";
import TerminologyPage from "./pages/TerminologyPage";

// HashRouter: the bundle is served as static files by the backend, so deep links must not need server routing.
export default function App() {
  return (
    <ReviewerProvider>
      <HashRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<RunsPage />} />
            <Route path="/runs/:runId" element={<DashboardPage />} />
            <Route path="/runs/:runId/review" element={<ReviewQueuePage />} />
            <Route path="/runs/:runId/rows/:rowId" element={<EvidencePage />} />
            <Route path="/runs/:runId/documents" element={<DocumentsPage />} />
            <Route path="/runs/:runId/documents/:docId" element={<DocumentPage />} />
            <Route path="/runs/:runId/mining" element={<MiningPage />} />
            <Route path="/runs/:runId/business" element={<BusinessCasePage />} />
            <Route path="/runs/:runId/diff" element={<DiffPage />} />
            <Route path="/terminology" element={<TerminologyPage />} />
            <Route path="/action-items" element={<ActionItemsPage />} />
            <Route
              path="*"
              element={
                <div className="text-xs">
                  Page not found.{" "}
                  <Link className="underline" to="/">
                    Back to runs
                  </Link>
                </div>
              }
            />
          </Route>
        </Routes>
      </HashRouter>
    </ReviewerProvider>
  );
}
