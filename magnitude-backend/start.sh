#!/bin/bash

# Make the script executable
chmod +x start.sh

# Check if .env file exists
if [ ! -f .env ]; then
    echo "AWS credentials not found. Please configure your AWS credentials."
    echo "Enter your AWS Access Key ID:"
    read aws_access_key_id
    
    echo "Enter your AWS Secret Access Key:"
    read -s aws_secret_access_key
    
    echo "Enter your AWS region (e.g., us-east-1):"
    read aws_region
    
    # Create .env file with AWS credentials
    cat > .env << EOL
AWS_ACCESS_KEY_ID=$aws_access_key_id
AWS_SECRET_ACCESS_KEY=$aws_secret_access_key
AWS_DEFAULT_REGION=$aws_region
EOL
    
    echo "AWS credentials configured successfully in .env file!"
fi

# Install dependencies if not already installed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment and installing dependencies..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Start the FastAPI server
echo "Starting FastAPI server..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 