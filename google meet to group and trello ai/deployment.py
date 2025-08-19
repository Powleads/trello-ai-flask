#!/usr/bin/env python3
"""
Deployment Configuration and Scripts for Google Meet to Trello AI
Supports Docker, AWS, Azure, and other cloud platforms
"""

import os
import json
import subprocess
from typing import Dict, List, Optional
from datetime import datetime

class DeploymentManager:
    """Manages deployment configurations and scripts."""
    
    def __init__(self):
        self.project_name = "google-meet-trello-ai"
        self.version = "1.0.0"
        self.environments = ["development", "staging", "production"]
    
    def generate_dockerfile(self) -> str:
        """Generate Dockerfile for containerization."""
        dockerfile_content = f"""
# Google Meet to Trello AI - Production Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV FLASK_APP=web_app.py

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \\
    && apt-get install -y --no-install-recommends \\
        gcc \\
        build-essential \\
        curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:5000/api/health || exit 1

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "web_app:app"]
"""
        return dockerfile_content.strip()
    
    def generate_docker_compose(self) -> str:
        """Generate docker-compose.yml for local development."""
        compose_content = f"""
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=development
      - DATABASE_URL=sqlite:///meetingai.db
    volumes:
      - .:/app
      - ./data:/app/data
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - web
    restart: unless-stopped

volumes:
  redis_data:
"""
        return compose_content.strip()
    
    def generate_nginx_config(self) -> str:
        """Generate nginx configuration."""
        nginx_config = """
upstream app {
    server web:5000;
}

server {
    listen 80;
    server_name localhost;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name localhost;
    
    # SSL configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    
    # File upload size
    client_max_body_size 50M;
    
    location / {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Static files
    location /static/ {
        alias /app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        proxy_pass http://app/api/health;
    }
}
"""
        return nginx_config.strip()
    
    def generate_kubernetes_manifest(self) -> str:
        """Generate Kubernetes deployment manifest."""
        k8s_manifest = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {self.project_name}
  labels:
    app: {self.project_name}
    version: {self.version}
spec:
  replicas: 3
  selector:
    matchLabels:
      app: {self.project_name}
  template:
    metadata:
      labels:
        app: {self.project_name}
        version: {self.version}
    spec:
      containers:
      - name: app
        image: {self.project_name}:{self.version}
        ports:
        - containerPort: 5000
        env:
        - name: FLASK_ENV
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: {self.project_name}-service
spec:
  selector:
    app: {self.project_name}
  ports:
  - protocol: TCP
    port: 80
    targetPort: 5000
  type: LoadBalancer
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {self.project_name}-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
  - hosts:
    - your-domain.com
    secretName: {self.project_name}-tls
  rules:
  - host: your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: {self.project_name}-service
            port:
              number: 80
"""
        return k8s_manifest.strip()
    
    def generate_aws_cloudformation(self) -> str:
        """Generate AWS CloudFormation template."""
        cloudformation_template = f"""
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Google Meet to Trello AI - AWS Infrastructure'

Parameters:
  Environment:
    Type: String
    Default: production
    AllowedValues: [development, staging, production]
  
  InstanceType:
    Type: String
    Default: t3.medium
    Description: EC2 instance type

