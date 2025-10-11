#!/bin/bash

# Railway Deployment Script for Ponmo Accounting App
set -e

echo "🚀 Starting Railway deployment..."

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📦 Initializing git repository..."
    git init
    git add .
    git commit -m "Initial commit for Railway deployment"
fi

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "📥 Installing Railway CLI..."
    npm install -g @railway/cli
fi

# Login to Railway
echo "🔐 Logging into Railway..."
railway login

# Deploy to Railway
echo "🚀 Deploying to Railway..."
railway up

echo "✅ Deployment completed!"
echo ""
echo "🔍 Next steps:"
echo "1. Go to Railway dashboard"
echo "2. Set environment variables:"
echo "   - FIREBASE_PROJECT_ID=ponmoapp"
echo "   - SECRET_KEY=ponmo-accounting-app-secret-key-2025"
echo "   - FLASK_ENV=production"
echo "3. Add Firebase auth file as FIREBASE_AUTH_JSON variable"
echo "4. Update Firebase authorized domains with your Railway URL"
echo ""
echo "📱 Your app will be available at: https://your-app-name.railway.app"
