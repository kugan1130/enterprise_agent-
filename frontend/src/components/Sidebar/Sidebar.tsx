import React from "react";
import { DocumentRecord, User } from "../../types";
import { UploadDocument } from "./UploadDocument";

interface SidebarProps {
  user: User;
  documents: DocumentRecord[];
  onNewSession: () => void;
  onDocumentUploaded: () => void;
  onLogout: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  user,
  documents,
  onNewSession,
  onDocumentUploaded,
  onLogout,
}) => {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-logo">
          <i className="fa-solid fa-brain"></i>
        </div>
        <div className="brand-info">
          <h3>Nexa AI</h3>
          <span>Enterprise Assistant</span>
        </div>
      </div>

      <div className="user-profile-badge">
        <div className="user-avatar">
          <i className="fa-solid fa-user-shield"></i>
        </div>
        <div className="user-details">
          <span className="user-name">{user.username}</span>
          <span className="user-role">{user.role.toUpperCase()}</span>
        </div>
      </div>

      <button className="new-chat-btn" onClick={onNewSession}>
        <i className="fa-solid fa-plus"></i> New Conversation
      </button>

      <div className="sidebar-section">
        <div className="section-title">
          <i className="fa-solid fa-file-pdf"></i> Document Ingestion
        </div>

        <UploadDocument onDocumentUploaded={onDocumentUploaded} />

        <div className="doc-list-header">Indexed Documents ({documents.length})</div>
        <div className="doc-list">
          {documents.map((doc) => (
            <div key={doc.document_id} className="doc-item">
              <i className="fa-solid fa-file-pdf" style={{ color: "#ef4444" }}></i>
              <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis" }}>
                {doc.filename}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="sidebar-footer">
        <button className="logout-btn" onClick={onLogout}>
          <i className="fa-solid fa-right-from-bracket"></i> Sign Out
        </button>
      </div>
    </aside>
  );
};