Resources:
  # VPC and Networking
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsHostnames: true
      EnableDnsSupport: true
      Tags:
        - Key: Name
          Value: !Sub '${{AWS::StackName}}-vpc'

  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: Name
          Value: !Sub '${{AWS::StackName}}-igw'

  AttachGateway:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  # Subnets
  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.1.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: !Sub '${{AWS::StackName}}-public-subnet-1'

  PublicSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.2.0/24
      AvailabilityZone: !Select [1, !GetAZs '']
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: !Sub '${{AWS::StackName}}-public-subnet-2'

  # Security Groups
  WebSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for web servers
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0
        - IpProtocol: tcp
          FromPort: 22
          ToPort: 22
          CidrIp: 0.0.0.0/0

  # Application Load Balancer
  ApplicationLoadBalancer:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Name: !Sub '${{AWS::StackName}}-alb'
      Scheme: internet-facing
      Type: application
      Subnets:
        - !Ref PublicSubnet1
        - !Ref PublicSubnet2
      SecurityGroups:
        - !Ref WebSecurityGroup

  # Auto Scaling Group
  LaunchTemplate:
    Type: AWS::EC2::LaunchTemplate
    Properties:
      LaunchTemplateName: !Sub '${{AWS::StackName}}-launch-template'
      LaunchTemplateData:
        ImageId: ami-0c55b159cbfafe1d0  # Amazon Linux 2
        InstanceType: !Ref InstanceType
        SecurityGroupIds:
          - !Ref WebSecurityGroup
        UserData:
          Fn::Base64: !Sub |
            #!/bin/bash
            yum update -y
            yum install -y docker git
            service docker start
            usermod -a -G docker ec2-user
            
            # Install Docker Compose
            curl -L "https://github.com/docker/compose/releases/download/v2.0.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
            chmod +x /usr/local/bin/docker-compose
            
            # Clone and deploy application
            cd /home/ec2-user
            git clone https://github.com/your-repo/{self.project_name}.git
            cd {self.project_name}
            docker-compose up -d

  AutoScalingGroup:
    Type: AWS::AutoScaling::AutoScalingGroup
    Properties:
      AutoScalingGroupName: !Sub '${{AWS::StackName}}-asg'
      LaunchTemplate:
        LaunchTemplateId: !Ref LaunchTemplate
        Version: !GetAtt LaunchTemplate.LatestVersionNumber
      MinSize: 1
      MaxSize: 5
      DesiredCapacity: 2
      VPCZoneIdentifier:
        - !Ref PublicSubnet1
        - !Ref PublicSubnet2
      TargetGroupARNs:
        - !Ref TargetGroup
      HealthCheckType: ELB
      HealthCheckGracePeriod: 300

  # Target Group
  TargetGroup:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      Name: !Sub '${{AWS::StackName}}-tg'
      Port: 80
      Protocol: HTTP
      VpcId: !Ref VPC
      HealthCheckPath: /api/health
      HealthCheckProtocol: HTTP
      HealthCheckIntervalSeconds: 30
      HealthyThresholdCount: 2
      UnhealthyThresholdCount: 3

  # Listener
  Listener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      DefaultActions:
        - Type: forward
          TargetGroupArn: !Ref TargetGroup
      LoadBalancerArn: !Ref ApplicationLoadBalancer
      Port: 80
      Protocol: HTTP

Outputs:
  LoadBalancerDNS:
    Description: DNS name of the load balancer
    Value: !GetAtt ApplicationLoadBalancer.DNSName
    Export:
      Name: !Sub '${{AWS::StackName}}-LoadBalancerDNS'
"""
        return cloudformation_template.strip()
    
    def generate_azure_arm_template(self) -> str:
        """Generate Azure ARM template."""
        arm_template = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "parameters": {
                "appName": {
                    "type": "string",
                    "defaultValue": self.project_name,
                    "metadata": {
                        "description": "The name of the web app"
                    }
                },
                "sku": {
                    "type": "string",
                    "defaultValue": "B2",
                    "metadata": {
                        "description": "The SKU of App Service Plan"
                    }
                }
            },
            "variables": {
                "appServicePlanName": "[concat(parameters('appName'), '-plan')]",
                "webAppName": "[parameters('appName')]"
            },
            "resources": [
                {
                    "type": "Microsoft.Web/serverfarms",
                    "apiVersion": "2020-06-01",
                    "name": "[variables('appServicePlanName')]",
                    "location": "[resourceGroup().location]",
                    "sku": {
                        "name": "[parameters('sku')]"
                    },
                    "properties": {
                        "reserved": True
                    }
                },
                {
                    "type": "Microsoft.Web/sites",
                    "apiVersion": "2020-06-01",
                    "name": "[variables('webAppName')]",
                    "location": "[resourceGroup().location]",
                    "dependsOn": [
                        "[resourceId('Microsoft.Web/serverfarms', variables('appServicePlanName'))]"
                    ],
                    "properties": {
                        "serverFarmId": "[resourceId('Microsoft.Web/serverfarms', variables('appServicePlanName'))]",
                        "siteConfig": {
                            "linuxFxVersion": "PYTHON|3.11",
                            "appSettings": [
                                {
                                    "name": "FLASK_ENV",
                                    "value": "production"
                                },
                                {
                                    "name": "SCM_DO_BUILD_DURING_DEPLOYMENT",
                                    "value": "true"
                                }
                            ]
                        }
                    }
                }
            ],
            "outputs": {
                "webAppUrl": {
                    "type": "string",
                    "value": "[concat('https://', reference(resourceId('Microsoft.Web/sites', variables('webAppName'))).defaultHostName)]"
                }
            }
        }
        return json.dumps(arm_template, indent=2)
    
    def generate_github_actions_workflow(self) -> str:
        """Generate GitHub Actions CI/CD workflow."""
        workflow_content = f"""
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  DOCKER_IMAGE: {self.project_name}
  DOCKER_TAG: ${{{{ github.sha }}}}

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python -m pytest tests/
        python test_app.py
    
    - name: Run security scan
      run: |
        pip install bandit safety
        bandit -r . -x tests/
        safety check
    
    - name: Code quality check
      run: |
        pip install flake8 black
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        black --check .

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Login to DockerHub
      uses: docker/login-action@v2
      with:
        username: ${{{{ secrets.DOCKER_USERNAME }}}}
        password: ${{{{ secrets.DOCKER_PASSWORD }}}}
    
    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: |
          ${{{{ env.DOCKER_IMAGE }}}}:latest
          ${{{{ env.DOCKER_IMAGE }}}}:${{{{ env.DOCKER_TAG }}}}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to production
      run: |
        echo "Deploying to production environment"
        # Add your deployment commands here
        # For example, deploy to AWS ECS, Azure Container Instances, etc.
    
    - name: Health check
      run: |
        echo "Running post-deployment health checks"
        # Add health check commands here
