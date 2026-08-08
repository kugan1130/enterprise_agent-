import { DocumentRecord, SSEPayload, UploadResponse } from "../types";
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
  onStatus: (message: string) => void;
  onRoute: (route: string) => void;
  onToken: (chunk: string) => void;
  onComplete: (fullResponse: string) => void;
  onError: (errorMsg: string) => void;
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

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunkStr = decoder.decode(value, { stream: true });
      const lines = chunkStr.split("\n");

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith("data: ")) {
          try {
            const payload = JSON.parse(trimmed.substring(6)) as SSEPayload;

            if (payload.event === "status" && payload.message) {
              handlers.onStatus(payload.message);
            } else if (payload.event === "route_selected" && payload.route) {
              handlers.onRoute(payload.route);
            } else if (payload.event === "token" && payload.chunk) {
              accumulatedResponse += payload.chunk;
              handlers.onToken(payload.chunk);
            } else if (payload.event === "completed") {
              const finalResp = payload.response || accumulatedResponse;
              handlers.onComplete(finalResp);
            } else if (payload.event === "error" && payload.error) {
              handlers.onError(payload.error);
            }
          } catch {
            // Ignore partial SSE JSON parse chunks
          }
        }
      }
    }
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : "Network communication error.";
    handlers.onError(errorMsg);
  }
};
