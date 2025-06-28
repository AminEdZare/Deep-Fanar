// deep-research-frontend/src/App.jsx

import React, { useState, useRef, useEffect, useCallback } from "react";
import "./index.css";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

const App = () => {
  const initialMessages = []; // This should now be empty based on previous step

  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState(initialMessages);
  const [currentProgress, setCurrentProgress] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [showSidePanel, setShowSidePanel] = useState(false);
  const [finalReportContent, setFinalReportContent] = useState('');
  const [sources, setSources] = useState([]);
  const [isTTSLoading, setIsTTSLoading] = useState(false);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const [isAudioPaused, setIsAudioPaused] = useState(false);
  const [currentAudio, setCurrentAudio] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // NEW: Determine if we are in the initial state
  const isInitialState = messages.length === 0 && !isLoading && !currentProgress;

  useEffect(() => {
    // Only scroll if not in initial state and side panel is not open
    if (!showSidePanel && !isInitialState) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, currentProgress, showSidePanel, isInitialState]); // Add isInitialState to dependencies

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
            content: "View Research Report",
            isClickableReport: true,
            timestamp: new Date().toLocaleTimeString()
          }]);
          setFinalReportContent(message.content);
          setSources(message.sources || []);
          setCurrentProgress(null);
          setShowSidePanel(true);
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

    // This block for initialMessages check is no longer strictly needed if initialMessages is always empty
    // However, if you ever re-introduce initial messages, this logic might be useful.
    // For now, it will simply add the userMessage to an empty array.
    if (messages.length > 0 && JSON.stringify(messages[0]) === JSON.stringify(initialMessages[0])) {
      setMessages([userMessage]);
    } else {
      setMessages(prevMessages => [...prevMessages, userMessage]);
    }

    setIsLoading(true);
    setError('');
    setCurrentProgress({ type: 'ai', stage: 'Initiating research...', detail: '', timestamp: new Date().toLocaleTimeString() });
    setQuery('');
    setShowSidePanel(false);
    setFinalReportContent('');

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

  // The handleClearChat function is still present if you wish to use it for other purposes,
  // but it's no longer triggered by a visible button.
  const handleClearChat = () => {
    setMessages(initialMessages); // This will set messages to []
    setError('');
    setCurrentProgress(null);
    setIsLoading(false);
    setQuery('');
    setShowSidePanel(false);
    setFinalReportContent('');
    setSources([]);
  };

  const toggleSidePanel = () => {
    setShowSidePanel(prev => !prev);
  };

  // Helper component for the spinner
  const LoadingSpinner = () => (
    <svg className="icon spinner" viewBox="0 0 24 24">
      <circle className="path" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
      <path className="segment" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
  );

  // Functions for Copy and Download Report
  const handleCopyReport = () => {
    if (finalReportContent) {
      navigator.clipboard.writeText(finalReportContent)
        .then(() => {
          console.log('Report copied to clipboard!');
        })
        .catch(err => {
          console.error('Failed to copy report: ', err);
        });
    }
  };

  const handleTextToSpeech = async (retryCount = 0) => {
    if (!finalReportContent) {
      console.error('No content to convert to speech');
      return;
    }

    setIsTTSLoading(true);
    setIsAudioPaused(false); // Reset paused state when starting new TTS
    try {
      const backendUrl = 'http://localhost:8000/tts';

      // Check if content is very long and notify user
      if (finalReportContent.length > 2000) {
        console.log('Long content detected, will be truncated for TTS');
        // Show a brief notification that content will be truncated
        setError('Note: Long research report will be truncated for speech synthesis. Full report available in text.');
        // Clear the error after 3 seconds
        setTimeout(() => setError(''), 3000);
      }

      const response = await fetch(backendUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: finalReportContent }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'TTS service error' }));
        const errorMessage = errorData.detail || `TTS service responded with status ${response.status}`;

        // Handle specific error types
        if (response.status === 408) {
          throw new Error(`TTS timeout: ${errorMessage}. Try with a shorter research report.`);
        } else if (response.status === 503) {
          // Retry for service unavailable errors
          if (retryCount < 2) {
            console.log(`TTS service unavailable, retrying... (attempt ${retryCount + 1})`);
            setIsTTSLoading(false);
            setTimeout(() => handleTextToSpeech(retryCount + 1), 2000); // Retry after 2 seconds
            return;
          } else {
            throw new Error(`TTS service unavailable after ${retryCount + 1} attempts. Please try again later.`);
          }
        } else {
          throw new Error(errorMessage);
        }
      }

      // Get the audio blob
      const audioBlob = await response.blob();

      // Create an audio URL and play it
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);

      setIsAudioPlaying(true);
      setCurrentAudio(audio);

      audio.onended = () => {
        URL.revokeObjectURL(audioUrl); // Clean up the URL
        setIsAudioPlaying(false);
        setIsAudioPaused(false);
        setCurrentAudio(null);
      };

      audio.onerror = () => {
        URL.revokeObjectURL(audioUrl);
        setIsAudioPlaying(false);
        setIsAudioPaused(false);
        setCurrentAudio(null);
        setError('Failed to play audio. Please try again.');
      };

      await audio.play();

    } catch (err) {
      console.error('TTS error:', err);
      setError(`Failed to convert text to speech: ${err.message}`);
    } finally {
      setIsTTSLoading(false);
    }
  };

  const handleDownloadReport = () => {
    if (finalReportContent) {
      const today = new Date();
      const yyyy = today.getFullYear();
      const mm = String(today.getMonth() + 1).padStart(2, '0');
      const dd = String(today.getDate()).padStart(2, '0');
      const filename = `DeepFanar_Research_Report_${yyyy}-${mm}-${dd}.pdf`;

      const blob = new Blob([finalReportContent], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  const handlePauseResume = () => {
    if (currentAudio && (isAudioPlaying || isAudioPaused)) {
      if (isAudioPlaying) {
        currentAudio.pause();
        setIsAudioPlaying(false);
        setIsAudioPaused(true);
      } else {
        currentAudio.play();
        setIsAudioPlaying(true);
        setIsAudioPaused(false);
      }
    } else {
      // Start new TTS
      handleTextToSpeech();
    }
  };

  const startRecording = async () => {
    try {
      // Check if MediaRecorder is supported
      if (!window.MediaRecorder) {
        setError('Voice recording is not supported in this browser. Please use a modern browser.');
        return;
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks = [];

      recorder.ondataavailable = (event) => {
        chunks.push(event.data);
      };

      recorder.onstop = async () => {
        const audioBlob = new Blob(chunks, { type: 'audio/mp3' });
        await transcribeAudio(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
    } catch (err) {
      console.error('Error starting recording:', err);
      if (err.name === 'NotAllowedError') {
        setError('Microphone access denied. Please allow microphone permissions and try again.');
      } else {
        setError('Failed to start recording. Please check microphone permissions.');
      }
    }
  };

  const stopRecording = () => {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
      setIsRecording(false);
      setMediaRecorder(null);
    }
  };

  const transcribeAudio = async (audioBlob) => {
    try {
      // Create FormData to send the audio file
      const formData = new FormData();
      formData.append('file', audioBlob, 'recording.mp3');

      const response = await fetch('http://localhost:8000/transcribe', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Transcription failed: ${response.status}`);
      }

      const result = await response.json();
      if (result.text) {
        setQuery(result.text);
      } else {
        setError('No text was transcribed from the audio.');
      }
    } catch (err) {
      console.error('Transcription error:', err);
      setError('Failed to transcribe audio. Please try again.');
    }
  };

  const handleMicrophoneClick = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <div className={`main-layout-container ${showSidePanel ? 'side-panel-open' : ''}`}>
      {isInitialState ? (
        // === Initial Screen Layout ===
        <div className="initial-screen-wrapper">
          <header className="app-header">
            <div className="header-brand">DeepFanar</div>
          </header>
          <div className="initial-center-content">
            <h2 className="initial-prompt-text">What would you like to research?</h2>
            <div className="input-wrapper-container initial-input-container">
              <textarea
                ref={textareaRef}
                className="chat-textarea"
                value={query}
                onChange={handleQueryChange}
                onKeyDown={handleKeyDown}
                placeholder={"Ask DeepFanar"}
                disabled={isLoading}
                rows={1}
                aria-label="Research query input"
              ></textarea>
              <button
                onClick={handleMicrophoneClick}
                className={`microphone-button ${isRecording ? 'recording' : ''}`}
                disabled={isLoading}
                aria-label={isRecording ? "Stop recording" : "Start voice recording"}
                title={isRecording ? "Stop recording" : "Voice input"}
              >
                {isRecording ? (
                  <svg xmlns="http://www.w3.org/2000/svg" className="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <rect x="6" y="6" width="12" height="12" rx="2" ry="2"></rect>
                  </svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" className="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                    <line x1="12" y1="19" x2="12" y2="23"></line>
                    <line x1="8" y1="23" x2="16" y2="23"></line>
                  </svg>
                )}
              </button>
              <button
                onClick={handleResearchSubmit}
                className="send-button"
                disabled={isLoading || !query.trim()}
                aria-label="Send message"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
              </button>
            </div>
            {error && <div className="error-message-fixed initial-error-message">{error}</div>}
          </div>
        </div>
      ) : (
        // === Existing: Chat Interface Layout ===
        <div className="chat-interface-wrapper">
          <header className="app-header">
            <div className="header-brand">DeepFanar</div>
          </header>

          <div className="chat-messages-area">
            {messages.map((msg, index) => (
              <div key={index} className={`message-row ${msg.type === 'user' ? 'message-row-user' : 'message-row-ai'}`}>
                {/* Avatars */}
                {msg.type === 'ai' && (
                  <div className="avatar ai-avatar">
                    <svg xmlns="http://www.w3.org/2000/svg" className="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 7.373v-1.07a3 3 0 013-3h2.328l-1.164-1.164a1 1 0 011.414-1.414l2.829 2.829A1 1 0 0115 5.328V8h-2.328l-1.164 1.164a1 1 0 01-1.414 0L7 5.328V3z"></path></svg>
                  </div>
                )}
                {msg.type === 'user' && (
                  <div className="avatar user-avatar">
                    <svg xmlns="http://www.w3.org/2000/svg" className="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
                  </div>
                )}

                {/* Message Bubble */}
                <div className={`message-bubble ${msg.type === 'user' ? 'user-bubble' :
                  msg.type === 'ai' ? 'ai-bubble' :
                    'error-bubble'
                  }`}>
                  <div className="message-header">
                    <span className="message-timestamp">{msg.timestamp}</span>
                  </div>
                  {msg.isClickableReport ? (
                    <button onClick={toggleSidePanel} className="view-report-button">
                      {msg.content}
                      <svg className={`icon arrow-icon ${showSidePanel ? 'rotated' : ''}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  ) : msg.type === 'ai' ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                      {msg.content}
                    </ReactMarkdown>
                  ) : (
                    <div>{msg.content}</div>
                  )}
                </div>
              </div>
            ))}

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
                onClick={handleMicrophoneClick}
                className={`microphone-button ${isRecording ? 'recording' : ''}`}
                disabled={isLoading}
                aria-label={isRecording ? "Stop recording" : "Start voice recording"}
                title={isRecording ? "Stop recording" : "Voice input"}
              >
                {isRecording ? (
                  <svg xmlns="http://www.w3.org/2000/svg" className="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <rect x="6" y="6" width="12" height="12" rx="2" ry="2"></rect>
                  </svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" className="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                    <line x1="12" y1="19" x2="12" y2="23"></line>
                    <line x1="8" y1="23" x2="16" y2="23"></line>
                  </svg>
                )}
              </button>
              <button
                onClick={handleResearchSubmit}
                className="send-button"
                disabled={isLoading || !query.trim()}
                aria-label="Send message"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
              </button>
            </div>
          </div>
        </div>
      )}

      <div className={`side-panel ${showSidePanel ? 'open' : ''}`}>
        <div className="side-panel-header">
          {/* Title remains on the left */}
          <h3>Synthesized Report</h3>
          <div className="panel-actions">
            {/* Volume button for TTS */}
            <button
              onClick={handlePauseResume}
              className="icon-button"
              aria-label={isAudioPlaying ? "Pause audio" : isAudioPaused ? "Resume audio" : "Convert report to speech"}
              title={isAudioPlaying ? "Pause audio" : isAudioPaused ? "Resume audio" : "Text to Speech"}
              disabled={isTTSLoading || !finalReportContent}
            >
              {isTTSLoading ? (
                <LoadingSpinner />
              ) : isAudioPlaying ? (
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="icon">
                  <rect x="6" y="4" width="4" height="16"></rect>
                  <rect x="14" y="4" width="4" height="16"></rect>
                </svg>
              ) : isAudioPaused ? (
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="icon">
                  <polygon points="5 4 15 12 5 20 5 4"></polygon>
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="icon">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                  <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                  <path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>
                </svg>
              )}
            </button>
            {/* Copy button moved back to the right */}
            <button onClick={handleCopyReport} className="icon-button" aria-label="Copy report to clipboard" title="Copy Report">
              {/* Copy Icon: Two Rectangles */}
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="icon">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
            </button>
            <button onClick={handleDownloadReport} className="icon-button" aria-label="Download report as PDF" title="Download Report">
              {/* Download Icon (Disk with arrow) - unchanged */}
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="icon">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
            </button>
            <button onClick={toggleSidePanel} className="icon-button close-panel-button" aria-label="Close panel" title="Close Panel">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
        <div className="side-panel-content">
          {finalReportContent ? (
            <>
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                {finalReportContent}
              </ReactMarkdown>

              {sources.length > 0 && (
                <div className="sources-section">
                  <h4>Sources</h4>
                  <div className="sources-list">
                    {sources.map((url, index) => (
                      <div key={index} className="source-item">
                        <a
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="source-link"
                        >
                          {url}
                        </a>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <p>No report loaded.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;