"""
        return workflow_content.strip()
    
    def generate_production_requirements(self) -> str:
        """Generate production requirements.txt with specific versions."""
        requirements = """
# Web Framework
Flask==3.0.3
gunicorn==21.2.0

# Database
SQLAlchemy==2.0.30

# API Integration
requests==2.31.0
trello-python==0.19.0

# AI/ML
openai==1.3.0

# Authentication & Security
bcrypt==4.1.2
PyJWT==2.8.0

# Environment & Configuration
python-dotenv==1.0.0

# Date/Time handling
python-dateutil==2.8.2

# Utilities
click==8.1.7
itsdangerous==2.1.2
Jinja2==3.1.4
MarkupSafe==2.1.5
Werkzeug==3.0.3

# Production dependencies
redis==5.0.0
celery==5.3.4
flower==2.0.1

# Monitoring
prometheus-client==0.20.0
psutil==5.9.8

# Testing (for CI/CD)
pytest==8.1.1
pytest-cov==5.0.0
pytest-flask==1.3.0

# Code quality
flake8==7.0.0
black==24.3.0
bandit==1.7.8
safety==3.1.0
"""
        return requirements.strip()
    
    def create_deployment_files(self, output_dir: str = "./deployment"):
        """Create all deployment files in the specified directory."""
        os.makedirs(output_dir, exist_ok=True)
        
        files_to_create = [
            ("Dockerfile", self.generate_dockerfile()),
            ("docker-compose.yml", self.generate_docker_compose()),
            ("nginx.conf", self.generate_nginx_config()),
            ("k8s-manifest.yaml", self.generate_kubernetes_manifest()),
            ("cloudformation.yaml", self.generate_aws_cloudformation()),
            ("azure-template.json", self.generate_azure_arm_template()),
            (".github/workflows/ci-cd.yml", self.generate_github_actions_workflow()),
            ("requirements-prod.txt", self.generate_production_requirements())
        ]
        
        created_files = []
        
        for filename, content in files_to_create:
            file_path = os.path.join(output_dir, filename)
            
            # Create subdirectories if needed
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            created_files.append(file_path)
            print(f"Created: {file_path}")
        
        return created_files
    
    def generate_deployment_guide(self) -> str:
        """Generate deployment guide documentation."""
        guide = f"""
# {self.project_name.title()} Deployment Guide

## Overview
This guide covers deploying the Google Meet to Trello AI application to various platforms.

## Quick Start (Docker)

1. **Prerequisites**
   - Docker and Docker Compose installed
   - Environment variables configured

2. **Local Development**
   ```bash
   # Clone the repository
   git clone https://github.com/your-repo/{self.project_name}.git
   cd {self.project_name}
   
   # Copy and configure environment
   cp .env.example .env
   # Edit .env with your API keys
   
   # Start with Docker Compose
   docker-compose up -d
   ```

3. **Access the application**
   - Web interface: http://localhost:5000
   - Health check: http://localhost:5000/api/health

## Production Deployment

### Docker Container

1. **Build the image**
   ```bash
   docker build -t {self.project_name}:{self.version} .
   ```

