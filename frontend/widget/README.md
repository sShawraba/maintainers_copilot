# Maintainers Copilot Widget

A complete embeddable React chatbot widget built with Vite. This widget can be embedded into any website using a simple script tag.

## Features

- ✅ **Embeddable** - Single `<script>` tag integration
- ✅ **React + TypeScript Ready** - Modern frontend stack
- ✅ **Fully Styled** - Beautiful UI with light/dark theme support
- ✅ **Responsive** - Works on desktop, tablet, and mobile
- ✅ **CSS Isolated** - Won't conflict with host site styles
- ✅ **Production Ready** - Minified, optimized bundle
- ✅ **Configurable** - Multiple customization options
- ✅ **Accessible** - ARIA labels and semantic HTML

## Quick Start

### Installation

```bash
cd frontend/widget
npm install
```

### Development

```bash
npm run dev
```

This starts a dev server at `http://localhost:5173` with hot module replacement.

### Building

```bash
npm run build
```

This creates a production-ready bundle at `dist/widget.js`.

### Build & Watch

```bash
npm run build:watch
```

Useful during development to continuously rebuild as you make changes.

## Usage

### Basic Embedding

Add this line to any HTML page:

```html
<script src="https://yourdomain.com/widget.js" data-widget-id="demo123"></script>
```

### With Configuration

```html
<script src="https://yourdomain.com/widget-loader.js" 
        data-widget-id="my-widget"
        data-api-url="https://api.yourdomain.com"
        data-position="bottom-right"
        data-theme="light">
</script>
```

### Programmatic Initialization

```html
<script src="https://yourdomain.com/widget.js"></script>
<script>
  window.MaintainersCopilotWidget.init({
    widgetId: 'my-widget',
    apiUrl: 'https://api.yourdomain.com',
    position: 'bottom-right',
    theme: 'light',
    onClose: () => console.log('Widget closed')
  });
</script>
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `widgetId` | `default-widget` | Unique identifier for the widget instance |
| `apiUrl` | `http://localhost:8000` | Backend API endpoint |
| `position` | `bottom-right` | Widget position: `bottom-right`, `bottom-left`, `top-right`, `top-left` |
| `theme` | `light` | Color theme: `light` or `dark` |
| `containerId` | `widget-{widgetId}` | Custom container element ID |
| `onClose` | `undefined` | Callback function when widget is closed |

## Backend API Integration

The widget expects a `/api/chat` endpoint:

### Request

```json
POST /api/chat
Content-Type: application/json

{
  "message": "User question",
  "conversationId": "widget-id"
}
```

### Response

```json
{
  "response": "AI response",
  "sources": [
    {
      "title": "Source Title",
      "url": "https://..."
    }
  ]
}
```

## Project Structure

```
frontend/widget/
├── src/
│   ├── components/
│   │   ├── ChatbotWidget.jsx      # Main widget component
│   │   └── ChatMessage.jsx        # Message display component
│   ├── styles/
│   │   ├── widget.css             # Main widget styles
│   │   └── chatbot.css            # Additional styles
│   └── widget.jsx                 # Entry point
├── public/
│   └── widget-loader.js           # Loader script for easier embedding
├── index.html                      # Demo page
├── vite.config.js                 # Vite configuration
└── package.json
```

## Deployment

### Prerequisites

1. Build the widget: `npm run build`
2. Ensure your backend API is accessible

### Hosting Options

- **AWS S3 + CloudFront** - Static hosting with CDN
- **Cloudflare Pages** - Zero-config deployment
- **GitHub Pages** - Free static hosting
- **Vercel** - Serverless hosting with edge caching
- **Firebase Hosting** - Google's static hosting
- **Any static file server** - Nginx, Apache, etc.

### Steps

1. Deploy `dist/widget.js` and `public/widget-loader.js` to your CDN
2. Update the script src URL in your documentation
3. Configure CORS headers on your API endpoint
4. Test with a sample page

### CORS Configuration

Your backend must allow requests from the widget's domain:

```python
# FastAPI example
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Development Tips

### Debugging

Open browser DevTools (F12) to:
- Check console for errors
- Inspect the widget DOM
- Monitor network requests

### Theming

Customize colors by modifying CSS variables in `src/styles/widget.css`:

```css
.copilot-theme-light {
  --copilot-primary: #3b82f6;
  --copilot-secondary: #f3f4f6;
  --copilot-text: #1f2937;
  /* ... more variables */
}
```

### Adding Features

1. Modify `ChatbotWidget.jsx` for component logic
2. Update `ChatMessage.jsx` for message rendering
3. Add styles to `widget.css` for styling
4. Rebuild with `npm run build`

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari 14+, Chrome Android)

## Troubleshooting

### Widget not showing

1. Check browser console for errors
2. Verify API URL is correct and accessible
3. Check CORS headers on backend
4. Ensure script is loaded before page closes

### Styling conflicts

The widget uses CSS class prefixes (`copilot-*`) and CSS custom properties to minimize conflicts. If issues persist:

1. Check for z-index issues
2. Verify no global CSS overrides
3. Use browser DevTools to inspect computed styles

### API connection errors

1. Verify API endpoint URL
2. Check CORS configuration
3. Verify backend is running and accessible
4. Check network tab in DevTools

## License

MIT

## Support

For issues or feature requests, create an issue in the repository.
