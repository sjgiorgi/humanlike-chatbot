# Use a Python image
FROM python:3.12

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
    nginx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install pipenv 
RUN pip install pipenv

# Copy Pipfile
COPY Pipfile /app/

# Install dependencies using Pipenv
RUN pipenv install --system --skip-lock

# Copy the application code into the container
COPY . /app

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
