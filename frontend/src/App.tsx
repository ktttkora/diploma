/**
 * Application root: routing and theme.
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import UploadPage from './pages/UploadPage';
import ProcessingPage from './pages/ProcessingPage';
import ResultsPage from './pages/ResultsPage';
import HistoryPage from './pages/HistoryPage';
import authService from './services/authService';

const theme = createTheme({
  palette: {
    primary: {
      main: '#7b1fa2',
    },
    secondary: {
      main: '#f50057',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
});

/** Redirect to login when the visitor is not authenticated. */
function PrivateRoute({ children }: { children: React.ReactNode }) {
  return authService.isAuthenticated() ? <>{children}</> : <Navigate to="/login" replace />;
}

/** Redirect to the upload page when the visitor is already authenticated. */
function PublicRoute({ children }: { children: React.ReactNode }) {
  return authService.isAuthenticated() ? <Navigate to="/upload" replace /> : <>{children}</>;
}

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <Routes>
          <Route
            path="/login"
            element={
              <PublicRoute>
                <LoginPage />
              </PublicRoute>
            }
          />
          <Route
            path="/register"
            element={
              <PublicRoute>
                <RegisterPage />
              </PublicRoute>
            }
          />
          <Route
            path="/upload"
            element={
              <PrivateRoute>
                <UploadPage />
              </PrivateRoute>
            }
          />
          <Route
            path="/processing/:analysisId"
            element={
              <PrivateRoute>
                <ProcessingPage />
              </PrivateRoute>
            }
          />
          <Route
            path="/results/:analysisId"
            element={
              <PrivateRoute>
                <ResultsPage />
              </PrivateRoute>
            }
          />
          <Route
            path="/history"
            element={
              <PrivateRoute>
                <HistoryPage />
              </PrivateRoute>
            }
          />
          <Route path="/" element={<Navigate to="/upload" replace />} />
          <Route path="*" element={<Navigate to="/upload" replace />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}
