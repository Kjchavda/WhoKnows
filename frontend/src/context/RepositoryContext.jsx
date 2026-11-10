import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { listRepositories, getJobStatus, checkBackendHealth } from '../services/api';

const RepositoryContext = createContext(null);

const STORAGE_KEY_SELECTED = 'whoknows_selected_repo';
const STORAGE_KEY_JOBS = 'whoknows_indexing_jobs';

export function RepositoryProvider({ children }) {
  const [repositories, setRepositories] = useState([]);
  const [loadingRepositories, setLoadingRepositories] = useState(true);
  const [repositoriesError, setRepositoriesError] = useState(null);

  const [selectedRepo, setSelectedRepoState] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY_SELECTED);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [jobs, setJobs] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY_JOBS);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [backendHealth, setBackendHealth] = useState({ healthy: true, latencyMs: 24 });
  const [isNewJobModalOpen, setIsNewJobModalOpen] = useState(false);

  // Persist selected repo
  const setSelectedRepo = useCallback((repo) => {
    setSelectedRepoState(repo);
    try {
      if (repo) {
        localStorage.setItem(STORAGE_KEY_SELECTED, JSON.stringify(repo));
      } else {
        localStorage.removeItem(STORAGE_KEY_SELECTED);
      }
    } catch {
      // Ignore localStorage write failures
    }
  }, []);

  // Persist jobs to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY_JOBS, JSON.stringify(jobs));
    } catch {
      // Ignore
    }
  }, [jobs]);

  // Fetch repositories from backend
  const fetchRepositories = useCallback(async () => {
    setLoadingRepositories(true);
    setRepositoriesError(null);
    try {
      const list = await listRepositories();
      const repos = Array.isArray(list) ? list : [];
      setRepositories(repos);

      // Auto-select first repo if none selected or if selected is not in list
      setSelectedRepoState((current) => {
        if (!current && repos.length > 0) {
          const first = repos[0];
          try {
            localStorage.setItem(STORAGE_KEY_SELECTED, JSON.stringify(first));
          } catch {}
          return first;
        }
        if (current && repos.length > 0) {
          const stillExists = repos.find(r => r.github_id === current.github_id);
          if (stillExists) return stillExists;
        }
        return current || (repos.length > 0 ? repos[0] : null);
      });
    } catch (err) {
      console.error('Failed to load repositories:', err);
      setRepositoriesError(err.message || 'Failed to load repositories from backend');
    } finally {
      setLoadingRepositories(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchRepositories();
  }, [fetchRepositories]);

  // Periodic backend health ping
  useEffect(() => {
    const checkHealth = async () => {
      const health = await checkBackendHealth();
      setBackendHealth(health);
    };
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  // Add new job
  const addJob = useCallback((job) => {
    const newJob = {
      job_id: job.job_id,
      repository: job.repository,
      status: job.status || 'queued',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      ...job,
    };
    setJobs((prev) => [newJob, ...prev.filter(j => j.job_id !== job.job_id)]);
    return newJob;
  }, []);

  // Update existing job
  const updateJob = useCallback((jobId, updates) => {
    setJobs((prev) =>
      prev.map((job) =>
        job.job_id === jobId
          ? { ...job, ...updates, updatedAt: new Date().toISOString() }
          : job
      )
    );
  }, []);

  // Active jobs polling worker: Polls all jobs that are still 'queued' or 'started' or 'deferred'
  useEffect(() => {
    const activeJobs = jobs.filter(
      (job) => job.status === 'queued' || job.status === 'started' || job.status === 'deferred'
    );

    if (activeJobs.length === 0) return;

    const interval = setInterval(async () => {
      for (const job of activeJobs) {
        try {
          const statusData = await getJobStatus(job.job_id);
          if (statusData && statusData.status !== job.status) {
            updateJob(job.job_id, {
              status: statusData.status,
              result: statusData.result,
              error: statusData.error,
            });

            // If job just finished successfully, refresh repositories list
            if (statusData.status === 'finished') {
              fetchRepositories();
            }
          }
        } catch (err) {
          console.warn(`Polling error for job ${job.job_id}:`, err);
        }
      }
    }, 2500);

    return () => clearInterval(interval);
  }, [jobs, updateJob, fetchRepositories]);

  const value = {
    repositories,
    loadingRepositories,
    repositoriesError,
    selectedRepo,
    setSelectedRepo,
    refreshRepositories: fetchRepositories,
    jobs,
    addJob,
    updateJob,
    backendHealth,
    isNewJobModalOpen,
    setIsNewJobModalOpen,
  };

  return (
    <RepositoryContext.Provider value={value}>
      {children}
    </RepositoryContext.Provider>
  );
}

export function useRepositories() {
  const context = useContext(RepositoryContext);
  if (!context) {
    throw new Error('useRepositories must be used within a RepositoryProvider');
  }
  return context;
}

