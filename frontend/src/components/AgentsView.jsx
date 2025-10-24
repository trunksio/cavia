import React, { useState, useEffect } from 'react';
import { listAgents } from '../services/api';

const AgentsView = () => {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadAgents();
    const interval = setInterval(loadAgents, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const loadAgents = async () => {
    try {
      const data = await listAgents();
      setAgents(data);
      setError(null);
    } catch (err) {
      setError('Failed to load agents');
      console.error(err);
    } finally {
      setLoading(false);
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
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Registered Agents</h2>
        <button
          onClick={loadAgents}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Refresh
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {agents.map((agent) => (
          <div
            key={agent.agent_id}
            className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{agent.name}</h3>
                <p className="text-sm text-gray-500">{agent.agent_id}</p>
              </div>
              <span
                className={`px-2 py-1 text-xs font-medium rounded-full ${
                  agent.status === 'active'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                {agent.status}
              </span>
            </div>

            <p className="text-sm text-gray-600 mb-4">{agent.description}</p>

            <div className="space-y-2">
              <div className="flex items-center text-sm">
                <span className="text-gray-500 font-medium mr-2">Type:</span>
                <span className="text-gray-900">{agent.agent_type}</span>
              </div>
              <div className="flex items-center text-sm">
                <span className="text-gray-500 font-medium mr-2">Queue:</span>
                <span className="text-gray-900 font-mono text-xs">{agent.queue_name}</span>
              </div>
            </div>

            {agent.capabilities && (
              <div className="mt-4 pt-4 border-t border-gray-100">
                <p className="text-xs font-medium text-gray-500 mb-2">Capabilities</p>
                <div className="space-y-1">
                  {Object.entries(agent.capabilities).map(([key, value]) => (
                    <div key={key} className="text-xs">
                      <span className="text-gray-500">{key}:</span>{' '}
                      <span className="text-gray-700">
                        {Array.isArray(value) ? value.join(', ') : String(value)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {agents.length === 0 && (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <p className="text-gray-500">No agents registered</p>
        </div>
      )}
    </div>
  );
};

export default AgentsView;
