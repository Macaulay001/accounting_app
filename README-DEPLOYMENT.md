# Ponmo Accounting App - Production Deployment Guide

This guide covers deploying the Ponmo Accounting App using Docker and Kubernetes for free.

## Prerequisites

### Local Development
- Docker Desktop
- kubectl
- minikube (for local testing)

### Cloud Deployment (Free Options)
- Oracle Cloud Always Free account
- Docker Hub account
- Domain name (optional, for custom domain)

## Quick Start

### 1. Build and Test Locally

```bash
# Build Docker image
docker build -t ponmo-accounting:latest .

# Test locally
docker run -p 8000:8000 -v $(pwd)/firebase-auth.json:/app/firebase-auth.json ponmo-accounting:latest
```

### 2. Deploy to Local Kubernetes (minikube)

```bash
# Start minikube
minikube start

# Enable ingress
minikube addons enable ingress

# Deploy using the script
./deploy.sh deploy

# Get application URL
./deploy.sh url
```

### 3. Deploy to Cloud (Oracle Cloud Always Free)

#### Step 1: Set up Oracle Cloud VM
1. Create Oracle Cloud account
2. Create 2 ARM-based VMs (Always Free tier)
3. Install k3s on one VM:
   ```bash
   curl -sfL https://get.k3s.io | sh -
   sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
   chmod 600 ~/.kube/config
   ```

#### Step 2: Configure Docker Hub
1. Create Docker Hub account
2. Update `DOCKER_USERNAME` in `deploy.sh`
3. Update image name in `k8s/deployment.yaml`

#### Step 3: Deploy
```bash
# Build and push image
./deploy.sh push

# Deploy to cloud
./deploy.sh deploy
```

## Configuration

### 1. Update Secrets

Edit `k8s/secret.yaml` and replace the base64 encoded values:

```bash
# Encode your firebase-auth.json
base64 -i firebase-auth.json | tr -d '\n'

# Encode your secret key
echo -n "your-secret-key" | base64

# Update the secret.yaml file with these values
```

### 2. Update ConfigMap

Edit `k8s/configmap.yaml` with your Firebase project details:

```yaml
data:
  FIREBASE_PROJECT_ID: "your-actual-project-id"
  FIREBASE_DATABASE_URL: "https://your-project-id-default-rtdb.firebaseio.com/"
```

### 3. Update Ingress

Edit `k8s/ingress.yaml` with your domain:

```yaml
rules:
- host: your-domain.com
  http:
    paths:
    - path: /
      pathType: Prefix
      backend:
        service:
          name: accounting-app-service
          port:
            number: 80
```

## File Structure

```
k8s/
├── namespace.yaml          # Namespace definition
├── configmap.yaml          # Configuration data
├── secret.yaml             # Sensitive data (base64 encoded)
├── deployment.yaml         # Application deployment
├── service.yaml            # Service definition
├── ingress.yaml            # Ingress configuration
├── hpa.yaml               # Horizontal Pod Autoscaler
├── cluster-issuer.yaml    # Cert-manager for TLS
├── persistent-volume.yaml  # Optional persistent storage
└── kustomization.yaml     # Kustomize configuration

.github/workflows/
└── docker-build.yml       # GitHub Actions CI/CD

deploy.sh                  # Deployment script
Dockerfile                 # Docker image definition
.dockerignore             # Docker ignore file
```

## Deployment Commands

```bash
# Build Docker image
./deploy.sh build

# Build and push to registry
./deploy.sh push

# Deploy to Kubernetes
./deploy.sh deploy

# View logs
./deploy.sh logs

# Scale deployment
./deploy.sh scale 3

# Get application URL
./deploy.sh url

# Delete deployment
./deploy.sh delete
```

## Manual Deployment

If you prefer manual deployment:

```bash
# Create namespace
kubectl create namespace accounting-app

# Create secret (replace with your values)
kubectl create secret generic accounting-app-secrets \
  --from-file=firebase-auth.json=firebase-auth.json \
  --from-literal=secret-key="your-secret-key" \
  --from-literal=firebase-project-id="your-project-id" \
  -n accounting-app

# Apply all manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n accounting-app
kubectl get services -n accounting-app
kubectl get ingress -n accounting-app
```

## Monitoring and Maintenance

### Health Checks
- Application health endpoint: `/healthz`
- Kubernetes liveness and readiness probes configured

### Scaling
- Horizontal Pod Autoscaler (HPA) configured
- Scales based on CPU (70%) and memory (80%) usage
- Min replicas: 2, Max replicas: 10

### Logs
```bash
# View application logs
kubectl logs -f deployment/accounting-app -n accounting-app

# View specific pod logs
kubectl logs -f <pod-name> -n accounting-app
```

### Updates
```bash
# Update image
kubectl set image deployment/accounting-app accounting-app=your-dockerhub-username/ponmo-accounting:new-tag -n accounting-app

# Rollback
kubectl rollout undo deployment/accounting-app -n accounting-app
```

## Troubleshooting

### Common Issues

1. **Pod not starting**
   ```bash
   kubectl describe pod <pod-name> -n accounting-app
   kubectl logs <pod-name> -n accounting-app
   ```

2. **Service not accessible**
   ```bash
   kubectl get services -n accounting-app
   kubectl get ingress -n accounting-app
   ```

3. **Firebase authentication issues**
   - Check if `firebase-auth.json` is properly mounted
   - Verify Firebase project ID and database URL

4. **Resource constraints**
   ```bash
   kubectl top pods -n accounting-app
   kubectl describe nodes
   ```

### Debug Commands

```bash
# Get all resources
kubectl get all -n accounting-app

# Describe deployment
kubectl describe deployment accounting-app -n accounting-app

# Check events
kubectl get events -n accounting-app --sort-by='.lastTimestamp'

# Port forward for local testing
kubectl port-forward service/accounting-app-service 8000:80 -n accounting-app
```

## Security Considerations

1. **Secrets Management**
   - Use Kubernetes secrets for sensitive data
   - Consider using external secret management (e.g., HashiCorp Vault)

2. **Network Security**
   - Configure network policies
   - Use TLS/SSL certificates

3. **Access Control**
   - Implement RBAC (Role-Based Access Control)
   - Use service accounts with minimal permissions

## Cost Optimization

### Free Tier Limits
- **Oracle Cloud Always Free**: 2 ARM VMs, 1GB RAM each
- **Docker Hub**: 1 private repository, unlimited public
- **GitHub Actions**: 2000 minutes/month

### Resource Optimization
- Adjust resource requests/limits based on usage
- Use horizontal pod autoscaling
- Monitor resource usage regularly

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review Kubernetes and Docker logs
3. Verify configuration files
4. Test locally before deploying to cloud
