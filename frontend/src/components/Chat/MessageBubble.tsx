import React from "react";
import { marked } from "marked";
import { ChatMessage } from "../../types";

interface MessageBubbleProps {
  message: ChatMessage;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === "user";
  const downloadUrl = message.download_url || message.artifact?.download_url;

  const renderContent = () => {
    if (message.error) {
      return (
        <span style={{ color: "#f43f5e" }}>
          <i className="fa-solid fa-triangle-exclamation"></i> Notice: {message.error}
        </span>
      );
    }

    const htmlContent = marked.parse(message.content) as string;
    return <div dangerouslySetInnerHTML={{ __html: htmlContent }} />;
  };

  return (
    <div className={`message-row ${isUser ? "user-row" : "assistant-row"}`}>
      <div className="avatar">
        <i className={isUser ? "fa-solid fa-user" : "fa-solid fa-bot"}></i>
      </div>
      <div className="bubble">
        {!isUser && message.route && (
          <div className="route-badge">ROUTE: {message.route.toUpperCase()}</div>
        )}
        {renderContent()}

        {!isUser && downloadUrl && (
          <div className="artifact-download-banner" style={{ marginTop: "12px" }}>
            <a
              href={downloadUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="download-btn"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 16px",
                backgroundColor: "#2563eb",
                color: "#ffffff",
                borderRadius: "6px",
                textDecoration: "none",
                fontWeight: 600,
                fontSize: "14px",
              }}
            >
              <i className="fa-solid fa-file-pdf"></i> Download PDF Report
            </a>
          </div>
        )}
      </div>
    </div>
  );
};
