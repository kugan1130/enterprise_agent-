import React, { useEffect, useRef } from "react";
import { ChatMessage } from "../../types";
import { MessageBubble } from "./MessageBubble";

interface ChatCanvasProps {
  messages: ChatMessage[];
  onSelectPrompt: (promptText: string) => void;
}

export const ChatCanvas: React.FC<ChatCanvasProps> = ({ messages, onSelectPrompt }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div ref={containerRef} className="chat-messages">
      {messages.length === 0 ? (
        <div className="welcome-card">
          <div className="welcome-icon">
            <i className="fa-solid fa-robot"></i>
          </div>
          <h2>Welcome to Enterprise AI Assistant</h2>
          <p>
            Ask company policy questions, search the web, query SQL sales databases, or upload PDFs for auto-ingested RAG analysis.
          </p>
          <div className="quick-prompts">
            <button onClick={() => onSelectPrompt("What is our company remote work policy?")}>
              Company Policy
            </button>
            <button onClick={() => onSelectPrompt("What is total sales revenue by region?")}>
              SQL Revenue
            </button>
            <button onClick={() => onSelectPrompt("Analyze Q1 sales and compare with recent AI developments.")}>
              Research Report
            </button>
          </div>
        </div>
      ) : (
        messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)
      )}
    </div>
  );
};
