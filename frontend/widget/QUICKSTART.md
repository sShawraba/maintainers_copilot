# Quick Start Guide

Get the Maintainers Copilot widget up and running in minutes.

## Prerequisites

- Node.js 16+ and npm
- Your backend API running (or modify `apiUrl` in config)
- A modern web browser

## Setup (5 minutes)

### 1. Install Dependencies

```bash
cd frontend/widget
npm install
```

### 2. Start Development Server

```bash
npm run dev
```

Open http://localhost:5173 in your browser. You should see the demo page with the widget.

### 3. Configure API Endpoint

Edit `src/components/ChatbotWidget.jsx` and update the default API URL if needed:

```javascript
const apiUrl = config.apiUrl || 'http://localhost:8000';
```

Or pass it as a config option when initializing the widget.

## Testing Locally

### Option 1: Using the Demo Page

The widget comes with a demo page at `index.html`:

```bash
npm run dev
# Open http://localhost:5173
```

### Option 2: Creating a Test Page

Create a simple HTML file to test the widget:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Widget Test</title>
</head>
<body>
    <h1>Test Page</h1>
    <p>The widget should appear in the bottom-right corner</p>

    <!-- Load from development server -->
    <script src="http://localhost:5173/dist/widget.js"></script>
    <script>
        window.MaintainersCopilotWidget.init({
            widgetId: 'test-widget',
            apiUrl: 'http://localhost:8000',
            position: 'bottom-right',
            theme: 'light'
        });
    </script>
</body>
</html>
```

### Option 3: Using the Loader Script

Test the loader script locally:

```bash
# In one terminal, start dev server
npm run dev

# In another terminal, serve the public folder
cd public
python -m http.server 8080

# In test.html, use:
# <script src="http://localhost:8080/widget-loader.js" 
#         data-widget-id="test"></script>
```

## Building for Production

### 1. Build the Widget

```bash
npm run build
```

This creates:
- `dist/widget.js` - Main widget bundle (~60KB minified)
- `public/widget-loader.js` - Loader script (~2KB)

### 2. Verify the Build

```bash
# Check files exist and their sizes
ls -lh dist/widget.js public/widget-loader.js

# Expected output:
# dist/widget.js: ~60KB
# public/widget-loader.js: ~2KB
```

### 3. Deploy Files

Upload both files to your CDN or static host:

```bash
# Using AWS S3 example
aws s3 cp dist/widget.js s3://your-bucket/widget.js
aws s3 cp public/widget-loader.js s3://your-bucket/widget-loader.js
```

## Integration

### Basic (Recommended)

Add one line of HTML to any webpage:

```html
<script src="https://yourdomain.com/widget-loader.js" 
        data-widget-id="demo123">
</script>
```

### Advanced

For more control, use programmatic initialization:

```html
<script src="https://yourdomain.com/widget.js"></script>
<script>
    window.MaintainersCopilotWidget.init({
        widgetId: 'my-widget',
        apiUrl: 'https://api.yourdomain.com',
        position: 'bottom-right',
        theme: 'light',
        onClose: () => {
            console.log('Widget closed');
        }
    });
</script>
```

## Configuration

All options are optional (sensible defaults provided):

| Option | Default | Values |
|--------|---------|--------|
| `widgetId` | `default-widget` | Any unique string |
| `apiUrl` | `http://localhost:8000` | Your API endpoint |
| `position` | `bottom-right` | `bottom-right`, `bottom-left`, `top-right`, `top-left` |
| `theme` | `light` | `light`, `dark` |
| `containerId` | `widget-{widgetId}` | Custom element ID |
| `onClose` | `undefined` | Callback function |

## API Endpoint

Your backend must expose a `/api/chat` endpoint:

```python
@app.post("/api/chat")
async def chat(request: dict):
    message = request.get("message")
    conversation_id = request.get("conversationId")
    
    # Your implementation
    response = await your_chat_function(message, conversation_id)
    
    return {
        "response": response["text"],
        "sources": [
            {
                "title": "Source Title",
                "url": "https://example.com"
            }
        ]
    }
```

## Troubleshooting

### Widget not appearing

1. Check browser console for errors
2. Verify API URL is correct
3. Check if CORS is enabled on your backend
4. Make sure the script tag is at the end of `<body>`

### Messages not sending

1. Verify API endpoint is running
2. Check Network tab in DevTools
3. Look for CORS errors
4. Ensure JSON response format is correct

### Styling issues

1. Check for conflicting CSS
2. Verify widget CSS loaded properly
3. Inspect widget DOM with DevTools
4. Check for z-index issues with other elements

## Development Tips

### Watch Mode for Development

```bash
npm run build:watch
```

This continuously rebuilds as you edit files.

### Debug Widget Code

In `src/components/ChatbotWidget.jsx`, add console logs:

```javascript
console.log('Widget initialized with config:', { widgetId, apiUrl, position, theme });
```

### Test API Integration

```bash
# Test the API endpoint directly
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello",
    "conversationId": "test-widget"
  }'
```

### Performance Optimization

1. Minification happens automatically in `npm run build`
2. Use a CDN for distribution
3. Set proper cache headers (see DEPLOYMENT.md)
4. Monitor bundle size: `npm run build` shows final size

## File Structure Reference

```
frontend/widget/
├── src/
│   ├── components/
│   │   ├── ChatbotWidget.jsx    # Main chat component
│   │   └── ChatMessage.jsx      # Message renderer
│   ├── styles/
│   │   ├── widget.css           # Widget styles
│   │   └── chatbot.css          # Chat styles
│   └── widget.jsx               # Entry point
├── public/
│   └── widget-loader.js         # Loader script
├── index.html                   # Demo page
├── example-integration.html     # Full example
├── vite.config.js              # Build config
├── package.json                # Dependencies
└── README.md                   # Full docs
```

## Next Steps

1. ✅ Run locally: `npm run dev`
2. ✅ Test with your API
3. ✅ Customize styling if needed
4. ✅ Build: `npm run build`
5. ✅ Deploy files to CDN
6. ✅ Add embed code to your site
7. ✅ Test in production
8. ✅ Monitor usage and errors

## Getting Help

- Check [README.md](./README.md) for detailed documentation
- See [DEPLOYMENT.md](./DEPLOYMENT.md) for deployment guides
- Review [example-integration.html](./example-integration.html) for usage examples
- Check browser DevTools console for error messages

---

**Ready to go?** Start with `npm install && npm run dev` 🚀
