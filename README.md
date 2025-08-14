# GENERIC BOT

## Overview

Generic Bot is a lightweight, modular chatbot framework designed to help researchers deploy and experiment with text-based conversational agents efficiently. Built with a Django backend, a React frontend, the [Kani](https://github.com/zhudotexe/kani) Framework for LLM integration, and a MariaDB database, it is fully containerized using Docker for seamless deployment.

Researchers can easily customize in config.json file:

- Language model selection
- Anthropomorphism settings
- Bot-specific prompts
- And more to come

The project streamlines research workflow with integration with tools like Qualtrics, and allows efficient data collection and analysis.
For detailed design specifications, see the [link](https://docs.google.com/document/d/1-cyC4nnibAFTxRk5-PV73yGv9hUJpHiCy3lXoQ9WDY0/edit?tab=t.0)

## Directory Structure

---

```
HUMANLIKE-CHATBOT/
├── generic_chatbot/
    ├── generic_chatbot/
        ├── settings.py
        ├── urls.py 
    ├── chatbot/
        ├── urls.py
        ├── views.py
        ├── models.py
    ├── server/
        ├── engine.py 
    ├── config.json # Custom Chatbot configuration 
    ├── Dockerfile
    ├── manage.py
    ├── Pipfile
    ├── Pipfile.lock
    ├── wait-for-db.sh
├── generic_chatbot_frontend/
    ├── public/
        ├── index.html/
    ├── src/
        ├── utils/
            ├── api.js
        ├── App.js
    ├── Dockerfile.local   
├── docker-compose.yml
├── .env # Replace .env_template with .env and add API keys
├── init.sql
├── README.md
```

---

## Getting Started

### Prerequisites

- Docker
- Docker Compose

### Setup

1. **Branch Information**: 
   - `main` branch is the stable production branch
   - `staging` branch is the development environment branch  
   - Other branches are feature branches

2. Create .env file: Copy example.env and add required API for your chosen LLM model:

    ```bash
    cp example.env .env
    ```

3. Build and run the containers for the bot:

    ```bash
    make start
    ```

4. Access the Application:
   - Run a quick session at <http://localhost:3000/>
   - Access admin interface at <http://localhost:8000/api/admin/> for defining bots and tracking conversations
   - For admin interface credential setup, see the [Admin Interface](#admin-interface) section at the end of this file

5. **Available Commands**:
   - `make start` - Start the containers (builds if needed)
   - `make stop` - Stop the containers
   - `make stop-clean` - Stop and remove volumes (clean slate)
   - `make test` - Run all django app backend tests (requires containers to be running)

---

## Project Status

Date:26/12/2024

### Current Functionality

- Language model selection and bot/prompt management via config.json
- Chat interaction logging (stored in MariaDB).
- Dockerized for easy setup and deployment.

---

### Known Bugs

- N/A
  
---

### V1 Next Steps

1. Build and integrate the React-based frontend.
2. Implement user ID tracking and storage (consider user-flow for chat page entry).
3. Create a script to convert SQL conversation data to ConvoKit-formatted JSON.
4. Host the project on AWS EC2.
5. Develop comprehensive API documentation for integration.

---

### V2 Future Enhancements

1. Add voice interaction support.
2. Create adaptable UX/UI for various research case

---

## Challenges

- **HuggingFace Support**: Compatibility issues with PyTorch libraries and GPU support in Docker need to be resolved to integrate HuggingFace models.

---

## To Be Specced & Open Questions

- How can user authentication and tracking be best integrated with Qualtrics?
- The  name of the project Humanlike chatbot does not intuitively describe what this project does do I need to keep this repository name?

## Admin Interface

1. **Access your Django instance** (run inside the backend container):

   ```bash
   docker exec -it humanlike-chatbot-backend-1 bash
   cd /app
   ```

2. **Create a superuser**  

   ```bash
   python manage.py createsuperuser
   # follow the prompts to set username, email, and password
   ```

3. **Log in to the admin panel**  
   Open your browser and go to:  

   ```
   https://<your-domain>/api/admin/
   ```  

   (or `http://localhost:8000/api/admin/` when running locally)  
   Enter the superuser credentials you just created.