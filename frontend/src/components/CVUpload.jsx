import React, { useState, useRef } from 'react';
import { Upload, FileText, X, CheckCircle, AlertCircle } from 'lucide-react';
import { uploadCV } from '../services/api';

const CVUpload = ({ onUploadSuccess }) => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = (file) => {
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
    setSuccess(null);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setError(null);
    setSuccess(null);
    setUploadProgress(0);

    try {
      const result = await uploadCV(selectedFile, (progress) => {
        setUploadProgress(progress);
      });

      setSuccess(`CV uploaded successfully! Job ID: ${result.job_id}`);
      setSelectedFile(null);
      setUploadProgress(0);

      // Notify parent component
      if (onUploadSuccess) {
        onUploadSuccess(result);
      }

      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to upload CV. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleRemove = () => {
    setSelectedFile(null);
    setError(null);
    setSuccess(null);
    setUploadProgress(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="card">
      <h2 className="text-2xl font-bold mb-4 text-gray-800">Upload CV</h2>

      {/* Drag and Drop Zone */}
      <div
        className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-all ${
          dragActive
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-300 hover:border-primary-400'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".pdf,.doc,.docx"
          onChange={handleChange}
          disabled={uploading}
        />

        {!selectedFile ? (
          <div className="space-y-4">
            <Upload className="mx-auto h-12 w-12 text-gray-400" />
            <div>
              <p className="text-lg text-gray-600">
                Drag and drop your CV here, or{' '}
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="text-primary-600 hover:text-primary-700 font-medium"
                  disabled={uploading}
                >
                  browse
                </button>
              </p>
              <p className="text-sm text-gray-500 mt-2">
                Supports PDF and DOCX files (max 10MB)
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <FileText className="mx-auto h-12 w-12 text-primary-600" />
            <div className="flex items-center justify-center space-x-2">
              <span className="text-gray-700 font-medium">{selectedFile.name}</span>
              {!uploading && (
                <button
                  onClick={handleRemove}
                  className="text-danger-600 hover:text-danger-700"
                >
                  <X className="h-5 w-5" />
                </button>
              )}
            </div>
            <p className="text-sm text-gray-500">
              {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
        )}
      </div>

      {/* Upload Progress */}
      {uploading && (
        <div className="mt-4">
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
        <div className="mt-4 p-4 bg-danger-50 border border-danger-200 rounded-lg flex items-start space-x-3">
          <AlertCircle className="h-5 w-5 text-danger-600 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-danger-800">{error}</p>
        </div>
      )}

      {/* Success Message */}
      {success && (
        <div className="mt-4 p-4 bg-success-50 border border-success-200 rounded-lg flex items-start space-x-3">
          <CheckCircle className="h-5 w-5 text-success-600 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-success-800">{success}</p>
        </div>
      )}

      {/* Upload Button */}
      {selectedFile && !uploading && (
        <button
          onClick={handleUpload}
          className="btn btn-primary w-full mt-4"
          disabled={uploading}
        >
          Upload and Process CV
        </button>
      )}
    </div>
  );
};

export default CVUpload;
