#!/bin/bash

echo "Setting up environment variables for local development..."

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cat > .env << EOF
# Database Configuration
MYSQL_ROOT_PASSWORD=rootpassword
MYSQL_DATABASE=chatbot_db
MYSQL_USER=chatbot_user
MYSQL_PASSWORD=chatbot_password
DATABASE_NAME=chatbot_db
DATABASE_USER=chatbot_user
DATABASE_PASSWORD=chatbot_password
DATABASE_HOST=db
DATABASE_PORT=3306

# Django Configuration
DEBUG=True
SECRET_KEY=your-secret-key-here-for-local-development
CORS_ALLOW_ALL_ORIGINS=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# API Keys (you'll need to add your actual keys)
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# AWS Configuration (for local development, you can use dummy values or real ones)
AWS_BUCKET_NAME=your-s3-bucket-name
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
BACKEND_ENVIRONMENT=local

# Frontend Configuration
REACT_APP_API_URL=http://localhost:8000

# Chatbot Configuration
CHATBOT_CONTROL_IMAGE=https://example.com/control-image.png
CHATBOT_AVATAR_PROMPT=Create a professional avatar for a chatbot
EOF
    echo "✅ Created .env file with default values"
else
    echo "⚠️  .env file already exists. Please check if it has the required variables."
fi

echo ""
echo "📝 Next steps:"
echo "1. Edit the .env file and add your actual API keys:"
echo "   - OPENAI_API_KEY"
echo "   - ANTHROPIC_API_KEY"
echo "   - AWS credentials (if you want S3 functionality)"
echo ""
echo "2. Run your Docker Compose setup:"
echo "   docker-compose up --build"
echo ""
echo "3. If you don't have AWS credentials, the app will run with S3 functionality disabled." 