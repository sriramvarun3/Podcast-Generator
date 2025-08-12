#!/bin/bash

echo "🚀 Deploying Podcast Generator API..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r ../requirements.txt

# Create required directories
echo "📁 Creating required directories..."
mkdir -p static/podcasts static/notes static/scripts static/music_beds logs

# Start the server
echo "🚀 Starting server..."
echo "📖 API Documentation: http://localhost:8000/docs"
echo "🔗 API Base URL: http://localhost:8000"
echo "⏹️  Press Ctrl+C to stop the server"

# Start server with debug mode enabled
DEBUG=true LOG_LEVEL=DEBUG python3 main.py 