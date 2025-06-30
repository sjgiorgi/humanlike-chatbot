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
    ├── Dockerfile.local
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

1. Clone the repository under Soojin branch:

    ```bash
    git clone git@github.com:wwbp/humanlike-chatbot.git
    cd humanlike-chatbot
    git checkout Soojin

    ```

2. Create .env file: Copy example.env and add required API for your chosen LLM model:

    ```bash
    cp example.env .env
    ```

3. Build and run the containers for the bot:

    ```bash
    docker-compose -f docker-compose.yml up --build
    ```

4. Access the Application at <http://localhost:8000/>

    ```bash
    http://localhost:8000/
    ```

5. To stop and remove the volumes:

    ```bash
    docker-compose -f docker-compose.yml down -v
    ```

6. [Optional] Customize the config.json file located at generic_chatbot/config.json to:

- Select a language model.
- Adjust bot-specific settings like anthropomorphism and prompts

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

1. **Access your Django instance**  

   ```bash
   cd /path/to/your/project
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
