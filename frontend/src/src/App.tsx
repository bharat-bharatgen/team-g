import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { Layout } from './components/layout/Layout';
import { LoginPage } from './pages/auth/LoginPage';
import { SignupPage } from './pages/auth/SignupPage';
import { DashboardPage } from './pages/DashboardPage';
import { NewCasePage } from './pages/NewCasePage';
import { CaseDetailPage } from './pages/CaseDetailPage';
import { ReviewPage } from './pages/ReviewPage';
import { RiskAnalysisPage } from './pages/RiskAnalysisPage';
import { MERResultPage } from './pages/MERResultPage';
import { PathologyResultPage } from './pages/PathologyResultPage';
import { FaceMatchResultPage } from './pages/FaceMatchResultPage';
import { LocationCheckResultPage } from './pages/LocationCheckResultPage';
import { TestVerificationResultPage } from './pages/TestVerificationResultPage';
import { NotFoundPage } from './pages/NotFoundPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="cases/new" element={<NewCasePage />} />
          <Route path="cases/:id" element={<CaseDetailPage />} />
          <Route path="cases/:id/review" element={<ReviewPage />} />
          <Route path="cases/:id/risk-analysis" element={<RiskAnalysisPage />} />
          <Route path="cases/:id/mer-results" element={<MERResultPage />} />
          <Route path="cases/:id/pathology-results" element={<PathologyResultPage />} />
          <Route path="cases/:id/face-match" element={<FaceMatchResultPage />} />
          <Route path="cases/:id/location-check" element={<LocationCheckResultPage />} />
          <Route path="cases/:id/test-verification" element={<TestVerificationResultPage />} />
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
