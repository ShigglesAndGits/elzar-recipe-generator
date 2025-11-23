#!/bin/bash

# Elzar Setup Script
# This script helps set up Elzar for the first time

set -e

echo "🌶️  Welcome to Elzar Setup! BAM!"
echo ""

# Check Python
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✓ Found Python $PYTHON_VERSION"
echo ""

# Check Node.js
echo "Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    echo "⚠️  Node.js is not installed. You'll need it for frontend development."
    echo "   Download from: https://nodejs.org/"
    echo ""
else
    NODE_VERSION=$(node --version)
    echo "✓ Found Node.js $NODE_VERSION"
    echo ""
fi

# Backend Setup
echo "Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

echo "Activating virtual environment and installing dependencies..."
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ Backend dependencies installed"

if [ ! -f ".env" ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Edit backend/.env with your actual configuration:"
    echo "   - GROCY_URL"
    echo "   - GROCY_API_KEY"
    echo "   - LLM_API_KEY"
    echo "   - LLM_MODEL"
    echo ""
else
    echo "✓ .env file already exists"
fi

cd ..

# Frontend Setup
if command -v npm &> /dev/null; then
    echo "Setting up frontend..."
    cd frontend
    
    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies (this may take a minute)..."
        npm install
        echo "✓ Frontend dependencies installed"
    else
        echo "✓ Frontend dependencies already installed"
    fi
    
    cd ..
else
    echo "⚠️  Skipping frontend setup (Node.js not found)"
fi

# Create data directories
echo "Creating data directories..."
mkdir -p data/recipes
echo "✓ Data directories created"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit backend/.env with your configuration"
echo "2. Start the backend:"
echo "   cd backend && source venv/bin/activate && python -m app.main"
echo "3. In a new terminal, start the frontend:"
echo "   cd frontend && npm run dev"
echo "4. Open http://localhost:5173 in your browser"
echo ""
echo "For detailed instructions, see QUICKSTART.md"
echo ""
echo "BAM! Let's make something delicious! 🌶️"

