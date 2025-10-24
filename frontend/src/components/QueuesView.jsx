import React, { useState, useEffect } from 'react';
import { listQueues, getQueueDetails } from '../services/api';

const QueuesView = () => {
  const [queues, setQueues] = useState([]);
  const [selectedQueue, setSelectedQueue] = useState(null);
  const [queueDetails, setQueueDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadQueues();
    const interval = setInterval(loadQueues, 5000); // Refresh every 5s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedQueue) {
      loadQueueDetails(selectedQueue);
    }
  }, [selectedQueue]);

  const loadQueues = async () => {
    try {
      const data = await listQueues();
      setQueues(data);
      setError(null);
    } catch (err) {
      setError('Failed to load queues');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadQueueDetails = async (queueName) => {
    try {
      const data = await getQueueDetails(queueName);
      setQueueDetails(data);
    } catch (err) {
      console.error('Failed to load queue details:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">RQ Queue Status</h2>
        <button
          onClick={loadQueues}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Refresh
        </button>
      </div>

      {/* Queues Overview */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {queues.map((queue) => (
          <button
            key={queue.name}
            onClick={() => setSelectedQueue(queue.name)}
            className={`text-left bg-white rounded-lg shadow-sm border-2 p-6 hover:shadow-md transition-all ${
              selectedQueue === queue.name ? 'border-blue-500' : 'border-gray-200'
            }`}
          >
            <h3 className="text-lg font-semibold text-gray-900 mb-2">{queue.name}</h3>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Queued:</span>
                <span className="font-semibold text-yellow-600">{queue.queued_jobs}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Processing:</span>
                <span className="font-semibold text-blue-600">{queue.started_jobs}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Finished:</span>
                <span className="font-semibold text-green-600">{queue.finished_jobs}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Failed:</span>
                <span className="font-semibold text-red-600">{queue.failed_jobs}</span>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Queue Details */}
      {selectedQueue && queueDetails && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-xl font-bold text-gray-900 mb-4">
            {selectedQueue} - Detailed View
          </h3>

          {/* Statistics */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="text-center">
              <p className="text-2xl font-bold text-yellow-600">
                {queueDetails.statistics.queued}
              </p>
              <p className="text-sm text-gray-500">Queued</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-600">
                {queueDetails.statistics.started}
              </p>
              <p className="text-sm text-gray-500">Processing</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-green-600">
                {queueDetails.statistics.finished}
              </p>
              <p className="text-sm text-gray-500">Finished</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-red-600">
                {queueDetails.statistics.failed}
              </p>
              <p className="text-sm text-gray-500">Failed</p>
            </div>
          </div>

          {/* Job Lists */}
          <div className="space-y-4">
            {queueDetails.started_jobs && queueDetails.started_jobs.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">
                  Currently Processing
                </h4>
                <div className="space-y-2">
                  {queueDetails.started_jobs.map((job) => (
                    job && (
                      <div
                        key={job.job_id}
                        className="bg-blue-50 border border-blue-200 rounded p-3 text-sm"
                      >
                        <div className="font-mono text-xs text-gray-600">{job.job_id}</div>
                        <div className="text-gray-700 mt-1">{job.func_name}</div>
                        {job.started_at && (
                          <div className="text-xs text-gray-500 mt-1">
                            Started: {new Date(job.started_at).toLocaleString()}
                          </div>
                        )}
                      </div>
                    )
                  ))}
                </div>
              </div>
            )}

            {queueDetails.failed_jobs && queueDetails.failed_jobs.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Recent Failures</h4>
                <div className="space-y-2">
                  {queueDetails.failed_jobs.slice(0, 5).map((job) => (
                    job && (
                      <div
                        key={job.job_id}
                        className="bg-red-50 border border-red-200 rounded p-3 text-sm"
                      >
                        <div className="font-mono text-xs text-gray-600">{job.job_id}</div>
                        <div className="text-gray-700 mt-1">{job.func_name}</div>
                      </div>
                    )
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default QueuesView;
