/**
 * Maintainers Copilot Widget Loader
 * 
 * This script loads the widget dynamically and injects it into the page.
 * 
 * Usage:
 *   <script src="https://yourdomain.com/widget-loader.js" data-widget-id="demo123"></script>
 * 
 * Or with more options:
 *   <script src="https://yourdomain.com/widget-loader.js" 
 *           data-widget-id="demo123" 
 *           data-api-url="https://api.yourdomain.com"
 *           data-position="bottom-right"
 *           data-theme="light">
 *   </script>
 */

(function () {
  'use strict';

  // Get the script tag that loaded this loader
  const loaderScript = document.currentScript;
  if (!loaderScript) {
    console.error('[Copilot Widget] Could not find loader script');
    return;
  }

  // Extract configuration from data attributes
  const config = {
    widgetId: loaderScript.dataset.widgetId || 'default-widget',
    apiUrl: loaderScript.dataset.apiUrl || 'http://localhost:8000',
    position: loaderScript.dataset.position || 'bottom-right',
    theme: loaderScript.dataset.theme || 'light',
    widgetUrl: loaderScript.dataset.widgetUrl || getWidgetUrl(),
  };

  /**
   * Determine the widget URL based on the loader script source
   */
  function getWidgetUrl() {
    const src = loaderScript.src;
    if (src.includes('localhost') || src.includes('127.0.0.1')) {
      return 'http://localhost:5173/dist/widget.js';
    }
    // Replace widget-loader.js with widget.js
    return src.replace(/widget-loader\.js/, 'widget.js');
  }

  /**
   * Load the widget script
   */
  function loadWidget() {
    const script = document.createElement('script');
    script.src = config.widgetUrl;
    script.type = 'text/javascript';
    script.async = true;
    script.onerror = function () {
      console.error('[Copilot Widget] Failed to load widget from: ' + config.widgetUrl);
    };
    script.onload = function () {
      initializeWidget();
    };
    document.head.appendChild(script);
  }

  /**
   * Initialize the widget once it's loaded
   */
  function initializeWidget() {
    if (typeof window.MaintainersCopilotWidget === 'undefined') {
      console.error('[Copilot Widget] Widget library not found');
      return;
    }

    // Initialize with the configuration
    window.MaintainersCopilotWidget.init(config);

    // Log success
    console.log('[Copilot Widget] Initialized with config:', config);
  }

  /**
   * Wait for DOM to be ready, then load the widget
   */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadWidget);
  } else {
    loadWidget();
  }
})();
