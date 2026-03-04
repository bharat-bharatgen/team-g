import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { Layout } from '@/components/layout/Layout';
import { LoginPage } from '@/pages/auth/LoginPage';
import { SignupPage } from '@/pages/auth/SignupPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { NewCasePage } from '@/pages/NewCasePage';
import { CaseDetailPage } from '@/pages/CaseDetailPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { useToast } from '@/hooks/useToast';
import { ToastContainer } from '@/components/ui/toast';

function App() {
  const { toasts, dismiss } = useToast();

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
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Routes>

      <ToastContainer toasts={toasts} onClose={dismiss} />
    </BrowserRouter>
  );
}

export default App;
