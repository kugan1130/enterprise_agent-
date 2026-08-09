import { useState, useEffect } from "react";
import { ArtifactRecord, ChatMessage, DocumentRecord, User } from "./types";
import { getStoredUser, authService } from "./services/authService";
import { fetchDocuments, streamChat } from "./services/api";
import { AuthModal } from "./components/Auth/AuthModal";
import { Sidebar } from "./components/Sidebar/Sidebar";
import { ChatCanvas } from "./components/Chat/ChatCanvas";
import { ChatInput } from "./components/Chat/ChatInput";
import { ActivityPanel } from "./components/Chat/ActivityPanel";

export const App = () => {
  const [user, setUser] = useState<User | null>(getStoredUser());
  const [sessionId, setSessionId] = useState<string>(
    () => "session_" + Math.floor(Math.random() * 1000000)
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [activitySteps, setActivitySteps] = useState<string[]>([]);
  const [isSending, setIsSending] = useState(false);

  const loadDocs = async () => {
    if (user) {
      const docs = await fetchDocuments();
      setDocuments(docs);
    }
  };

  useEffect(() => {
    if (user) {
      loadDocs();
    }
  }, [user]);

  const handleAuthSuccess = (authenticatedUser: User) => {
    setUser(authenticatedUser);
  };

  const handleLogout = () => {
    authService.logout();
    setUser(null);
    setMessages([]);
    setDocuments([]);
  };

  const handleNewSession = () => {
    const newId = "session_" + Math.floor(Math.random() * 1000000);
    setSessionId(newId);
    setMessages([]);
    setActivitySteps([]);
  };

  const handleSendMessage = async (text: string) => {
    if (!text.trim() || isSending) return;

    const userMsgId = "msg_" + Date.now();
    const assistantMsgId = "asst_" + (Date.now() + 1);

    const newUserMsg: ChatMessage = {
      id: userMsgId,
      role: "user",
      content: text.trim(),
    };

    // Append ONLY user message to chat canvas. Internal activity status NEVER enters chat messages.
    setMessages((prev) => [...prev, newUserMsg]);
    setIsSending(true);
    setActivitySteps(["Evaluating request guardrails..."]);

    let assistantMsgCreated = false;
    let currentRoute = "direct";
    let activeArtifact: ArtifactRecord | undefined = undefined;

    await streamChat(text, sessionId, {
      onActivity: (activityMsg) => {
        // Activity events update ActivityPanel ONLY
        setActivitySteps((prev) => [...prev, activityMsg]);
      },
      onRoute: (route) => {
        currentRoute = route;
        setActivitySteps((prev) => [...prev, `Routed to '${route.toUpperCase()}' Agent`]);
      },
      onArtifact: (artifact) => {
        activeArtifact = artifact;
        if (artifact.download_url) {
          setActivitySteps((prev) => [...prev, `Generated PDF Artifact: ${artifact.title}`]);
        }
      },
      onToken: (chunk) => {
        // Token events create/update assistant message ONLY when actual response text arrives
        setMessages((prev) => {
          if (!assistantMsgCreated) {
            assistantMsgCreated = true;
            const newAsstMsg: ChatMessage = {
              id: assistantMsgId,
              role: "assistant",
              content: chunk,
              route: currentRoute,
              artifact: activeArtifact,
              download_url: activeArtifact?.download_url,
              isStreaming: true,
            };
            return [...prev, newAsstMsg];
          }

          return prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content: m.content + chunk,
                  artifact: activeArtifact || m.artifact,
                  download_url: activeArtifact?.download_url || m.download_url,
                }
              : m
          );
        });
      },
      onComplete: (fullResponse) => {
        setActivitySteps((prev) => [...prev, "Execution completed."]);
        setMessages((prev) => {
          const finalContent = fullResponse || "Completed.";
          if (!assistantMsgCreated) {
            assistantMsgCreated = true;
            const newAsstMsg: ChatMessage = {
              id: assistantMsgId,
              role: "assistant",
              content: finalContent,
              route: currentRoute,
              artifact: activeArtifact,
              download_url: activeArtifact?.download_url,
              isStreaming: false,
            };
            return [...prev, newAsstMsg];
          }

          return prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content: finalContent,
                  artifact: activeArtifact || m.artifact,
                  download_url: activeArtifact?.download_url || m.download_url,
                  isStreaming: false,
                }
              : m
          );
        });
        setIsSending(false);
      },
      onError: (errorMsg) => {
        setActivitySteps((prev) => [...prev, `Execution Notice: ${errorMsg}`]);
        setMessages((prev) => {
          if (!assistantMsgCreated) {
            const errAsstMsg: ChatMessage = {
              id: assistantMsgId,
              role: "assistant",
              content: `Service Notice: ${errorMsg}`,
              error: errorMsg,
              isStreaming: false,
            };
            return [...prev, errAsstMsg];
          }
          return prev.map((m) =>
            m.id === assistantMsgId
              ? { ...m, error: errorMsg, isStreaming: false }
              : m
          );
        });
        setIsSending(false);
      },
    });
  };

  if (!user) {
    return <AuthModal onAuthSuccess={handleAuthSuccess} />;
  }

  return (
    <div className="app-layout">
      <Sidebar
        user={user}
        documents={documents}
        onNewSession={handleNewSession}
        onDocumentUploaded={loadDocs}
        onLogout={handleLogout}
      />

      <main className="chat-viewport">
        <header className="chat-header">
          <div className="header-status">
            <span className="status-indicator online"></span>
            <span>
              Session: <strong>{sessionId}</strong>
            </span>
          </div>
          <div className="header-badges">
            <span className="badge">Groq Llama 3.3 70B</span>
            <span className="badge">ChromaDB RAG</span>
            <span className="badge">PostgreSQL SQL</span>
          </div>
        </header>

        <ActivityPanel
          steps={activitySteps}
          onClose={() => setActivitySteps([])}
        />

        <ChatCanvas
          messages={messages}
          onSelectPrompt={(promptText) => handleSendMessage(promptText)}
        />

        <ChatInput
          onSendMessage={handleSendMessage}
          disabled={isSending}
        />
      </main>
    </div>
  );
};

export default App;
