import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import {
  getCurrentUser,
  getGitHubLoginUrl,
  logout as logoutRequest,
} from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loadingUser, setLoadingUser] = useState(true);
  const [authError, setAuthError] = useState(null);

  const refreshUser = useCallback(async () => {
    setLoadingUser(true);
    try {
      const response = await getCurrentUser();
      setUser(response.user);
      setAuthError(null);
      return response.user;
    } catch (error) {
      setUser(null);
      if (error.status === 401) {
        setAuthError(null);
        return null;
      }
      setAuthError(error.message || 'Unable to check your sign-in status.');
      return null;
    } finally {
      setLoadingUser(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const signInWithGitHub = useCallback(() => {
    window.location.assign(getGitHubLoginUrl());
  }, []);

  const signOut = useCallback(async () => {
    await logoutRequest();
    setUser(null);
    setAuthError(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        loadingUser,
        authError,
        refreshUser,
        signInWithGitHub,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
