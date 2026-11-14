/**
 * Shared navigation bar for authenticated pages.
 */

import { useNavigate, Link as RouterLink, useLocation } from 'react-router-dom';
import { AppBar, Toolbar, Typography, Button, IconButton } from '@mui/material';
import { CloudUpload, History, Person, Logout } from '@mui/icons-material';
import authService from '../services/authService';

const LINKS = [
  { to: '/upload', label: 'Загрузить', icon: <CloudUpload /> },
  { to: '/history', label: 'История', icon: <History /> },
  { to: '/profile', label: 'Профиль', icon: <Person /> },
];

export default function Header() {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  return (
    <AppBar position="static">
      <Toolbar sx={{ overflowX: 'auto' }}>
        <Typography
          variant="h6"
          component={RouterLink}
          to="/upload"
          sx={{ flexGrow: 1, color: 'inherit', textDecoration: 'none' }}
        >
          Hustl Analyzer
        </Typography>
        {LINKS.map((link) => {
          const active = location.pathname.startsWith(link.to);
          return (
            <Button
              key={link.to}
              color="inherit"
              component={RouterLink}
              to={link.to}
              startIcon={link.icon}
              aria-current={active ? 'page' : undefined}
              sx={{ fontWeight: active ? 700 : 400 }}
            >
              {link.label}
            </Button>
          );
        })}
        <IconButton color="inherit" onClick={handleLogout} aria-label="Выйти" title="Выйти">
          <Logout />
        </IconButton>
      </Toolbar>
    </AppBar>
  );
}
