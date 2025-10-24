# EV SCMMS AI - Docker Setup Guide
==================================

This guide explains how to run the EV SCMMS AI Chatbot service using Docker.

## 🚀 Quick Start

### Prerequisites
- Docker installed on your system
- Docker Compose (usually included with Docker Desktop)

### 1. Clone and Navigate
```bash
git clone <repository-url>
cd EV_SCMMS_AI
```

### 2. Environment Setup
Create your environment file:
```bash
cp shared/config.env.example shared/config.env
# Edit shared/config.env with your actual values
```

Required environment variables:
```env
DATABASE_URL=postgresql://user:password@host:port/database
GEMINI_API_KEY=your_gemini_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### 3. Build and Run
```bash
# Build the image
docker-compose build

# Start the service
docker-compose up -d

# Check logs
docker-compose logs -f ev-scmms-ai
```

### 4. Verify Deployment
```bash
# Health check
curl http://localhost:8469/health

# Test API
curl -X POST http://localhost:8469/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello AI", "user_id": "test"}'
```

## 📋 Available Services

### EV SCMMS AI Chatbot
- **Port**: 8469
- **Health Check**: `GET /health`
- **Chat API**: `POST /api/ai/chat`
- **WebSocket**: `ws://localhost:8469`

## 🛠️ Development Commands

```bash
# Build image
docker-compose build

# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Execute commands in container
docker-compose exec ev-scmms-ai bash

# Rebuild and restart
docker-compose up -d --build
```

## 🔧 Configuration

### Environment Variables
The application uses the following environment variables (defined in `shared/config.env`):

- `DATABASE_URL`: PostgreSQL connection string
- `GEMINI_API_KEY`: Google Gemini AI API key
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase API key
- `FLASK_ENV`: Environment (development/production)

### Volumes
- `./logs:/app/logs`: Persistent logging directory

## 🏗️ Docker Image Details

### Base Image
- Python 3.11 slim
- Includes PostgreSQL client and curl for health checks

### Security
- Runs as non-root user (`app`)
- Minimal attack surface with slim base image

### Health Checks
- Automatic health monitoring every 30 seconds
- Checks `/health` endpoint
- Auto-restart on failure

## 🐛 Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Check what's using port 8469
   lsof -i :8469
   # Change port in docker-compose.yml if needed
   ```

2. **Database connection failed**
   ```bash
   # Check environment variables
   docker-compose exec ev-scmms-ai env | grep DATABASE
   # Verify database is accessible
   docker-compose exec ev-scmms-ai pg_isready -h <host> -p <port>
   ```

3. **Permission issues**
   ```bash
   # Fix logs directory permissions
   sudo chown -R $USER:$USER logs/
   ```

### Logs and Debugging
```bash
# View application logs
docker-compose logs ev-scmms-ai

# View container resource usage
docker stats

# Enter container for debugging
docker-compose exec ev-scmms-ai bash
```

## 📊 Monitoring

### Health Endpoints
- `GET /health`: Service health status
- Returns JSON with status, service name, and timestamp

### Logs
- Application logs are written to `./logs/` directory
- Container logs available via `docker-compose logs`

## 🔄 Updates

To update the application:
```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose up -d --build
```

## 🏭 Production Deployment

For production deployment:

1. Use proper secrets management (Docker secrets or external providers)
2. Configure proper logging and monitoring
3. Set up load balancing if needed
4. Use environment-specific docker-compose files
5. Implement proper backup strategies

## 📞 Support

For issues or questions:
1. Check the logs: `docker-compose logs`
2. Verify configuration files
3. Test API endpoints manually
4. Check database connectivity