import React, { useState, useEffect, useRef } from "react";

import {
  Bot,
  Send,
  Plus,
  Settings,
  Zap,
  Database,
  Clock,
  Activity,
  AlertCircle,
  User,
  Menu,
  X,
  Sparkles,
  Server
} from "lucide-react";

const API_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000";

function App() {
  const [sessionId, setSessionId] = useState(
    () => crypto.randomUUID()
  );

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [systemPrompt, setSystemPrompt] = useState("");
  const [failureMode, setFailureMode] = useState("");
  const [backendOnline, setBackendOnline] = useState(false);
  const [keyCount, setKeyCount] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const messagesEndRef = useRef(null);

  // Check backend health
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch(`${API_URL}/health`);
        const data = await response.json();

        setBackendOnline(
          response.ok && data.status === "ok"
        );

        setKeyCount(data.keys_configured || 0);
      } catch {
        setBackendOnline(false);
      }
    };

    checkHealth();

    const interval = setInterval(checkHealth, 15000);

    return () => clearInterval(interval);
  }, []);

  // Automatically scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth"
    });
  }, [messages, loading]);

  // Start a new session
  const newChat = () => {
    if (loading) return;

    setSessionId(crypto.randomUUID());
    setMessages([]);
    setInput("");
    setFailureMode("");
    setSystemPrompt("");
  };

  // Send message to FastAPI
  const sendMessage = async (customMessage) => {
    const message =
      typeof customMessage === "string"
        ? customMessage.trim()
        : input.trim();

    if (!message || loading) return;

    setMessages((previous) => [
      ...previous,
      {
        role: "user",
        content: message
      }
    ]);

    setInput("");
    setLoading(true);

    try {
      const headers = {
        "Content-Type": "application/json"
      };

      if (failureMode) {
        headers["X-Simulate-Failure"] = failureMode;
      }

      const body = {
        session_id: sessionId,
        message: message
      };

      if (systemPrompt.trim()) {
        body.system_prompt = systemPrompt.trim();
      }

      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: headers,
        body: JSON.stringify(body)
      });

      const data = await response.json();

      if (!response.ok) {
        const detail =
          typeof data.detail === "string"
            ? data.detail
            : "Invalid request. Please check your message.";

        throw new Error(detail);
      }

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: data.reply,
          metadata: data.metadata
        }
      ]);
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        {
          role: "error",
          content: error.message || "Something went wrong."
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Send message using Enter
  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  const suggestions = [
    "Explain artificial intelligence in simple words.",
    "What is response caching?",
    "Explain the difference between SQL and NoSQL.",
    "How does API key failover work?"
  ];

  const assistantMessages = messages.filter(
    (message) => message.role === "assistant"
  );

  const cacheHits = assistantMessages.filter(
    (message) =>
      message.metadata?.resolution_source === "LLM_CACHE"
  ).length;

  const liveRequests = assistantMessages.filter(
    (message) =>
      message.metadata?.resolution_source === "LIVE_INFERENCE"
  ).length;

  return (
    <div className="app-container">

      {/* Sidebar */}

      <aside
        className={`sidebar ${sidebarOpen ? "" : "sidebar-hidden"}`}
      >
        <div className="brand">
          <div className="brand-icon">
            <Sparkles size={25} />
          </div>

          <div>
            <h2>LYFTR AI</h2>
            <span>Intelligent Chatbot</span>
          </div>
        </div>

        <button
          className="new-chat-button"
          onClick={newChat}
          disabled={loading}
        >
          <Plus size={19} />
          New Conversation
        </button>

        <div className="sidebar-section">
          <h3>
            <Server size={16} />
            System Status
          </h3>

          <div className="status-row">
            <span>Backend</span>

            <span
              className={
                backendOnline ? "status-online" : "status-offline"
              }
            >
              <span className="status-dot"></span>
              {backendOnline ? "Online" : "Offline"}
            </span>
          </div>

          <div className="status-row">
            <span>API Keys</span>
            <strong>{keyCount} configured</strong>
          </div>

          <div className="status-row">
            <span>Storage</span>
            <strong>SQLite</strong>
          </div>
        </div>

        <div className="sidebar-section">
          <h3>
            <Activity size={16} />
            Session Analytics
          </h3>

          <div className="analytics-card">
            <div className="analytics-icon live-icon">
              <Zap size={19} />
            </div>

            <div>
              <span>Live Requests</span>
              <h2>{liveRequests}</h2>
            </div>
          </div>

          <div className="analytics-card">
            <div className="analytics-icon cache-icon">
              <Database size={19} />
            </div>

            <div>
              <span>Cache Hits</span>
              <h2>{cacheHits}</h2>
            </div>
          </div>
        </div>

        <div className="sidebar-section">
          <h3>
            <Settings size={16} />
            Configuration
          </h3>

          <label className="field-label">
            System Prompt
          </label>

          <textarea
            data-testid="system-prompt-input"
            className="system-prompt"
            placeholder="Customize the AI assistant..."
            value={systemPrompt}
            disabled={loading}
            onChange={(event) =>
              setSystemPrompt(event.target.value)
            }
          />

          <label className="field-label">
            Failure Simulation
          </label>

          <select
            className="failure-select"
            value={failureMode}
            disabled={loading}
            onChange={(event) =>
              setFailureMode(event.target.value)
            }
          >
            <option value="">
              Normal Operation
            </option>

            <option value="key_1=429">
              Key 1 — Rate Limit (429)
            </option>

            <option value="key_1=500">
              Key 1 — Server Error (500)
            </option>

            <option value="key_1=429,key_2=500">
              Key 1 & Key 2 Failure
            </option>

            <option value="*=429">
              All Keys Failure
            </option>
          </select>

          <p className="helper-text">
            Simulate provider failures to verify automatic
            API key failover.
          </p>
        </div>

        <div className="sidebar-footer">
          <p>Powered by LiteLLM</p>
          <span>React · FastAPI · SQLite</span>
        </div>
      </aside>

      {/* Main chat area */}

      <main className="main-content">

        <header className="chat-header">
          <div className="header-left">
            <button
              className="icon-button"
              aria-label="Toggle sidebar"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              {sidebarOpen ? (
                <X size={21} />
              ) : (
                <Menu size={21} />
              )}
            </button>

            <div>
              <h2>AI Workspace</h2>
              <p>Resilient AI conversation engine</p>
            </div>
          </div>

          <div className="header-status">
            <span
              className={`connection-dot ${
                backendOnline ? "connected" : "disconnected"
              }`}
            ></span>

            {backendOnline ? "Connected" : "Disconnected"}
          </div>
        </header>

        <section className="chat-messages">

          {/* Welcome screen */}

          {messages.length === 0 && (
            <div className="welcome-screen">

              <div className="welcome-icon">
                <Bot size={48} />
              </div>

              <span className="welcome-tag">
                <Sparkles size={14} />
                Intelligent AI Assistant
              </span>

              <h1>How can I help you today?</h1>

              <p>
                Experience intelligent conversations with
                automatic provider failover, response caching
                and persistent conversation memory.
              </p>

              <div className="feature-row">
                <span>
                  <Zap size={16} />
                  Automatic Failover
                </span>

                <span>
                  <Database size={16} />
                  Smart Caching
                </span>

                <span>
                  <Activity size={16} />
                  Token Tracking
                </span>
              </div>

              <div className="suggestion-grid">
                {suggestions.map((suggestion, index) => (
                  <button
                    key={index}
                    className="suggestion-card"
                    onClick={() => sendMessage(suggestion)}
                  >
                    <Sparkles size={18} />
                    <span>{suggestion}</span>
                  </button>
                ))}
              </div>

            </div>
          )}

          {/* Conversation messages */}

          {messages.map((message, index) => (
            <div
              key={index}
              className={`message-row ${message.role}`}
            >

              <div className={`avatar ${message.role}-avatar`}>
                {message.role === "user" ? (
                  <User size={19} />
                ) : message.role === "error" ? (
                  <AlertCircle size={19} />
                ) : (
                  <Bot size={21} />
                )}
              </div>

              <div
                className="message-body"
                data-testid={
                  message.role === "assistant"
                    ? "assistant-message"
                    : undefined
                }
              >

                <div className="message-author">
                  {message.role === "user"
                    ? "You"
                    : message.role === "error"
                    ? "Request Failed"
                    : "LYFTR AI"}
                </div>

                <div className="message-text">
                  {message.content}
                </div>

                {/* Required response metadata */}

                {message.metadata && (
                  <div className="metadata-panel">

                    <div className="metadata-heading">
                      <Activity size={14} />
                      Response Metadata
                    </div>

                    <div className="metadata-grid">

                      <div className="metadata-item">
                        <span>Resolution Source</span>

                        <strong
                          data-testid="meta-source"
                          className={
                            message.metadata.resolution_source ===
                            "LLM_CACHE"
                              ? "cache-badge"
                              : "live-badge"
                          }
                        >
                          {message.metadata.resolution_source}
                        </strong>
                      </div>

                      <div className="metadata-item">
                        <span>Model</span>

                        <strong data-testid="meta-model">
                          {message.metadata.model}
                        </strong>
                      </div>

                      <div className="metadata-item">
                        <span>
                          <Clock size={12} /> Latency
                        </span>

                        <strong data-testid="meta-latency">
                          {message.metadata.latency_ms} ms
                        </strong>
                      </div>

                      <div className="metadata-item">
                        <span>Input Tokens</span>

                        <strong data-testid="meta-input-tokens">
                          {message.metadata.input_tokens}
                        </strong>
                      </div>

                      <div className="metadata-item">
                        <span>Output Tokens</span>

                        <strong data-testid="meta-output-tokens">
                          {message.metadata.output_tokens}
                        </strong>
                      </div>

                      <div className="metadata-item">
                        <span>API Key</span>

                        <strong>
                          {message.metadata.key_id || "Cached"}
                        </strong>
                      </div>

                      <div className="metadata-item">
                        <span>Fallback Attempts</span>

                        <strong>
                          {message.metadata.fallback_attempts}
                        </strong>
                      </div>

                    </div>

                    {message.metadata.fallback_attempts > 0 && (
                      <div className="failover-notice">
                        <Zap size={15} />
                        Automatic failover completed successfully.
                      </div>
                    )}

                  </div>
                )}

              </div>
            </div>
          ))}

          {/* Loading animation */}

          {loading && (
            <div className="message-row assistant">

              <div className="avatar assistant-avatar">
                <Bot size={21} />
              </div>

              <div className="message-body">
                <div className="message-author">
                  LYFTR AI
                </div>

                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>

                <p className="loading-text">
                  Processing your request...
                </p>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />

        </section>

        {/* Message input */}

        <footer className="chat-footer">

          {failureMode && (
            <div className="simulation-warning">
              <AlertCircle size={16} />
              Failure simulation active: {failureMode}
            </div>
          )}

          <div className="input-container">

            <textarea
              data-testid="chat-input"
              placeholder="Ask me anything..."
              value={input}
              maxLength={4000}
              rows={1}
              disabled={loading}
              onChange={(event) =>
                setInput(event.target.value)
              }
              onKeyDown={handleKeyDown}
            />

            <button
              data-testid="send-button"
              className="send-button"
              aria-label="Send message"
              onClick={() => sendMessage()}
              disabled={!input.trim() || loading}
            >
              <Send size={20} />
            </button>

          </div>

          <div className="input-footer">
            <span>
              Enter to send · Shift + Enter for new line
            </span>

            <span>{input.length}/4000</span>
          </div>

          <p className="disclaimer">
            AI-generated responses may contain inaccuracies.
            Verify important information.
          </p>

        </footer>

      </main>

    </div>
  );
}

export default App;