import React from "react";
import { marked } from "marked";
import { ChatMessage } from "../../types";

interface MessageBubbleProps {
  message: ChatMessage;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === "user";

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
      </div>
    </div>
  );
};
