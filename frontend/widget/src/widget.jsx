import React from 'react';
import ReactDOM from 'react-dom/client';
import ChatbotWidget from './components/ChatbotWidget';
import './styles/widget.css';

window.MaintainersCopilotWidget = {
  init: function (config = {}) {
    // Get the widget ID from script data attribute or config
    const scriptTag = document.currentScript;
    const widgetId =
      config.widgetId ||
      scriptTag?.dataset.widgetId ||
      'default-widget';

    const apiUrl =
      config.apiUrl ||
      scriptTag?.dataset.apiUrl ||
      'http://localhost:8000';

    const containerId = config.containerId || `widget-${widgetId}`;
    const position = config.position || 'bottom-right';
    const theme = config.theme || 'light';

    // Find or create container
    let container = document.getElementById(containerId);
    if (!container) {
      container = document.createElement('div');
      container.id = containerId;
      container.className = `copilot-widget-container copilot-${position} copilot-theme-${theme}`;
      document.body.appendChild(container);
    }

    // Render the widget
    const root = ReactDOM.createRoot(container);
    root.render(
      <ChatbotWidget
        widgetId={widgetId}
        apiUrl={apiUrl}
        position={position}
        theme={theme}
        onClose={() => {
          // Optional: Handle close event
          if (config.onClose) {
            config.onClose();
          }
        }}
      />
    );

    return root;
  },

  // Expose config for programmatic initialization
  config: {
    apiUrl: 'http://localhost:8000',
    widgetId: 'default-widget',
  },
};

// Auto-initialize if script tag has data-auto-init attribute
if (document.currentScript?.dataset.autoInit !== 'false') {
  document.addEventListener('DOMContentLoaded', () => {
    window.MaintainersCopilotWidget.init();
  });
}
