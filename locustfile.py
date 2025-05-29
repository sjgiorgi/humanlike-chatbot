import logging
from locust import HttpUser, task, between
import random
import datetime
from gevent.lock import Semaphore
from locust.exception import StopUser

# for handler in logging.root.handlers[:]:
#     logging.root.removeHandler(handler)
logging.basicConfig(filename="locust_errors.log",
                    level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s",
                    force=True)  # if using Python 3.8+
logging.info("Test log: logging is working.")

# Global dictionary to count failures by key (request type + endpoint)
failure_counts = {}


def log_failure_event(request_type, name, response_time, response_length, exception, status_code):
    key = f"{request_type} {name} [Status: {status_code}]"
    failure_counts[key] = failure_counts.get(key, 0) + 1
    logging.error("Request Failure: %s %s took %.2fms, response_length: %s, status_code: %s. Exception: %s. Count: %d",
                  request_type, name, response_time, response_length, status_code, exception, failure_counts[key])


def log_success_event(request_type, name, response_time, response_length):
    logging.info("Request Success: %s %s took %.2fms, response_length: %s",
                 request_type, name, response_time, response_length)


# Global counter to track completed users in the experiment
completed_users = 0
completed_lock = Semaphore()


class ConversationUser(HttpUser):
    wait_time = between(1, 3)
    # Number of chat messages per conversation (adjustable)
    conversation_length = 10

    # Payload templates for initialization and chat messages
    payloads = {
        "initialize": {
            "initial_utterance": "Hello!",
            "study_name": "study1",
            "user_group": "group1",
            "survey_id": "survey1",
            "survey_meta_data": "meta"
        },
        "chat": {
            "message": "How are you?"
        }
    }

    def fetch_bots(self):
        """Fetch available bots from the /api/bots/ endpoint."""
        response = self.client.get("/api/bots/")
        if response.status_code == 200:
            return response.json().get("bots", [])
        else:
            log_failure_event("GET", "/api/bots/",
                              response.elapsed.total_seconds() * 1000,
                              len(response.content),
                              Exception("Failed to fetch bots"),
                              response.status_code)
            return []

    def initialize_conversation(self, bot_name, participant_id):
        """Initialize a conversation via /api/initialize_conversation/."""
        # Generate a unique conversation_id for the payload
        conv_id_generated = f"conv_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"
        init_payload = self.payloads["initialize"].copy()
        init_payload.update({
            "bot_name": bot_name,
            "participant_id": participant_id,
            "conversation_id": conv_id_generated
        })
        response = self.client.post(
            "/api/initialize_conversation/", json=init_payload)
        if response.status_code == 200:
            return response.json().get("conversation_id")
        else:
            log_failure_event("POST", "/api/initialize_conversation/",
                              response.elapsed.total_seconds() * 1000,
                              len(response.content),
                              Exception("Conversation initialization failed"),
                              response.status_code)
            return None

    def send_chat_message(self, bot_name, conversation_id, participant_id, message):
        """Send a chat message via /api/chatbot/ and capture the response."""
        chat_payload = self.payloads["chat"].copy()
        chat_payload.update({
            "message": message,
            "bot_name": bot_name,
            "conversation_id": conversation_id,
            "participant_id": participant_id
        })
        response = self.client.post("/api/chatbot/", json=chat_payload)
        if response.status_code != 200:
            log_failure_event("POST", "/api/chatbot/",
                              response.elapsed.total_seconds() * 1000,
                              len(response.content),
                              Exception("Chat message failed"),
                              response.status_code)
        else:
            log_success_event("POST", "/api/chatbot/",
                              response.elapsed.total_seconds() * 1000,
                              len(response.content))
        return response

    @task
    def conversation_flow(self):
        # 1) fetch bots, pick one
        bots = self.fetch_bots()
        if not bots:
            logging.error("No bots available.")
            raise StopUser()

        bot = random.choice(bots).get("name")

        # 2) init conversation
        participant_id = f"test_{datetime.datetime.now():%Y%m%d%H%M%S}_{random.randint(1000,9999)}"
        conv_id = self.initialize_conversation(bot, participant_id)
        if not conv_id:
            raise StopUser()

        # 3) send `conversation_length` messages
        for i in range(self.conversation_length):
            msg = f"Message {i+1}: How are you?"
            self.send_chat_message(bot, conv_id, participant_id, msg)

        logging.info("Conversation done for %s on %s", participant_id, bot)
        # *** tear down this user ***
        raise StopUser()

    def on_stop(self):
        global completed_users
        with completed_lock:
            completed_users += 1
            total = self.environment.runner.user_count
            logging.info("Completed %d/%d", completed_users, total)
            if completed_users >= total:
                logging.info("All done → quitting runner.")
                self.environment.runner.quit()
