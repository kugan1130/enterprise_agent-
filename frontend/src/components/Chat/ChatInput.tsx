import React, { useState, KeyboardEvent, FormEvent } from "react";

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSendMessage, disabled }) => {
  const [text, setText] = useState("");

  const handleSubmit = (e?: FormEvent) => {
    if (e) e.preventDefault();
    if (!text.trim() || disabled) return;
    onSendMessage(text.trim());
    setText("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="chat-input-container">
      <form className="input-form" onSubmit={handleSubmit}>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message or question..."
          rows={1}
          disabled={disabled}
        />
        <button type="submit" className="send-btn" disabled={disabled || !text.trim()}>
          <i className="fa-solid fa-paper-plane"></i>
        </button>
      </form>
      <div className="input-footer">
        <span>Protected by Enterprise Guardrails & SQL Read-Only Validation</span>
      </div>
    </div>
  );
};
