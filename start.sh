#!/bin/bash

# Document Classification System - Start Script

echo "🚀 Starting Bank Document Classification System..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please create a .env file with your MISTRAL_API_KEY:"
    echo "  echo 'MISTRAL_API_KEY=your_api_key_here' > .env"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

echo "✅ Starting services with Docker Compose..."
docker-compose up -d

echo ""
echo "✅ Services started successfully!"
echo ""
echo "📝 API Documentation: http://localhost:8000/docs"
echo "🔌 API Endpoint: http://localhost:8000"
echo "🗄️  ChromaDB: http://localhost:8001"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"

