// deep-research-frontend/src/App.jsx

import React, { useState, useRef, useEffect, useCallback } from 'react';
import './index.css';

const App = () => {
  const initialMessages = [
    { type: 'ai', content: "Hello! How can I assist you today? I'm an AI deep research agent.", timestamp: new Date().toLocaleTimeString() },
    { type: 'user', content: "Can you tell me about the future of AI in medicine?", timestamp: new Date().toLocaleTimeString() },
    { type: 'ai', content: "Working on it. Please note, I will provide real-time updates as I gather information from various sources.", timestamp: new Date().toLocaleTimeString() },
  ];

  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState(initialMessages);
  const [currentProgress, setCurrentProgress] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentProgress]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [query]);

  const handleQueryChange = (event) => {
    setQuery(event.target.value);
  };

  const processStreamedLines = useCallback((linesToProcess) => {
    for (const line of linesToProcess) {
      if (line.trim() === '') continue;

      try {
        const message = JSON.parse(line);
        if (message.type === 'progress') {
          setCurrentProgress({
            type: 'ai',
            stage: message.stage,
            detail: message.detail,
            timestamp: new Date().toLocaleTimeString()
          });
        } else if (message.type === 'final') {
          setMessages(prevMessages => [...prevMessages, {
            type: 'ai',
            content: message.content,
            timestamp: new Date().toLocaleTimeString()
          }]);
          setCurrentProgress(null);
        } else if (message.type === 'error') {
          setError(message.content);
          setCurrentProgress(null);
          setMessages(prevMessages => [...prevMessages, {
            type: 'error',
            content: message.content,
            timestamp: new Date().toLocaleTimeString()
          }]);
        }
      } catch (jsonError) {
        console.error("Failed to parse JSON line from stream:", line, jsonError);
      }
    }
  }, []);

  const handleResearchSubmit = async () => {
    if (!query.trim()) {
      setError("Please enter a query.");
      return;
    }

    const userMessage = { type: 'user', content: query, timestamp: new Date().toLocaleTimeString() };

    if (messages === initialMessages) {
      setMessages([userMessage]);
    } else {
      setMessages(prevMessages => [...prevMessages, userMessage]);
    }

    setIsLoading(true);
    setError('');
    setCurrentProgress({ type: 'ai', stage: 'Initiating research...', detail: '', timestamp: new Date().toLocaleTimeString() });
    setQuery('');

    try {
      const backendUrl = 'http://localhost:8000/research';

      const response = await fetch(backendUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: userMessage.content }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown server error' }));
        throw new Error(errorData.detail || `Server responded with status ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          if (buffer.length > 0) {
            processStreamedLines(buffer.split('\n'));
          }
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        processStreamedLines(lines);
      }

    } catch (err) {
      console.error('Frontend error during research fetch:', err);
      const errorMessageContent = `Failed to get research: ${err.message}. Please ensure the backend server is running and accessible.`;
      setError(errorMessageContent);
      setCurrentProgress(null);
      setMessages(prevMessages => [...prevMessages, { type: 'error', content: errorMessageContent, timestamp: new Date().toLocaleTimeString() }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !isLoading && query.trim() && !event.shiftKey) {
      event.preventDefault();
      handleResearchSubmit();
    }
  };

  const toggleSampleMessages = () => {
    const isSamplesActive = messages.length > 0 && JSON.stringify(messages[0]) === JSON.stringify(initialMessages[0]);

    if (isSamplesActive) {
      setMessages([]);
    } else {
      setMessages(initialMessages);
      setError('');
      setCurrentProgress(null);
      setIsLoading(false);
    }
  };


  const LoadingSpinner = () => (
    <svg className="icon spinner" viewBox="0 0 24 24">
      <circle className="path" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
      <path className="segment" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
  );

  return (
    <div className="chat-container">
      {/* NEW HEADER ADDITION START */}
      <header className="app-header">
        <div className="header-brand">DeepFanar</div>
        {/* You can add other header elements here if needed, like a settings icon or user profile */}
      </header>
      {/* NEW HEADER ADDITION END */}

      <div className="chat-messages-area">
        {messages.length === 0 && !isLoading && !currentProgress && (
          <div className="initial-greeting">
            Hello! How can I assist you today?
          </div>
        )}

        {messages.map((msg, index) => (
          <div key={index} className={`message-row ${msg.type === 'user' ? 'message-row-user' : 'message-row-ai'}`}>
            {/* Avatars */}
            {msg.type === 'ai' && (
              <div className="avatar ai-avatar">
                <svg xmlns="http://www.w3.org/2000/svg" className="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 7.373v-1.07a3 3 0 013-3h2.328l-1.164-1.164a1 1 0 011.414-1.414l2.829 2.829A1 0 0115 5.328V8h-2.328l-1.164 1.164a1 1 0 01-1.414 0L7 5.328V3z"></path></svg>
              </div>
            )}
            {msg.type === 'user' && (
              <div className="avatar user-avatar">
                <svg xmlns="http://www.w3.org/2000/svg" className="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
              </div>
            )}

            {/* Message Bubble */}
            <div className={`message-bubble ${
              msg.type === 'user' ? 'user-bubble' :
              msg.type === 'ai' ? 'ai-bubble' :
              'error-bubble'
            }`}>
              {msg.type === 'ai' ? (
                <div dangerouslySetInnerHTML={{ __html: msg.content }}></div>
              ) : (
                <div>{msg.content}</div>
              )}
            </div>
          </div>
        ))}

        {/* Dynamic Progress Message / Loading Indicator */}
        {currentProgress && (
          <div className="message-row message-row-ai">
            <div className="avatar ai-avatar">
              <LoadingSpinner />
            </div>
            <div className="message-bubble ai-bubble">
              <div className="loading-text">
                {currentProgress.stage} {currentProgress.detail && `(${currentProgress.detail})`}
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* NEW: Fade overlay div */}
      <div className="chat-fade-overlay"></div>

      {/* Fixed footer area for the input field */}
      <div className="chat-footer-area">
        {error && <div className="error-message-fixed">{error}</div>}
        <div className="input-wrapper-container">
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            value={query}
            onChange={handleQueryChange}
            onKeyDown={handleKeyDown}
            placeholder={isLoading ? "Please wait..." : "Ask DeepFanar..."}
            disabled={isLoading}
            rows={1}
            aria-label="Research query input"
          ></textarea>
          <button
            onClick={handleResearchSubmit}
            className="icon-button send-button"
            disabled={isLoading || !query.trim()}
            aria-label="Send message"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default App;