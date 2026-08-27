import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ArchitecturePage } from "./pages/ArchitecturePage";
import { BenchmarksPage } from "./pages/BenchmarksPage";
import { InsightsPage } from "./pages/InsightsPage";
import { MetricsPage } from "./pages/MetricsPage";
import { OverviewPage } from "./pages/OverviewPage";
import { ProjectsListPage } from "./pages/ProjectsListPage";
import { TestsPage } from "./pages/TestsPage";
import { TrendsPage } from "./pages/TrendsPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/projects" replace />} />
      <Route path="/projects" element={<ProjectsListPage />} />
      <Route path="/projects/:projectId" element={<Layout />}>
        <Route index element={<Navigate to="overview" replace />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="metrics" element={<MetricsPage />} />
        <Route path="trends" element={<TrendsPage />} />
        <Route path="tests" element={<TestsPage />} />
        <Route path="benchmarks" element={<BenchmarksPage />} />
        <Route path="insights" element={<InsightsPage />} />
        <Route path="architecture" element={<ArchitecturePage />} />
      </Route>
      <Route path="*" element={<p className="p-8 text-slate-500">Not found</p>} />
    </Routes>
  );
}