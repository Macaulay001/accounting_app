#!/bin/bash

# Kubernetes Deployment Script for Ponmo Accounting App
set -e

echo "🚀 Starting Kubernetes deployment..."

# Check prerequisites
echo "📋 Checking prerequisites..."
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed. Please install kubectl first."
    exit 1
fi

if ! kubectl cluster-info &> /dev/null; then
    echo "❌ kubectl is not configured or cluster is not accessible."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Create namespace
echo "📦 Creating namespace..."
kubectl apply -f k8s/namespace.yaml

# Create ConfigMap
echo "⚙️ Creating ConfigMap..."
kubectl apply -f k8s/configmap.yaml

# Create Secret (you need to update this with your actual values)
echo "🔐 Creating Secret..."
echo "⚠️  WARNING: Make sure to update k8s/secret.yaml with your actual base64 encoded values!"
kubectl apply -f k8s/secret.yaml

# Create Persistent Volume (optional)
echo "💾 Creating Persistent Volume..."
kubectl apply -f k8s/persistent-volume.yaml

# Deploy the application
echo "🚀 Deploying application..."
kubectl apply -f k8s/deployment.yaml

# Create Service
echo "🌐 Creating Service..."
kubectl apply -f k8s/service.yaml

# Create Ingress
echo "🔗 Creating Ingress..."
kubectl apply -f k8s/ingress.yaml

# Create HPA
echo "📈 Creating Horizontal Pod Autoscaler..."
kubectl apply -f k8s/hpa.yaml

# Wait for deployment
echo "⏳ Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/accounting-app -n accounting-app

# Show status
echo "📊 Deployment Status:"
kubectl get pods -n accounting-app
kubectl get services -n accounting-app
kubectl get ingress -n accounting-app

echo "✅ Deployment completed!"
echo ""
echo "🔍 To check logs: kubectl logs -f deployment/accounting-app -n accounting-app"
echo "🌐 To access locally: kubectl port-forward service/accounting-app-service 8080:80 -n accounting-app"
echo "📱 Then open: http://localhost:8080"
