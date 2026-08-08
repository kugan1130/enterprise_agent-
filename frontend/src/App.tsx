import { useState, useEffect } from "react";
import { ChatMessage, DocumentRecord, User } from "./types";
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
    const assistantMsgId = "msg_" + (Date.now() + 1);

    const newUserMsg: ChatMessage = {
      id: userMsgId,
      role: "user",
      content: text,
    };

    const newAssistantMsg: ChatMessage = {
      id: assistantMsgId,
      role: "assistant",
      content: "Assistant is thinking...",
      isStreaming: true,
    };

    setMessages((prev) => [...prev, newUserMsg, newAssistantMsg]);
    setIsSending(true);
    setActivitySteps(["Evaluating guardrails & routing..."]);

    await streamChat(text, sessionId, {
      onStatus: (statusMsg) => {
        setActivitySteps((prev) => [...prev, statusMsg]);
      },
      onRoute: (route) => {
        setActivitySteps((prev) => [...prev, `Routed to '${route.toUpperCase()}' Agent`]);
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantMsgId ? { ...m, route } : m))
        );
      },
      onToken: (chunk) => {
        setMessages((prev) =>
          prev.map((m) => {
            if (m.id === assistantMsgId) {
              const currentContent = m.isStreaming ? chunk : m.content + chunk;
              return { ...m, content: currentContent, isStreaming: false };
            }
            return m;
          })
        );
      },
      onComplete: (fullResponse) => {
        setActivitySteps((prev) => [...prev, "Execution completed."]);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? { ...m, content: fullResponse || m.content, isStreaming: false }
              : m
          )
        );
        setIsSending(false);
      },
      onError: (errorMsg) => {
        setActivitySteps((prev) => [...prev, `Execution Notice: ${errorMsg}`]);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? { ...m, error: errorMsg, isStreaming: false }
              : m
          )
        );
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
