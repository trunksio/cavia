import React, { useState } from 'react';
import CVUpload from './CVUpload';
import JobsList from './JobsList';

const Home = () => {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleUploadSuccess = (result) => {
    // Trigger jobs list refresh
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
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
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Left Column - Upload */}
          <div className="lg:col-span-1">
            <CVUpload onUploadSuccess={handleUploadSuccess} />
          </div>

          {/* Right Column - Jobs List */}
          <div className="lg:col-span-2">
            <JobsList refreshTrigger={refreshTrigger} />
          </div>
        </div>
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
