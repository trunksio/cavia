import React from 'react';
import { useParams } from 'react-router-dom';
import JobStatusCard from './JobStatusCard';

const JobDetailPage = () => {
  const { jobId } = useParams();

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
              <p className="text-sm text-gray-600">Job Status</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-6 py-8">
        <JobStatusCard jobId={jobId} autoRefresh={true} />
      </main>
    </div>
  );
};

export default JobDetailPage;
