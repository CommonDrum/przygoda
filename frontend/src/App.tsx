import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ToastProvider } from "./context/ToastContext";
import Layout from "./components/Layout";
import ProjectListPage from "./pages/ProjectListPage";
import NewProjectPage from "./pages/NewProjectPage";
import ProjectViewPage from "./pages/ProjectViewPage";
import SettingsPage from "./pages/SettingsPage";
import PromptsPage from "./pages/PromptsPage";
import LoginPage from "./pages/LoginPage";

function ProtectedRoute() {
  const { isLoggedIn } = useAuth();
  return isLoggedIn ? <Outlet /> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/" element={<ProjectListPage />} />
              <Route path="/new" element={<NewProjectPage />} />
              <Route path="/project/:id" element={<ProjectViewPage />} />
              <Route path="/prompts" element={<PromptsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  );
}