2. **Run the container**
   ```bash
   docker run -d \\
     --name {self.project_name} \\
     -p 5000:5000 \\
     -e FLASK_ENV=production \\
     -e OPENAI_API_KEY=your_key \\
     -e TRELLO_API_KEY=your_key \\
     -e TRELLO_TOKEN=your_token \\
     {self.project_name}:{self.version}
   ```

### Kubernetes

1. **Apply the manifest**
   ```bash
   kubectl apply -f k8s-manifest.yaml
   ```

2. **Create secrets**
   ```bash
   kubectl create secret generic app-secrets \\
     --from-literal=database-url=your_db_url \\
     --from-literal=openai-api-key=your_openai_key \\
     --from-literal=trello-api-key=your_trello_key \\
     --from-literal=trello-token=your_trello_token
   ```

### AWS (CloudFormation)

1. **Deploy the stack**
   ```bash
   aws cloudformation create-stack \\
     --stack-name {self.project_name} \\
     --template-body file://cloudformation.yaml \\
     --parameters ParameterKey=Environment,ParameterValue=production
   ```

### Azure (ARM Template)

1. **Deploy to Azure**
   ```bash
   az deployment group create \\
     --resource-group your-rg \\
     --template-file azure-template.json \\
     --parameters appName={self.project_name}
   ```

## Environment Variables

Required environment variables for production:

```env
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-secret-key
JWT_SECRET=your-jwt-secret

# Database
DATABASE_URL=sqlite:///meetingai.db

# API Keys
OPENAI_API_KEY=your-openai-api-key
TRELLO_API_KEY=your-trello-api-key
TRELLO_TOKEN=your-trello-token
GREEN_API_INSTANCE_ID=your-green-api-instance
GREEN_API_TOKEN=your-green-api-token

# Security
SESSION_TIMEOUT=3600
RATE_LIMIT_ENABLED=true

# Monitoring
PROMETHEUS_ENABLED=true
LOG_LEVEL=INFO
```

## Monitoring and Health Checks

- **Health endpoint**: `/api/health`
- **Metrics endpoint**: `/api/metrics` (if Prometheus enabled)
- **Log aggregation**: Configure your log management system
- **Alerts**: Set up alerts for error rates and response times

## Security Considerations

1. **HTTPS**: Always use HTTPS in production
2. **Environment Variables**: Never commit secrets to version control
3. **Database**: Use encrypted connections and strong credentials
4. **Rate Limiting**: Configure appropriate rate limits
5. **Updates**: Keep dependencies updated and monitor for vulnerabilities

## Backup and Recovery

1. **Database backups**: Implement regular database backups
2. **Configuration**: Backup environment configurations
3. **Disaster recovery**: Have a recovery plan documented

## Scaling

- **Horizontal**: Use load balancers and multiple instances
- **Vertical**: Increase CPU/memory resources as needed
- **Database**: Consider database scaling strategies
- **CDN**: Use CDN for static assets

## Troubleshooting

Common issues and solutions:

1. **Application won't start**
   - Check environment variables
   - Verify database connectivity
   - Check logs for error messages

2. **API errors**
   - Verify API keys are correct
   - Check rate limits
   - Ensure network connectivity

3. **Performance issues**
   - Monitor resource usage
   - Check database performance
   - Review application logs

## Support

For issues and questions:
- Check the application logs
- Review this deployment guide
- Create an issue in the repository
"""
        return guide.strip()

def main():
    """Main deployment preparation function."""
    print(f"Preparing deployment for Google Meet to Trello AI v{DeploymentManager().version}")
    
    manager = DeploymentManager()
    
    # Create deployment files
    created_files = manager.create_deployment_files()
    
    # Create deployment guide
    guide_content = manager.generate_deployment_guide()
    with open("./deployment/DEPLOYMENT_GUIDE.md", 'w', encoding='utf-8') as f:
        f.write(guide_content)
    
    print(f"\\nCreated {len(created_files) + 1} deployment files:")
    for file_path in created_files:
        print(f"  - {file_path}")
    print("  - ./deployment/DEPLOYMENT_GUIDE.md")
    
    print("\\n✅ Deployment preparation complete!")
    print("\\nNext steps:")
    print("1. Review and customize the generated files")
    print("2. Set up your environment variables")
    print("3. Choose your deployment platform")
    print("4. Follow the deployment guide")
    
    return True

if __name__ == "__main__":
    main()