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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install pipenv 
RUN pip install pipenv

# Copy Pipfile and Pipfile.lock (if available)
COPY Pipfile Pipfile.lock /app/

# Install dependencies using Pipenv
RUN pipenv install --deploy --system

# Copy the application code into the container
COPY . /app


# Expose the application's port
EXPOSE 8000

# Set the entrypoint
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]

# Command to run the application
CMD ["gunicorn", "generic_chatbot.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "5"]
