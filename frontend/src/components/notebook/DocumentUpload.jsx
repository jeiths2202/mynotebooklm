import React, { useState, useRef } from 'react';
import { Upload, FileUp, X, CheckCircle, AlertCircle } from 'lucide-react';

const ALLOWED_TYPES = ['.pdf', '.txt', '.docx'];
const MAX_SIZE = 50 * 1024 * 1024; // 50MB

export function DocumentUpload({ onUpload, disabled }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null); // 'success' | 'error'
  const [errorMessage, setErrorMessage] = useState('');
  const fileInputRef = useRef(null);

  const validateFile = (file) => {
    const extension = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED_TYPES.includes(extension)) {
      return `Invalid file type. Allowed: ${ALLOWED_TYPES.join(', ')}`;
    }
    if (file.size > MAX_SIZE) {
      return 'File too large. Maximum size: 50MB';
    }
    return null;
  };

  const handleUpload = async (file) => {
    const error = validateFile(file);
    if (error) {
      setErrorMessage(error);
      setUploadStatus('error');
      setTimeout(() => setUploadStatus(null), 3000);
      return;
    }

    try {
      setUploadProgress(0);
      setUploadStatus(null);
      setErrorMessage('');

      await onUpload(file, (progress) => {
        setUploadProgress(progress);
      });

      setUploadStatus('success');
      setTimeout(() => {
        setUploadStatus(null);
        setUploadProgress(null);
      }, 2000);
    } catch (err) {
      setUploadStatus('error');
      setErrorMessage(err.response?.data?.detail || 'Upload failed');
      setTimeout(() => setUploadStatus(null), 3000);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    if (!disabled) setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);

    if (disabled) return;

    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) handleUpload(file);
    e.target.value = '';
  };

  return (
    <div className="mb-6">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
        className={`
          relative border-2 border-dashed rounded-xl p-6 text-center cursor-pointer
          transition-all duration-200
          ${isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'}
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={ALLOWED_TYPES.join(',')}
          onChange={handleFileSelect}
          className="hidden"
          disabled={disabled}
        />

        {uploadProgress !== null && uploadProgress < 100 ? (
          <div className="space-y-2">
            <FileUp className="w-8 h-8 mx-auto text-blue-500 animate-bounce" />
            <p className="text-sm text-gray-600">Uploading... {uploadProgress}%</p>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        ) : uploadStatus === 'success' ? (
          <div className="space-y-2">
            <CheckCircle className="w-8 h-8 mx-auto text-green-500" />
            <p className="text-sm text-green-600">Upload successful!</p>
          </div>
        ) : uploadStatus === 'error' ? (
          <div className="space-y-2">
            <AlertCircle className="w-8 h-8 mx-auto text-red-500" />
            <p className="text-sm text-red-600">{errorMessage}</p>
          </div>
        ) : (
          <div className="space-y-2">
            <Upload className="w-8 h-8 mx-auto text-gray-400" />
            <p className="text-sm text-gray-600">
              <span className="text-blue-500 font-medium">Click to upload</span> or drag and drop
            </p>
            <p className="text-xs text-gray-400">PDF, TXT, DOCX up to 50MB</p>
          </div>
        )}
      </div>
    </div>
  );
}
