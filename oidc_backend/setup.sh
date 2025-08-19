#!/bin/bash

# OIDC Backend Setup Script
echo "🚀 Setting up OIDC Backend with PostgreSQL Database"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip3 first."
    exit 1
fi

# Install dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Check if PostgreSQL is running
if ! pg_isready -q; then
    echo "⚠️  PostgreSQL is not running. Please start PostgreSQL first."
    echo "   You can start it with: sudo systemctl start postgresql"
    echo "   Or use Docker: docker run --name postgres-oidc -e POSTGRES_PASSWORD=password -e POSTGRES_DB=oidc -p 5432:5432 -d postgres:13"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "✅ Created .env file. Please edit it with your database credentials if needed."
fi

# Setup database
echo "🗄️  Setting up database..."
python3 manage_db.py setup

if [ $? -eq 0 ]; then
    echo "✅ Database setup completed successfully!"
    echo ""
    echo "🎉 Setup complete! You can now run the application:"
    echo "   python3 app_with_db.py"
    echo ""
    echo "📊 Available endpoints:"
    echo "   - http://localhost:5000/dashboard (Database dashboard)"
    echo "   - http://localhost:5000/api/credentials (Credentials API)"
    echo "   - http://localhost:5000/api/verification-logs (Verification logs API)"
    echo "   - http://localhost:5000/verify (Credential verification UI)"
    echo "   - http://localhost:5000/form_credential (Credential request form)"
else
    echo "❌ Database setup failed. Please check the error messages above."
    exit 1
fi 