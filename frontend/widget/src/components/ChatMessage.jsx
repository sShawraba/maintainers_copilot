import React from 'react';

const ChatMessage = ({ message }) => {
  const isAssistant = message.role === 'assistant';

  return (
    <div className={`copilot-message copilot-message-${message.role}`}>
      <div className="copilot-message-content">
        <p>{message.content}</p>
        {message.sources && message.sources.length > 0 && (
          <div className="copilot-sources">
            <details>
              <summary>Sources ({message.sources.length})</summary>
              <ul>
                {message.sources.map((source, idx) => (
                  <li key={idx}>
                    {source.url ? (
                      <a href={source.url} target="_blank" rel="noopener noreferrer">
                        {source.title || source.url}
                      </a>
                    ) : (
                      <span>{source.title || 'Source'}</span>
                    )}
                  </li>
                ))}
              </ul>
            </details>
          </div>
        )}
      </div>
      <span className="copilot-message-time">
        {message.timestamp && message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </span>
    </div>
  );
};

export default ChatMessage;
