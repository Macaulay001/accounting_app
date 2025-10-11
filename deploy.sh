#!/bin/bash

# Deployment script for Ponmo Accounting App
# Usage: ./deploy.sh [environment] [action]
# Example: ./deploy.sh production deploy

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DOCKER_USERNAME="oladims-dockerhub"
IMAGE_NAME="ponmo-accounting"
TAG="latest"
NAMESPACE="accounting-app"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if kubectl is installed
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
}

# Check if docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."
    docker build -t ${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG} .
    log_info "Docker image built successfully"
}

# Push Docker image
push_image() {
    log_info "Pushing Docker image to registry..."
    docker push ${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG}
    log_info "Docker image pushed successfully"
}

# Deploy to Kubernetes
deploy_k8s() {
    log_info "Deploying to Kubernetes..."
    
    # Create namespace if it doesn't exist
    kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply all Kubernetes manifests
    kubectl apply -f k8s/
    
    # Wait for deployment to be ready
    log_info "Waiting for deployment to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/accounting-app -n ${NAMESPACE}
    
    log_info "Deployment completed successfully!"
}

# Get application URL
get_url() {
    log_info "Getting application URL..."
    
    # For minikube
    if command -v minikube &> /dev/null && minikube status &> /dev/null; then
        URL=$(minikube service accounting-app-service -n ${NAMESPACE} --url)
        log_info "Application URL: $URL"
    else
        # For other clusters, show ingress
        kubectl get ingress -n ${NAMESPACE}
    fi
}

# Show logs
show_logs() {
    log_info "Showing application logs..."
    kubectl logs -f deployment/accounting-app -n ${NAMESPACE}
}

# Scale deployment
scale_deployment() {
    local replicas=$1
    log_info "Scaling deployment to $replicas replicas..."
    kubectl scale deployment accounting-app -n ${NAMESPACE} --replicas=$replicas
}

# Delete deployment
delete_deployment() {
    log_warn "Deleting deployment..."
    kubectl delete -f k8s/
    log_info "Deployment deleted"
}

# Main script
main() {
    local action=${1:-deploy}
    
    case $action in
        "build")
            check_docker
            build_image
            ;;
        "push")
            check_docker
            build_image
            push_image
            ;;
        "deploy")
            check_kubectl
            deploy_k8s
            get_url
            ;;
        "logs")
            check_kubectl
            show_logs
            ;;
        "scale")
            check_kubectl
            local replicas=${2:-2}
            scale_deployment $replicas
            ;;
        "delete")
            check_kubectl
            delete_deployment
            ;;
        "url")
            check_kubectl
            get_url
            ;;
        *)
            echo "Usage: $0 [build|push|deploy|logs|scale|delete|url]"
            echo ""
            echo "Commands:"
            echo "  build   - Build Docker image"
            echo "  push    - Build and push Docker image"
            echo "  deploy  - Deploy to Kubernetes"
            echo "  logs    - Show application logs"
            echo "  scale   - Scale deployment (usage: $0 scale 3)"
            echo "  delete  - Delete deployment"
            echo "  url     - Get application URL"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
