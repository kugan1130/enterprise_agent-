import React from "react";

interface ActivityPanelProps {
  steps: string[];
  onClose: () => void;
}

export const ActivityPanel: React.FC<ActivityPanelProps> = ({ steps, onClose }) => {
  if (steps.length === 0) return null;

  return (
    <div className="activity-panel">
      <div className="activity-header">
        <span>
          <i className="fa-solid fa-network-wired"></i> Agent Execution Pipeline
        </span>
        <button className="close-panel-btn" onClick={onClose}>
          &times;
        </button>
      </div>
      <div className="activity-steps">
        {steps.map((step, idx) => (
          <div key={idx} className="step-chip active">
            <i className="fa-solid fa-check"></i> {step}
          </div>
        ))}
      </div>
    </div>
  );
};
