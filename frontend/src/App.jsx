import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Home from './components/Home';
import JobDetailPage from './components/JobDetailPage';
import JobResults from './components/JobResults';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/jobs/:jobId" element={<JobDetailPage />} />
      <Route path="/jobs/:jobId/results" element={<JobResults />} />
    </Routes>
  );
}

export default App;
