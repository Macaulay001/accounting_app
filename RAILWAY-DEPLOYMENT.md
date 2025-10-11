# 🚀 Railway Deployment Guide

## Prerequisites
- GitHub account
- Railway account (free at railway.app)

## Step 1: Push to GitHub
```bash
# Initialize git if not already done
git init
git add .
git commit -m "Initial commit for Railway deployment"

# Create GitHub repository and push
git remote add origin https://github.com/yourusername/ponmo-accounting-app.git
git push -u origin main
```

## Step 2: Deploy to Railway

### Option A: Deploy from GitHub (Recommended)
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Choose your repository
6. Railway will automatically detect the Dockerfile and deploy

### Option B: Deploy with Railway CLI
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Deploy
railway up
```

## Step 3: Configure Environment Variables

In Railway dashboard, add these environment variables:

```
FIREBASE_PROJECT_ID=ponmoapp
SECRET_KEY=ponmo-accounting-app-secret-key-2025
FLASK_ENV=production
```

## Step 4: Add Firebase Auth File

1. In Railway dashboard, go to your project
2. Click on "Variables" tab
3. Add a new variable:
   - **Name**: `FIREBASE_AUTH_JSON`
   - **Value**: Copy the entire content of `firebase-auth.json` file

## Step 5: Update Firebase Authorized Domains

1. Go to Firebase Console
2. Navigate to Authentication → Settings → Authorized domains
3. Add your Railway domain (e.g., `your-app-name.railway.app`)

## Step 6: Access Your App

Once deployed, Railway will provide you with a URL like:
`https://your-app-name.railway.app`

## Railway Free Tier Benefits
- ✅ **$5 credit** per month
- ✅ **Automatic HTTPS**
- ✅ **Custom domains**
- ✅ **Persistent storage**
- ✅ **24/7 availability**
- ✅ **Easy scaling**

## Troubleshooting

### Common Issues:
1. **Build fails**: Check Dockerfile syntax
2. **App crashes**: Check environment variables
3. **Firebase auth fails**: Check authorized domains
4. **Port issues**: Ensure app uses `$PORT` environment variable

### View Logs:
```bash
railway logs
```

## Next Steps
1. Set up custom domain (optional)
2. Configure database (if needed)
3. Set up monitoring
4. Configure backups

## Cost
- **Free tier**: $5 credit per month
- **Paid plans**: Start at $5/month for more resources
