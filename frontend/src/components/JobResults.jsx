import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Download,
  CheckCircle,
  XCircle,
  TrendingUp,
  TrendingDown,
  FileText,
  Loader2,
} from 'lucide-react';
import { getJobResult, downloadReport } from '../services/api';
import clsx from 'clsx';

const JobResults = () => {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [downloadingReport, setDownloadingReport] = useState(false);

  useEffect(() => {
    fetchResults();
  }, [jobId]);

  const fetchResults = async () => {
    try {
      setLoading(true);
      const data = await getJobResult(jobId);
      setResult(data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch results');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadReport = async () => {
    try {
      setDownloadingReport(true);
      const blob = await downloadReport(jobId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cv_report_${jobId}.md`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert('Failed to download report');
    } finally {
      setDownloadingReport(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto p-6">
        <div className="card">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-12 w-12 text-primary-600 animate-spin" />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto p-6">
        <div className="card">
          <div className="flex items-center space-x-3 text-danger-600 mb-4">
            <XCircle className="h-6 w-6" />
            <p className="text-lg">{error}</p>
          </div>
          <button onClick={() => navigate('/')} className="btn btn-secondary">
            <ArrowLeft className="h-5 w-5 mr-2" />
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  if (!result) return null;

  const isAccepted = result.recommendation === 'SUITABLE';
  const overallScore = result.overall_score || 0;

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/')}
          className="btn btn-secondary flex items-center space-x-2"
        >
          <ArrowLeft className="h-5 w-5" />
          <span>Back</span>
        </button>
        {result.report_url && (
          <button
            onClick={handleDownloadReport}
            disabled={downloadingReport}
            className="btn btn-primary flex items-center space-x-2"
          >
            <Download className="h-5 w-5" />
            <span>{downloadingReport ? 'Downloading...' : 'Download Report'}</span>
          </button>
        )}
      </div>

      {/* Overview Card */}
      <div className="card">
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center space-x-3">
            <FileText className="h-10 w-10 text-gray-400" />
            <div>
              <h1 className="text-3xl font-bold text-gray-800">{result.filename}</h1>
              <p className="text-sm text-gray-500">Job ID: {result.job_id}</p>
            </div>
          </div>
          <div
            className={clsx('px-6 py-3 rounded-lg flex items-center space-x-2', {
              'bg-success-100': isAccepted,
              'bg-danger-100': !isAccepted,
            })}
          >
            {isAccepted ? (
              <>
                <CheckCircle className="h-6 w-6 text-success-600" />
                <span className="text-xl font-bold text-success-800">SUITABLE</span>
              </>
            ) : (
              <>
                <XCircle className="h-6 w-6 text-danger-600" />
                <span className="text-xl font-bold text-danger-800">REJECTED</span>
              </>
            )}
          </div>
        </div>

        {/* Overall Score */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-lg font-medium text-gray-700">Overall Score</span>
            <span className="text-3xl font-bold text-gray-800">
              {(overallScore * 100).toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-4">
            <div
              className={clsx('h-4 rounded-full transition-all', {
                'bg-success-500': overallScore >= 0.7,
                'bg-warning-500': overallScore >= 0.5 && overallScore < 0.7,
                'bg-danger-500': overallScore < 0.5,
              })}
              style={{ width: `${overallScore * 100}%` }}
            />
          </div>
        </div>

        {/* Summary */}
        {result.summary && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-2">Summary</h3>
            <p className="text-gray-700">{result.summary}</p>
          </div>
        )}

        {/* Strengths and Concerns */}
        <div className="grid md:grid-cols-2 gap-6">
          {result.strengths && result.strengths.length > 0 && (
            <div>
              <div className="flex items-center space-x-2 mb-3">
                <TrendingUp className="h-5 w-5 text-success-600" />
                <h3 className="text-lg font-semibold text-gray-800">Strengths</h3>
              </div>
              <ul className="space-y-2">
                {result.strengths.map((strength, idx) => (
                  <li key={idx} className="flex items-start space-x-2">
                    <CheckCircle className="h-5 w-5 text-success-600 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">{strength}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.concerns && result.concerns.length > 0 && (
            <div>
              <div className="flex items-center space-x-2 mb-3">
                <TrendingDown className="h-5 w-5 text-danger-600" />
                <h3 className="text-lg font-semibold text-gray-800">Concerns</h3>
              </div>
              <ul className="space-y-2">
                {result.concerns.map((concern, idx) => (
                  <li key={idx} className="flex items-start space-x-2">
                    <XCircle className="h-5 w-5 text-danger-600 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">{concern}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Detailed Evaluations */}
      {result.evaluations && result.evaluations.length > 0 && (
        <div className="card">
          <h2 className="text-2xl font-bold text-gray-800 mb-6">Detailed Evaluation</h2>
          <div className="space-y-6">
            {result.evaluations.map((evaluation) => (
              <div
                key={evaluation.criterion_id}
                className="border border-gray-200 rounded-lg p-6"
              >
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-xl font-semibold text-gray-800">
                      {evaluation.criterion_name}
                    </h3>
                    <p className="text-sm text-gray-500">
                      Weight: {(evaluation.weight * 100).toFixed(0)}%
                    </p>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-gray-800">
                      {(evaluation.score * 100).toFixed(1)}%
                    </div>
                    <div className="text-sm text-gray-500">
                      Confidence: {(evaluation.confidence * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>

                <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
                  <div
                    className={clsx('h-3 rounded-full', {
                      'bg-success-500': evaluation.score >= 0.7,
                      'bg-warning-500': evaluation.score >= 0.5 && evaluation.score < 0.7,
                      'bg-danger-500': evaluation.score < 0.5,
                    })}
                    style={{ width: `${evaluation.score * 100}%` }}
                  />
                </div>

                <div className="space-y-3">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-700 mb-1">Reasoning</h4>
                    <p className="text-gray-600 text-sm">{evaluation.reasoning}</p>
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-700 mb-1">Evidence</h4>
                    <p className="text-gray-600 text-sm">{evaluation.evidence}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Detailed Analysis */}
      {result.detailed_analysis && (
        <div className="card">
          <h2 className="text-2xl font-bold text-gray-800 mb-4">Detailed Analysis</h2>
          <div className="prose max-w-none">
            <p className="text-gray-700 whitespace-pre-wrap">{result.detailed_analysis}</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default JobResults;
