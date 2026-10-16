import { lazy, Suspense } from "react";
import { Loading } from "./components/Feedback";
import { HashRouter, Navigate, Route, Routes, useParams } from "react-router-dom";
import { enc } from "./lib/format";
import { Layout } from "./components/Layout";
import { ReviewerProvider } from "./lib/reviewer";
import { ToastProvider } from "./lib/toast";
import { LinkButton, PageHeader } from "./components/ui";
const ActionItemsPage = lazy(() => import("./pages/ActionItemsPage"));
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const DiffPage = lazy(() => import("./pages/DiffPage"));
const DocumentPage = lazy(() => import("./pages/DocumentPage"));
const DocumentsPage = lazy(() => import("./pages/DocumentsPage"));
const EvidencePage = lazy(() => import("./pages/EvidencePage"));
const MiningPage = lazy(() => import("./pages/MiningPage"));
const LearningPage = lazy(() => import("./pages/LearningPage"));
const ReviewQueuePage = lazy(() => import("./pages/ReviewQueuePage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));
const RunsPage = lazy(() => import("./pages/RunsPage"));
const TerminologyPage = lazy(() => import("./pages/TerminologyPage"));
const TutorialPage = lazy(() => import("./pages/TutorialPage"));
const PrivacyPage = lazy(() => import("./pages/PrivacyPage"));
const ProfilePage = lazy(() => import("./pages/ProfilePage"));

// HashRouter: the bundle is served as static files by the backend, so deep links must not need server routing.
export default function App() {
  return (
    <ReviewerProvider>
      <ToastProvider>
      <HashRouter>
        <Suspense fallback={<Loading label="Loading screen" lines={5} />}>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<RunsPage />} />
            <Route path="/admin" element={<AdminPage />} />
            <Route path="/tutorial" element={<TutorialPage />} />
            <Route path="/privacy" element={<PrivacyPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/runs/:runId" element={<DashboardPage />} />
            <Route path="/runs/:runId/review" element={<ReviewQueuePage />} />
            <Route path="/runs/:runId/rows/:rowId" element={<EvidencePage />} />
            <Route path="/runs/:runId/documents" element={<DocumentsPage />} />
            <Route path="/runs/:runId/documents/:docId" element={<DocumentPage />} />
            <Route path="/runs/:runId/mining" element={<MiningPage />} />
            <Route path="/runs/:runId/learning" element={<LearningPage />} />
            <Route path="/runs/:runId/business" element={<RunOverviewRedirect />} />
            <Route path="/runs/:runId/diff" element={<DiffPage />} />
            <Route path="/terminology" element={<TerminologyPage />} />
            <Route path="/action-items" element={<ActionItemsPage />} />
            <Route
              path="*"
              element={
                <div>
                  <PageHeader title="Page not found" description="The address doesn’t match a page in Kaizen." />
                  <LinkButton to="/" variant="primary">Back to runs</LinkButton>
                </div>
              }
            />
          </Route>
        </Routes>
        </Suspense>
      </HashRouter>
      </ToastProvider>
    </ReviewerProvider>
  );
}

// Preserve saved links to the retired estimate screen.
function RunOverviewRedirect() {
  const { runId = "" } = useParams();
  return <Navigate replace to={`/runs/${enc(runId)}`} />;
}
