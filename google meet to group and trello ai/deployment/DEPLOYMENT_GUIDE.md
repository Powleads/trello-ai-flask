# Google-Meet-Trello-Ai Deployment Guide

## Overview
This guide covers deploying the Google Meet to Trello AI application to various platforms.

## Quick Start (Docker)

1. **Prerequisites**
   - Docker and Docker Compose installed
   - Environment variables configured

2. **Local Development**
   ```bash
   # Clone the repository
   git clone https://github.com/your-repo/google-meet-trello-ai.git
   cd google-meet-trello-ai
   
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
   docker build -t google-meet-trello-ai:1.0.0 .
   ```

2. **Run the container**
   ```bash
   docker run -d \
     --name google-meet-trello-ai \
     -p 5000:5000 \
     -e FLASK_ENV=production \
     -e OPENAI_API_KEY=your_key \
     -e TRELLO_API_KEY=your_key \
     -e TRELLO_TOKEN=your_token \
     google-meet-trello-ai:1.0.0
   ```

### Kubernetes

1. **Apply the manifest**
   ```bash
   kubectl apply -f k8s-manifest.yaml
   ```

2. **Create secrets**
   ```bash
   kubectl create secret generic app-secrets \
     --from-literal=database-url=your_db_url \
     --from-literal=openai-api-key=your_openai_key \
     --from-literal=trello-api-key=your_trello_key \
     --from-literal=trello-token=your_trello_token
   ```

### AWS (CloudFormation)

1. **Deploy the stack**
   ```bash
   aws cloudformation create-stack \
     --stack-name google-meet-trello-ai \
     --template-body file://cloudformation.yaml \
     --parameters ParameterKey=Environment,ParameterValue=production
   ```

### Azure (ARM Template)

1. **Deploy to Azure**
   ```bash
   az deployment group create \
     --resource-group your-rg \
     --template-file azure-template.json \
     --parameters appName=google-meet-trello-ai
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