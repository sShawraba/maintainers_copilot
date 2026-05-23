#!/bin/bash

# Maintainers Copilot Widget - Build & Deploy Script
# Usage: ./deploy.sh [environment]
# Environments: dev, staging, production

set -e

ENVIRONMENT=${1:-dev}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="$SCRIPT_DIR/dist"
PUBLIC_DIR="$SCRIPT_DIR/public"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🤖 Maintainers Copilot Widget - Build & Deploy"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Environment: $ENVIRONMENT"
echo "Script Directory: $SCRIPT_DIR"
echo ""

# Configuration by environment
case $ENVIRONMENT in
  dev)
    CDN_URL="http://localhost:5173"
    S3_BUCKET=""
    CLOUDFRONT_DIST=""
    API_URL="http://localhost:8000"
    ;;
  staging)
    CDN_URL="https://staging-cdn.yourdomain.com"
    S3_BUCKET="copilot-widget-staging"
    CLOUDFRONT_DIST="E1234ABCD"
    API_URL="https://staging-api.yourdomain.com"
    ;;
  production)
    CDN_URL="https://cdn.yourdomain.com"
    S3_BUCKET="copilot-widget-prod"
    CLOUDFRONT_DIST="E5678EFGH"
    API_URL="https://api.yourdomain.com"
    ;;
  *)
    echo "❌ Unknown environment: $ENVIRONMENT"
    echo "Usage: ./deploy.sh [dev|staging|production]"
    exit 1
    ;;
esac

# Step 1: Install dependencies
echo "📦 Installing dependencies..."
npm install

# Step 2: Build the widget
echo "🔨 Building widget..."
npm run build

if [ ! -f "$DIST_DIR/widget.js" ]; then
  echo "❌ Build failed: widget.js not found"
  exit 1
fi

# Step 3: Check file sizes
echo "📊 File sizes:"
du -h "$DIST_DIR/widget.js"
du -h "$PUBLIC_DIR/widget-loader.js"

WIDGET_SIZE=$(stat -f%z "$DIST_DIR/widget.js" 2>/dev/null || stat -c%s "$DIST_DIR/widget.js")
LOADER_SIZE=$(stat -f%z "$PUBLIC_DIR/widget-loader.js" 2>/dev/null || stat -c%s "$PUBLIC_DIR/widget-loader.js")

if [ "$WIDGET_SIZE" -gt 200000 ]; then
  echo "⚠️  Warning: widget.js is larger than expected ($WIDGET_SIZE bytes)"
fi

# Step 4: Generate embed code
echo ""
echo "📝 Generated embed code:"
echo ""
echo "<script src=\"$CDN_URL/widget-loader.js\""
echo "        data-widget-id=\"my-widget\""
echo "        data-api-url=\"$API_URL\""
echo "        data-position=\"bottom-right\""
echo "        data-theme=\"light\">"
echo "</script>"
echo ""

# Step 5: Deploy to CDN (if not dev)
if [ "$ENVIRONMENT" != "dev" ]; then
  echo "🚀 Deploying to CDN..."
  
  if command -v aws &> /dev/null; then
    echo "📤 Uploading to S3 ($S3_BUCKET)..."
    
    # Upload with appropriate cache headers
    aws s3 cp "$DIST_DIR/widget.js" "s3://$S3_BUCKET/widget.js" \
      --cache-control "public, max-age=3600" \
      --content-type "application/javascript" \
      --region us-east-1
    
    aws s3 cp "$PUBLIC_DIR/widget-loader.js" "s3://$S3_BUCKET/widget-loader.js" \
      --cache-control "public, max-age=300" \
      --content-type "application/javascript" \
      --region us-east-1
    
    echo "✅ Files uploaded to S3"
    
    # Invalidate CloudFront cache (if available)
    if [ ! -z "$CLOUDFRONT_DIST" ]; then
      echo "🔄 Invalidating CloudFront cache..."
      aws cloudfront create-invalidation \
        --distribution-id "$CLOUDFRONT_DIST" \
        --paths "/*" \
        --region us-east-1
      echo "✅ CloudFront cache invalidated"
    fi
  else
    echo "⚠️  AWS CLI not found. Skipping S3 upload."
    echo "📖 Manual deployment steps:"
    echo "   1. Upload $DIST_DIR/widget.js to $CDN_URL/widget.js"
    echo "   2. Upload $PUBLIC_DIR/widget-loader.js to $CDN_URL/widget-loader.js"
  fi
fi

# Step 6: Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Build and deployment complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Summary:"
echo "   Environment: $ENVIRONMENT"
echo "   Widget URL: $CDN_URL/widget.js"
echo "   Loader URL: $CDN_URL/widget-loader.js"
echo "   API URL: $API_URL"
echo "   Widget Size: $((WIDGET_SIZE / 1024))KB"
echo ""
echo "🔗 Next steps:"
echo "   1. Add the embed code above to your website"
echo "   2. Verify the widget appears and connects to your API"
echo "   3. Test in different browsers and devices"
echo "   4. Monitor performance and errors"
echo ""
