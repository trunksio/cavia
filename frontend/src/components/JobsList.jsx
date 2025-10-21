import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, RefreshCw, Filter } from 'lucide-react';
import { listJobs } from '../services/api';
import JobStatusCard from './JobStatusCard';
import clsx from 'clsx';

const STATUSES = [
  { value: '', label: 'All Jobs' },
  { value: 'pending', label: 'Pending' },
  { value: 'parsing', label: 'Parsing' },
  { value: 'evaluating', label: 'Evaluating' },
  { value: 'generating_report', label: 'Generating Report' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
];

const JobsList = ({ refreshTrigger }) => {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [limit] = useState(50);
  const [offset] = useState(0);
  const navigate = useNavigate();

  const fetchJobs = async () => {
    try {
      setLoading(true);
      const params = {
        limit,
        offset,
      };
      if (statusFilter) {
        params.status = statusFilter;
      }
      const data = await listJobs(params);
      setJobs(data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch jobs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [statusFilter, refreshTrigger]);

  // Auto-refresh for in-progress jobs
  useEffect(() => {
    const hasInProgressJobs = jobs.some((job) =>
      ['pending', 'parsing', 'evaluating', 'generating_report'].includes(job.status)
    );

    if (hasInProgressJobs) {
      const interval = setInterval(fetchJobs, 5000); // Refresh every 5 seconds
      return () => clearInterval(interval);
    }
  }, [jobs]);

  if (loading && jobs.length === 0) {
    return (
      <div className="card">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-12 w-12 text-primary-600 animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header and Filters */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-800">All Jobs</h2>
          <button
            onClick={fetchJobs}
            disabled={loading}
            className="btn btn-secondary flex items-center space-x-2"
          >
            <RefreshCw className={clsx('h-5 w-5', { 'animate-spin': loading })} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Status Filter */}
        <div className="flex items-center space-x-3">
          <Filter className="h-5 w-5 text-gray-500" />
          <div className="flex flex-wrap gap-2">
            {STATUSES.map((status) => (
              <button
                key={status.value}
                onClick={() => setStatusFilter(status.value)}
                className={clsx(
                  'px-4 py-2 rounded-lg text-sm font-medium transition-all',
                  statusFilter === status.value
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                )}
              >
                {status.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="card">
          <p className="text-danger-600">{error}</p>
        </div>
      )}

      {/* Jobs List */}
      {jobs.length === 0 ? (
        <div className="card">
          <p className="text-center text-gray-500 py-8">
            {statusFilter
              ? `No jobs found with status "${statusFilter}"`
              : 'No jobs yet. Upload a CV to get started!'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {jobs.map((job) => (
            <JobStatusCard key={job.job_id} jobId={job.job_id} initialData={job} compact />
          ))}
        </div>
      )}
    </div>
  );
};

export default JobsList;
