#!/bin/bash
#
# Python Project Setup Script
# Version: 1.0.0
# Last Updated: 2025-08-06
# Description: General template for setting up Python projects with virtual environment
#
# Changelog:
# v1.0.0 (2025-08-06) - Initial general template version

echo "📦 Starting project setup..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

if [ ! -d "venv" ]; then
  echo "🔧 Creating virtual environment..."
  python3 -m venv venv
  
  if [ $? -ne 0 ]; then
    echo "❌ Failed to create virtual environment."
    exit 1
  fi

  echo "📥 Activating virtual environment and upgrading pip..."
  source venv/bin/activate
  pip install --upgrade pip
  
  echo "📦 Installing dependencies from requirements.txt..."
  pip install -r requirements.txt
  
  if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies."
    exit 1
  fi
else
  echo "✅ Virtual environment already exists. Skipping creation."
  echo "💡 To reinstall dependencies, delete the 'venv' folder and run this script again."
fi

echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
  echo "⚠️  .env file not found!"
  echo "📝 Creating .env template..."
  cat > .env << 'EOF'
# Project Configuration
# Add your environment variables here
# Example:
# API_KEY=your-api-key
# DATABASE_URL=your-database-url
EOF
  echo "✅ Created .env template. Please edit it with your actual values."
else
  echo "✅ .env file already exists."
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📌 Next steps:"
echo "➡️  1. Edit .env file with your configuration"
echo "➡️  2. Run: source venv/bin/activate"
echo "➡️  3. Run: python3 main.py (or your main script)"
