export type UserRole = "user" | "admin";

export interface User {
  id?: number;
  username: string;
  email: string;
  role: UserRole;
  created_at?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ArtifactRecord {
  artifact_id: string;
  artifact_type: string;
  title: string;
  content: string;
  artifact_format?: string;
  download_url?: string;
  file_path?: string;
  source_documents?: string[];
  created_at?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  route?: string;
  artifact?: ArtifactRecord;
  download_url?: string;
  isStreaming?: boolean;
  error?: string;
}

export type ChatEventType = "activity" | "route" | "token" | "final" | "artifact" | "error";

export interface ChatStreamEvent {
  request_id?: string;
  type: ChatEventType;
  event?: string;
  message?: string;
  route?: string;
  chunk?: string;
  content?: string;
  response?: string;
  artifact?: ArtifactRecord;
  error?: string;
}

export interface DocumentRecord {
  document_id: string;
  filename: string;
  file_size: number;
  uploaded_by: string;
  upload_timestamp?: string;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  chunks_ingested: number;
  status: string;
  message: string;
}

export interface SQLChartDataset {
  label: string;
  data: number[];
  backgroundColor?: string | string[];
  borderColor?: string | string[];
}

export interface SQLChartData {
  type: "bar" | "line" | "pie";
  labels: string[];
  datasets: SQLChartDataset[];
}

export interface APIErrorResponse {
  error?: {
    code?: string;
    message?: string;
  };
  detail?: string;
}
