# Multi-stage Dockerfile for both development and production
ARG PYTHON_VERSION=3.12
ARG ENVIRONMENT=production

# Base stage for common dependencies
FROM python:3.12-slim as base

# Set the working directory
WORKDIR /app

# Install system dependencies required for MariaDB, Pipenv, Netcat, and pkg-config
RUN apt-get update && apt-get install -y \
    mariadb-client \
    libmariadb-dev \
    pkg-config \
    gcc \
    build-essential \
    netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install pipenv 
RUN pip install pipenv

# Copy Pipfile
COPY Pipfile /app/

# Install dependencies using Pipenv (conditionally include dev packages)
ARG ENVIRONMENT=production
RUN if [ "$ENVIRONMENT" = "development" ]; then \
        pipenv install --system --skip-lock --dev; \
    else \
        pipenv install --system --skip-lock; \
    fi

# Copy the application code into the container
COPY . /app

# Development stage
FROM base as development
ARG ENVIRONMENT=development

# Expose the application's port
EXPOSE 8000

# Use the wait-for-db.sh script as entrypoint
RUN chmod +x /app/wait-for-db.sh
ENTRYPOINT ["./wait-for-db.sh"]

# Run migrations before starting the application
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]

# Production stage
FROM base as production
ARG ENVIRONMENT=production

# Install nginx for production
RUN apt-get update && apt-get install -y nginx && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Create nginx log directory
RUN mkdir -p /var/log/nginx

# Expose the application's port
EXPOSE 8000 80

# Set the entrypoint
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]

# Command to run the application with nginx
CMD ["sh", "-c", "nginx -t && service nginx start && gunicorn generic_chatbot.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 300"]

# Default to production stage
FROM production
