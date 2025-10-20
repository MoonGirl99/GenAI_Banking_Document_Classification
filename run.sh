#!/bin/bash
# ==============================================================================
# Bank Document Classification System - Complete Startup Script
# ==============================================================================

set -e  # Exit on error

echo "🚀 Starting Bank Document Classification System..."
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  WARNING: .env file not found!"
    echo ""
    echo "Please create a .env file with your Mistral API key:"
    echo "---------------------------------------------------"
    echo "MISTRAL_API_KEY=your_api_key_here"
    echo "---------------------------------------------------"
    echo ""
    read -p "Do you want to create it now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your Mistral API key: " api_key
        echo "MISTRAL_API_KEY=$api_key" > .env
        echo "✅ .env file created!"
    else
        echo "❌ Cannot start without API key. Exiting..."
        exit 1
    fi
fi

echo "✅ .env file found"
echo ""

# Check if Docker is running
echo "🔍 Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    echo "Please start Docker Desktop and try again."
    exit 1
fi
echo "✅ Docker is running"
echo ""

# Stop any existing containers
echo "🛑 Stopping any existing containers..."
docker compose down 2>/dev/null || true
echo ""

# Build and start containers
echo "🏗️  Building and starting containers..."
docker compose up -d --build

echo ""
echo "⏳ Waiting for services to start..."
sleep 5

# Check if containers are running
echo ""
echo "🔍 Checking container status..."
docker compose ps

echo ""
echo "======================================================================"
echo "✅ Bank Document Classification System is NOW RUNNING!"
echo "======================================================================"
echo ""
echo "🌐 WEB APPLICATION:    http://localhost:8000"
echo "📚 API DOCUMENTATION:  http://localhost:8000/docs"
echo "🔌 API HEALTH CHECK:   http://localhost:8000/api/health"
echo "🗄️  CHROMADB:          http://localhost:8001"
echo ""
echo "======================================================================"
echo ""
echo "📋 Quick Actions:"
echo "  • Open Web UI:      open http://localhost:8000"
echo "  • View logs:        docker compose logs -f app"
echo "  • Stop server:      docker compose down"
echo "  • Restart:          docker compose restart"
echo ""
echo "======================================================================"
echo ""
echo "🎉 Ready to process documents!"
echo ""

# Offer to open browser
read -p "Would you like to open the Web UI in your browser? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Opening browser..."
    sleep 2
    open http://localhost:8000 2>/dev/null || xdg-open http://localhost:8000 2>/dev/null || echo "Please open http://localhost:8000 in your browser"
fi

echo ""
echo "💡 TIP: Upload the test_document.txt file to see the system in action!"
echo ""

