import { ArtifactRecord, ChatStreamEvent, DocumentRecord, UploadResponse } from "../types";
import { getApiBaseUrl, getStoredToken } from "./authService";

export const uploadPDF = async (file: File): Promise<UploadResponse> => {
  if (!file || file.type !== "application/pdf") {
    throw new Error("Only PDF documents (.pdf) are allowed.");
  }

  const baseUrl = getApiBaseUrl();
  const token = getStoredToken();
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${baseUrl}/api/documents/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });

  const data = await res.json();
  if (!res.ok) {
    const msg = data.error?.message || data.detail || "Document ingestion failed.";
    throw new Error(msg);
  }

  return data as UploadResponse;
};

export const fetchDocuments = async (): Promise<DocumentRecord[]> => {
  const baseUrl = getApiBaseUrl();
  const token = getStoredToken();
  if (!token) return [];

  const res = await fetch(`${baseUrl}/api/documents`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) return [];
  const data = await res.json();
  return data as DocumentRecord[];
};

export interface StreamChatHandlers {
  onActivity: (message: string, requestId?: string) => void;
  onRoute: (route: string, requestId?: string) => void;
  onToken: (chunk: string, requestId?: string) => void;
  onArtifact: (artifact: ArtifactRecord, requestId?: string) => void;
  onComplete: (fullResponse: string, requestId?: string) => void;
  onError: (errorMsg: string, requestId?: string) => void;
}

export const streamChat = async (
  message: string,
  sessionId: string,
  handlers: StreamChatHandlers
): Promise<void> => {
  const baseUrl = getApiBaseUrl();
  const token = getStoredToken();

  try {
    const response = await fetch(`${baseUrl}/api/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ message, session_id: sessionId }),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({ detail: "Request failed." }));
      const msg = errData.error?.message || errData.detail || `Server error (${response.status})`;
      handlers.onError(msg);
      return;
    }

    if (!response.body) {
      handlers.onError("No response stream received.");
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let accumulatedResponse = "";
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || ""; // Retain incomplete trailing line fragment in buffer

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith("data: ")) {
          try {
            const rawPayload = JSON.parse(trimmed.substring(6));
            const event: ChatStreamEvent = rawPayload;
            const reqId = event.request_id;
            const eventType = event.type || event.event;

            if (eventType === "activity" || eventType === "status") {
              const activityMsg = event.message || "Processing request...";
              handlers.onActivity(activityMsg, reqId);
            } else if (eventType === "route" || eventType === "route_selected") {
              const routeName = event.route || "direct";
              handlers.onRoute(routeName, reqId);
            } else if (eventType === "token") {
              const tokenChunk = event.chunk || event.content || "";
              if (tokenChunk) {
                accumulatedResponse += tokenChunk;
                handlers.onToken(tokenChunk, reqId);
              }
            } else if (eventType === "artifact" && event.artifact) {
              handlers.onArtifact(event.artifact, reqId);
            } else if (eventType === "final" || eventType === "completed") {
              const finalContent = event.content || event.response || accumulatedResponse;
              if (finalContent) {
                accumulatedResponse = finalContent;
              }
              handlers.onComplete(accumulatedResponse, reqId);
            } else if (eventType === "error") {
              const errorMsg = event.error || event.message || "An error occurred.";
              handlers.onError(errorMsg, reqId);
            }
          } catch {
            // Ignore incomplete line fragment JSON parsing
          }
        }
      }
    }

    if (buffer.trim().startsWith("data: ")) {
      try {
        const event: ChatStreamEvent = JSON.parse(buffer.trim().substring(6));
        if ((event.type === "final" || event.event === "completed") && (event.content || event.response)) {
          accumulatedResponse = event.content || event.response || accumulatedResponse;
        }
      } catch {
        // Safe end of stream
      }
    }

    handlers.onComplete(accumulatedResponse);
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : "Network communication error.";
    handlers.onError(errorMsg);
  }
};
