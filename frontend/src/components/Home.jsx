import React, { useState } from 'react';
import WorkflowUpload from './WorkflowUpload';
import JobsList from './JobsList';
import AgentsView from './AgentsView';
import QueuesView from './QueuesView';

const Home = () => {
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [activeTab, setActiveTab] = useState('jobs');

  const handleUploadSuccess = (result) => {
    // Trigger jobs list refresh and switch to jobs tab
    setRefreshTrigger((prev) => prev + 1);
    setActiveTab('jobs');
  };

  const tabs = [
    { id: 'jobs', label: 'CV Jobs', icon: '📄' },
    { id: 'agents', label: 'Agents', icon: '🤖' },
    { id: 'queues', label: 'Queues', icon: '📊' },
    { id: 'dashboard', label: 'RQ Dashboard', icon: '📈' },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-xl">C</span>
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">CAVIA</h1>
                <p className="text-sm text-gray-600">
                  CV Assessment via Intelligent Agents
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs Navigation */}
        <div className="max-w-7xl mx-auto px-6">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <span className="mr-2">{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {activeTab === 'jobs' && (
          <div className="grid lg:grid-cols-3 gap-8">
            {/* Left Column - Upload */}
            <div className="lg:col-span-1">
              <WorkflowUpload onUploadSuccess={handleUploadSuccess} />
            </div>

            {/* Right Column - Jobs List */}
            <div className="lg:col-span-2">
              <JobsList refreshTrigger={refreshTrigger} />
            </div>
          </div>
        )}

        {activeTab === 'agents' && <AgentsView />}

        {activeTab === 'queues' && <QueuesView />}

        {activeTab === 'dashboard' && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="p-4 bg-gray-50 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">RQ Dashboard</h2>
              <p className="text-sm text-gray-600">Real-time queue monitoring</p>
            </div>
            <iframe
              src="/rq-dashboard/"
              className="w-full h-[800px] border-0"
              title="RQ Dashboard"
            />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <p className="text-center text-sm text-gray-600">
            CAVIA - Automated CV evaluation system using Agent-Oriented Architecture
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Home;
