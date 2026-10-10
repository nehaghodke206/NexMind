import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { ProjectListPage } from './pages/ProjectListPage';
import { IncidentListPage } from './pages/IncidentListPage';
import { IncidentDetailPage } from './pages/IncidentDetailPage';
import { ActivityFeedPage } from './pages/ActivityFeedPage';
import { NotFoundPage } from './pages/NotFoundPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<Navigate to="/projects" replace />} />
          <Route path="projects" element={<ProjectListPage />} />
          <Route path="projects/:projectId/incidents" element={<IncidentListPage />} />
          <Route path="projects/:projectId/activity" element={<ActivityFeedPage />} />
          <Route path="incidents" element={<IncidentListPage />} />
          <Route path="incidents/:incidentId" element={<IncidentDetailPage />} />
          <Route path="activity" element={<ActivityFeedPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
