start:
	@if docker compose ps | grep -q "Up"; then \
		echo "Containers are already running"; \
	else \
		docker compose up --build -d; \
	fi

stop:
	docker compose down

stop-clean:
	docker compose down -v

test:
	@if docker compose ps | grep -q "Up"; then \
		docker exec humanlike-chatbot-backend-1 bash -c "cd /app && DJANGO_SETTINGS_MODULE=generic_chatbot.settings pytest"; \
	else \
		echo "Containers are not running. Please run 'make start' first."; \
	fi
