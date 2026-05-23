import React, { useState, useRef, useEffect } from 'react';
import { Send, X, MessageCircle, Loader } from 'lucide-react';
import ChatMessage from './ChatMessage';
import '../styles/chatbot.css';

const ChatbotWidget = ({ widgetId, apiUrl, position, theme, onClose }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 'welcome-1',
      role: 'assistant',
      content: 'Hello! I am the Maintainers Copilot. How can I help you today?',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiUrl}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: input,
          conversationId: widgetId,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      const assistantMessage = {
        id: `msg-${Date.now()}-ai`,
        role: 'assistant',
        content: data.response || data.message || 'I could not process your request.',
        timestamp: new Date(),
        sources: data.sources || [],
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error('Error sending message:', err);
      setError(err.message || 'Failed to send message. Please try again.');

      const errorMessage = {
        id: `msg-${Date.now()}-error`,
        role: 'assistant',
        content: `Sorry, I encountered an error: ${err.message}`,
        timestamp: new Date(),
        isError: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`copilot-widget copilot-widget-${position}`}>
      {!isOpen && (
        <button
          className="copilot-toggle-button"
          onClick={() => setIsOpen(true)}
          aria-label="Open chatbot"
          title="Chat with Maintainers Copilot"
        >
          <MessageCircle size={24} />
        </button>
      )}

      {isOpen && (
        <div className="copilot-chat-window">
          <div className="copilot-header">
            <div className="copilot-header-content">
              <h3>Maintainers Copilot</h3>
              <p className="copilot-status">Online</p>
            </div>
            <button
              className="copilot-close-button"
              onClick={() => {
                setIsOpen(false);
                onClose?.();
              }}
              aria-label="Close chatbot"
            >
              <X size={20} />
            </button>
          </div>

          <div className="copilot-messages">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            {loading && (
              <div className="copilot-message copilot-message-loading">
                <div className="copilot-message-content">
                  <Loader size={16} className="copilot-spinner" />
                  <span>Thinking...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {error && (
            <div className="copilot-error">
              {error}
            </div>
          )}

          <form className="copilot-input-area" onSubmit={handleSendMessage}>
            <input
              ref={inputRef}
              type="text"
              className="copilot-input"
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
              aria-label="Message input"
            />
            <button
              type="submit"
              className="copilot-send-button"
              disabled={loading || !input.trim()}
              aria-label="Send message"
            >
              <Send size={18} />
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

export default ChatbotWidget;
