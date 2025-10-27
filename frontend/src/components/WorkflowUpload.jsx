import React, { useState } from 'react';
import { Upload, ArrowLeft, CheckCircle, AlertCircle } from 'lucide-react';
import WorkflowSelector from './WorkflowSelector';
import IntentCapture from './IntentCapture';
import { uploadDocumentWithIntent } from '../services/api';

const WorkflowUpload = ({ onUploadSuccess }) => {
  const [step, setStep] = useState('select'); // 'select' | 'capture' | 'upload'
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [createdIntent, setCreatedIntent] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Step 1: Workflow Selection
  const handleWorkflowSelect = (workflow) => {
    setSelectedWorkflow(workflow);
    setStep('capture');
    setError(null);
  };

  // Step 2: Intent Creation
  const handleIntentCreated = (intent) => {
    setCreatedIntent(intent);
    setStep('upload');
    setError(null);
  };

  // Step 3: File Upload
  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword'];
    const allowedExtensions = ['.pdf', '.docx', '.doc'];
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();

    if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(fileExtension)) {
      setError('Invalid file type. Please upload a PDF or DOCX file.');
      return;
    }

    // Validate file size (max 10MB)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      setError('File too large. Maximum size is 10MB.');
      return;
    }

    setSelectedFile(file);
    setError(null);
  };

  const handleUpload = async () => {
    if (!selectedFile || !createdIntent) return;

    setUploading(true);
    setError(null);
    setSuccess(null);
    setUploadProgress(0);

    try {
      const result = await uploadDocumentWithIntent(
        selectedFile,
        createdIntent,
        (progress) => {
          setUploadProgress(progress);
        }
      );

      setSuccess(`Document uploaded successfully! Job ID: ${result.job_id}`);

      // Reset to step 1 after successful upload
      setTimeout(() => {
        setStep('select');
        setSelectedWorkflow(null);
        setCreatedIntent(null);
        setSelectedFile(null);
        setSuccess(null);
        setUploadProgress(0);

        // Notify parent component
        if (onUploadSuccess) {
          onUploadSuccess(result);
        }
      }, 2000);

    } catch (err) {
      console.error('Upload error:', err);
      setError(err.response?.data?.detail || 'Failed to upload document. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleBack = () => {
    if (step === 'capture') {
      setStep('select');
      setSelectedWorkflow(null);
    } else if (step === 'upload') {
      setStep('capture');
      setSelectedFile(null);
      setError(null);
    }
  };

  const handleStartOver = () => {
    setStep('select');
    setSelectedWorkflow(null);
    setCreatedIntent(null);
    setSelectedFile(null);
    setError(null);
    setSuccess(null);
    setUploadProgress(0);
  };

  // Render based on current step
  if (step === 'select') {
    return <WorkflowSelector onWorkflowSelect={handleWorkflowSelect} />;
  }

  if (step === 'capture') {
    return (
      <IntentCapture
        workflow={selectedWorkflow}
        onIntentCreated={handleIntentCreated}
        onBack={handleBack}
      />
    );
  }

  // Step 3: Upload
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Upload Document</h2>
          <p className="text-sm text-gray-600 mt-1">
            Workflow: <span className="font-medium">{selectedWorkflow?.name}</span>
          </p>
        </div>
        <button
          onClick={handleStartOver}
          className="text-sm text-gray-600 hover:text-gray-900"
        >
          Start Over
        </button>
      </div>

      {/* Intent Summary */}
      <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <h3 className="font-semibold text-blue-900 mb-1">Intent</h3>
        <p className="text-sm text-blue-800">{createdIntent?.goal}</p>
      </div>

      {/* File Upload */}
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Document
          </label>
          <input
            type="file"
            onChange={handleFileSelect}
            accept=".pdf,.doc,.docx"
            disabled={uploading}
            className="block w-full text-sm text-gray-500
              file:mr-4 file:py-2 file:px-4
              file:rounded-full file:border-0
              file:text-sm file:font-semibold
              file:bg-primary-50 file:text-primary-700
              hover:file:bg-primary-100
              disabled:opacity-50 disabled:cursor-not-allowed"
          />
          {selectedFile && (
            <p className="mt-2 text-sm text-gray-600">
              Selected: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
            </p>
          )}
        </div>

        {/* Upload Progress */}
        {uploading && (
          <div>
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm text-gray-600">Uploading...</span>
              <span className="text-sm font-medium text-gray-800">{uploadProgress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="p-4 bg-danger-50 border border-danger-200 rounded-lg flex items-start space-x-3">
            <AlertCircle className="h-5 w-5 text-danger-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-danger-800">{error}</p>
          </div>
        )}

        {/* Success Message */}
        {success && (
          <div className="p-4 bg-success-50 border border-success-200 rounded-lg flex items-start space-x-3">
            <CheckCircle className="h-5 w-5 text-success-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-success-800">{success}</p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex space-x-3">
          <button
            onClick={handleBack}
            disabled={uploading}
            className="btn btn-secondary flex-1 flex items-center justify-center"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Intent
          </button>
          <button
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            className="btn btn-primary flex-1 flex items-center justify-center"
          >
            <Upload className="h-4 w-4 mr-2" />
            {uploading ? 'Uploading...' : 'Upload with Intent'}
          </button>
        </div>
      </div>

      {/* Supported Formats */}
      <div className="mt-6 pt-6 border-t border-gray-200">
        <p className="text-xs text-gray-500 text-center">
          Supported formats: PDF, DOCX (max 10MB)
        </p>
      </div>
    </div>
  );
};

export default WorkflowUpload;
