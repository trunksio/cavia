import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  Download,
  Eye,
} from 'lucide-react';
import { getJobStatus } from '../services/api';
import clsx from 'clsx';

const STATUS_CONFIG = {
  pending: {
    label: 'Pending',
    icon: Clock,
    color: 'text-gray-600',
    bgColor: 'bg-gray-100',
    description: 'Waiting to start processing',
  },
  parsing: {
    label: 'Parsing',
    icon: Loader2,
    color: 'text-primary-600',
    bgColor: 'bg-primary-100',
    description: 'Extracting information from CV',
    animate: true,
  },
  evaluating: {
    label: 'Evaluating',
    icon: Loader2,
    color: 'text-warning-600',
    bgColor: 'bg-warning-100',
    description: 'Analyzing candidate qualifications',
    animate: true,
  },
  generating_report: {
    label: 'Generating Report',
    icon: Loader2,
    color: 'text-purple-600',
    bgColor: 'bg-purple-100',
    description: 'Creating evaluation report',
    animate: true,
  },
  completed: {
    label: 'Completed',
    icon: CheckCircle,
    color: 'text-success-600',
    bgColor: 'bg-success-100',
    description: 'Processing complete',
  },
  failed: {
    label: 'Failed',
    icon: XCircle,
    color: 'text-danger-600',
    bgColor: 'bg-danger-100',
    description: 'Processing failed',
  },
};

const JobStatusCard = ({ jobId, initialData, autoRefresh = false, compact = false }) => {
  const [job, setJob] = useState(initialData);
  const [loading, setLoading] = useState(!initialData);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const fetchStatus = async () => {
    try {
      setLoading(true);
      const data = await getJobStatus(jobId);
      setJob(data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch job status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!initialData) {
      fetchStatus();
    }
  }, [jobId, initialData]);

  // Auto-refresh for in-progress jobs
  useEffect(() => {
    if (!autoRefresh || !job) return;

    const isInProgress = ['pending', 'parsing', 'evaluating', 'generating_report'].includes(
      job.status
    );

    if (isInProgress) {
      const interval = setInterval(fetchStatus, 3000); // Refresh every 3 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh, job?.status]);

  if (loading && !job) {
    return (
      <div className="card">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 text-primary-600 animate-spin" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="flex items-center space-x-3 text-danger-600">
          <XCircle className="h-5 w-5" />
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!job) return null;

  const statusConfig = STATUS_CONFIG[job.status] || STATUS_CONFIG.pending;
  const StatusIcon = statusConfig.icon;

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  if (compact) {
    return (
      <div
        className="card hover:shadow-lg transition-shadow cursor-pointer"
        onClick={() => navigate(`/jobs/${job.job_id}`)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 flex-1">
            <FileText className="h-8 w-8 text-gray-400" />
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-gray-800 truncate">
                {job.filename}
              </h3>
              <p className="text-sm text-gray-500">{formatDate(job.submitted_at)}</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <span className={clsx('badge', `badge-${job.status}`)}>
              {statusConfig.label}
            </span>
            <Eye className="h-5 w-5 text-gray-400" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center space-x-3">
          <FileText className="h-8 w-8 text-gray-400" />
          <div>
            <h3 className="text-xl font-bold text-gray-800">{job.filename}</h3>
            <p className="text-sm text-gray-500">Job ID: {job.job_id}</p>
          </div>
        </div>
        <span className={clsx('badge text-sm px-3 py-1', `badge-${job.status}`)}>
          {statusConfig.label}
        </span>
      </div>

      {/* Status */}
      <div className="mb-6">
        <div className="flex items-center space-x-3 mb-2">
          <StatusIcon
            className={clsx(statusConfig.color, 'h-6 w-6', {
              'animate-spin': statusConfig.animate,
            })}
          />
          <span className="text-lg font-medium text-gray-700">
            {statusConfig.description}
          </span>
        </div>
      </div>

      {/* Timeline */}
      <div className="space-y-3 mb-6">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Submitted:</span>
          <span className="font-medium text-gray-800">{formatDate(job.submitted_at)}</span>
        </div>
        {job.started_at && (
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Started:</span>
            <span className="font-medium text-gray-800">{formatDate(job.started_at)}</span>
          </div>
        )}
        {job.completed_at && (
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Completed:</span>
            <span className="font-medium text-gray-800">
              {formatDate(job.completed_at)}
            </span>
          </div>
        )}
      </div>

      {/* Error Message */}
      {job.error_message && (
        <div className="mb-6 p-4 bg-danger-50 border border-danger-200 rounded-lg">
          <p className="text-sm text-danger-800">{job.error_message}</p>
        </div>
      )}

      {/* Actions */}
      {job.status === 'completed' && (
        <div className="flex space-x-3">
          <button
            onClick={() => navigate(`/jobs/${job.job_id}/results`)}
            className="btn btn-primary flex-1 flex items-center justify-center space-x-2"
          >
            <Eye className="h-5 w-5" />
            <span>View Results</span>
          </button>
        </div>
      )}
    </div>
  );
};

export default JobStatusCard;
