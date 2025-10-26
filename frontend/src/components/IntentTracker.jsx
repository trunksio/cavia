import React, { useState, useEffect } from 'react';
import { Target, CheckCircle, AlertTriangle, XCircle, TrendingUp, Shield, Award } from 'lucide-react';
import { getJobIntent, getJobValidations, getJobStatus } from '../services/api';

const IntentTracker = ({ jobId }) => {
  const [intent, setIntent] = useState(null);
  const [validations, setValidations] = useState([]);
  const [jobStatus, setJobStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [driftDetected, setDriftDetected] = useState(false);

  useEffect(() => {
    if (jobId) {
      loadIntentData();
      // Poll for updates every 3 seconds
      const interval = setInterval(loadIntentData, 3000);
      return () => clearInterval(interval);
    }
  }, [jobId]);

  useEffect(() => {
    // Check for drift
    if (validations.length > 0) {
      const avgDrift = validations.reduce((sum, v) => sum + v.drift_score, 0) / validations.length;
      const maxDrift = Math.max(...validations.map(v => v.drift_score));
      setDriftDetected(avgDrift > 0.4 || maxDrift > 0.7);
    }
  }, [validations]);

  const loadIntentData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load intent, validations, and job status in parallel
      const [intentData, validationsData, statusData] = await Promise.all([
        getJobIntent(jobId).catch(() => null),
        getJobValidations(jobId).catch(() => []),
        getJobStatus(jobId).catch(() => null),
      ]);

      setIntent(intentData);
      setValidations(validationsData);
      setJobStatus(statusData);
    } catch (err) {
      console.error('Failed to load intent data:', err);
      setError('Failed to load intent tracking data');
    } finally {
      setLoading(false);
    }
  };

  const getAlignmentColor = (score) => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getAlignmentBgColor = (score) => {
    if (score >= 0.8) return 'bg-green-100';
    if (score >= 0.6) return 'bg-yellow-100';
    return 'bg-red-100';
  };

  const getDriftColor = (score) => {
    if (score <= 0.3) return 'text-green-600';
    if (score <= 0.5) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getStatusIcon = (isAligned) => {
    return isAligned ? (
      <CheckCircle className="h-5 w-5 text-green-600" />
    ) : (
      <AlertTriangle className="h-5 w-5 text-red-600" />
    );
  };

  if (loading && !intent) {
    return (
      <div className="card">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="h-4 bg-gray-200 rounded w-2/3"></div>
          <div className="space-y-2">
            <div className="h-20 bg-gray-200 rounded"></div>
            <div className="h-20 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !intent) {
    return (
      <div className="card">
        <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg text-center">
          <p className="text-gray-600">
            {error || 'Intent tracking not available for this job'}
          </p>
        </div>
      </div>
    );
  }

  const avgAlignment = validations.length > 0
    ? validations.reduce((sum, v) => sum + v.alignment_score, 0) / validations.length
    : 0;

  const avgDrift = validations.length > 0
    ? validations.reduce((sum, v) => sum + v.drift_score, 0) / validations.length
    : 0;

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Intent Tracking</h2>
        {jobStatus && (
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            jobStatus.status === 'completed' ? 'bg-green-100 text-green-800' :
            jobStatus.status === 'failed' ? 'bg-red-100 text-red-800' :
            'bg-blue-100 text-blue-800'
          }`}>
            {jobStatus.status}
          </span>
        )}
      </div>

      {/* Drift Alert */}
      {driftDetected && (
        <div className="mb-6 p-4 bg-red-50 border-2 border-red-500 rounded-lg">
          <div className="flex items-start space-x-3">
            <XCircle className="h-6 w-6 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-red-900 mb-1">Intent Drift Detected!</h3>
              <p className="text-sm text-red-800">
                The workflow has drifted from the original intent. Review agent validations below.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Intent Goal */}
      <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-start space-x-3">
          <Target className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-blue-900 mb-1">Original Intent</h3>
            <p className="text-blue-800">{intent.goal}</p>
            <div className="mt-2 flex items-center space-x-4 text-sm">
              <span className="text-blue-700">
                Workflow: <span className="font-medium">{intent.workflow_type}</span>
              </span>
              <span className="text-blue-700">
                Stage: <span className="font-medium">{intent.current_stage || 'initiated'}</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Overall Metrics */}
      {validations.length > 0 && (
        <div className="mb-6 grid grid-cols-2 gap-4">
          <div className="p-4 bg-white border border-gray-200 rounded-lg">
            <div className="flex items-center space-x-2 mb-2">
              <TrendingUp className="h-5 w-5 text-gray-600" />
              <span className="text-sm text-gray-600">Avg Alignment</span>
            </div>
            <div className={`text-2xl font-bold ${getAlignmentColor(avgAlignment)}`}>
              {(avgAlignment * 100).toFixed(0)}%
            </div>
          </div>
          <div className="p-4 bg-white border border-gray-200 rounded-lg">
            <div className="flex items-center space-x-2 mb-2">
              <Shield className="h-5 w-5 text-gray-600" />
              <span className="text-sm text-gray-600">Avg Drift</span>
            </div>
            <div className={`text-2xl font-bold ${getDriftColor(avgDrift)}`}>
              {(avgDrift * 100).toFixed(0)}%
            </div>
          </div>
        </div>
      )}

      {/* Agent Validations */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center">
          <Award className="h-5 w-5 mr-2 text-gray-600" />
          Agent Validations
        </h3>

        {validations.length === 0 ? (
          <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg text-center">
            <p className="text-gray-600 text-sm">No validations yet. Agents will validate as they process.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {validations.map((validation, idx) => (
              <div
                key={idx}
                className={`p-4 border-2 rounded-lg ${
                  validation.is_aligned
                    ? 'border-green-200 bg-green-50'
                    : 'border-red-200 bg-red-50'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    {getStatusIcon(validation.is_aligned)}
                    <div>
                      <h4 className="font-semibold text-gray-900">
                        {validation.agent_type.toUpperCase()} Agent
                      </h4>
                      <p className="text-xs text-gray-600">{validation.agent_id}</p>
                    </div>
                  </div>
                  <div className="flex space-x-3">
                    <div className={`px-2 py-1 rounded text-xs font-medium ${getAlignmentBgColor(validation.alignment_score)}`}>
                      <span className={getAlignmentColor(validation.alignment_score)}>
                        Alignment: {(validation.alignment_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className={`px-2 py-1 rounded text-xs font-medium ${
                      validation.drift_score <= 0.3 ? 'bg-green-100' :
                      validation.drift_score <= 0.5 ? 'bg-yellow-100' : 'bg-red-100'
                    }`}>
                      <span className={getDriftColor(validation.drift_score)}>
                        Drift: {(validation.drift_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>

                <p className="text-sm text-gray-700 mb-2">{validation.reasoning}</p>

                {validation.suggestions && validation.suggestions.length > 0 && (
                  <div className="mt-2 p-2 bg-white rounded border border-gray-200">
                    <p className="text-xs font-medium text-gray-700 mb-1">Suggestions:</p>
                    <ul className="space-y-1">
                      {validation.suggestions.map((suggestion, sIdx) => (
                        <li key={sIdx} className="text-xs text-gray-600">
                          • {suggestion}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Constraints & Success Criteria */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        {intent.constraints && intent.constraints.length > 0 && (
          <div className="p-4 bg-orange-50 border border-orange-200 rounded-lg">
            <h4 className="font-medium text-orange-900 mb-2 flex items-center">
              <Shield className="h-4 w-4 mr-1" />
              Constraints
            </h4>
            <ul className="space-y-1">
              {intent.constraints.map((constraint, idx) => (
                <li key={idx} className="text-sm text-orange-800">
                  • {constraint.description || constraint.name}
                </li>
              ))}
            </ul>
          </div>
        )}

        {intent.success_criteria && intent.success_criteria.length > 0 && (
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
            <h4 className="font-medium text-green-900 mb-2 flex items-center">
              <CheckCircle className="h-4 w-4 mr-1" />
              Success Criteria
            </h4>
            <ul className="space-y-1">
              {intent.success_criteria.map((criterion, idx) => (
                <li key={idx} className="text-sm text-green-800">
                  • {criterion.description || criterion.criterion}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default IntentTracker;
