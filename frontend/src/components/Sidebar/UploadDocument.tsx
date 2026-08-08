import React, { useState, useRef, DragEvent, ChangeEvent } from "react";
import { uploadPDF } from "../../services/api";

interface UploadDocumentProps {
  onDocumentUploaded: () => void;
}

export const UploadDocument: React.FC<UploadDocumentProps> = ({ onDocumentUploaded }) => {
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    if (!file || file.type !== "application/pdf") {
      alert("Only PDF documents (.pdf) are allowed.");
      return;
    }

    setIsUploading(true);
    setUploadStatus(`Uploading ${file.name}...`);

    try {
      setUploadStatus(`Indexing & extracting document chunks...`);
      const response = await uploadPDF(file);
      setUploadStatus(response.message || `${file.name} is ready! You can now ask questions about it.`);
      onDocumentUploaded();
      setTimeout(() => {
        setUploadStatus(null);
        setIsUploading(false);
      }, 4000);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Document upload failed.";
      setUploadStatus(`Upload Notice: ${msg}`);
      setTimeout(() => {
        setUploadStatus(null);
        setIsUploading(false);
      }, 5000);
    }
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  return (
    <div className="upload-container">
      <div
        className="upload-dropzone"
        onClick={() => fileInputRef.current?.click()}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <i className="fa-solid fa-cloud-arrow-up upload-icon"></i>
        <p>
          Drop PDF or <span>Browse</span>
        </p>
        <small>Auto-indexed into Vector DB</small>
        <input
          type="file"
          ref={fileInputRef}
          accept="application/pdf"
          className="hidden"
          onChange={handleFileChange}
        />
      </div>

      {uploadStatus && (
        <div className="upload-status-banner">
          {isUploading && <div className="spinner-small"></div>}
          <span>{uploadStatus}</span>
        </div>
      )}
    </div>
  );
};
