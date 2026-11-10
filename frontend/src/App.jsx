import React, { useState } from 'react';
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  Outlet,
} from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { RepositoryProvider } from './context/RepositoryContext';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import NewJobModal from './components/NewJobModal';
import Home from './pages/Home';
import SearchResults from './pages/SearchResults';
import Repositories from './pages/Repositories';
import RepositoryDetails from './pages/RepositoryDetails';
import Documentation from './pages/Documentation';
import Login from './pages/Login';

function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-surface-container-lowest text-on-surface font-body-md flex flex-col">
      <Sidebar mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />
      <div className="md:pl-64 flex flex-col min-h-screen transition-all">
        <Header setMobileOpen={setMobileOpen} />
        <main className="w-full pt-14 flex-1 bg-surface-container-lowest">
          <Outlet />
        </main>
      </div>
      <NewJobModal />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            element={
              <RepositoryProvider>
                <AppLayout />
              </RepositoryProvider>
            }
          >
            <Route path="/" element={<Home />} />
            <Route path="/search" element={<SearchResults />} />
            <Route path="/repositories" element={<Repositories />} />
            <Route path="/repositories/:id" element={<RepositoryDetails />} />
            <Route path="/jobs" element={<Repositories />} />
            <Route path="/docs" element={<Documentation />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
