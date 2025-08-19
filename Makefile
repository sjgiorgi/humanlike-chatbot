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

lint:
	@echo "🔍 Running linting and formatting for both frontend and backend..."
	@echo ""
	@echo "📝 Backend (Django) linting..."
	@if docker compose ps | grep -q "Up"; then \
		docker exec humanlike-chatbot-backend-1 bash -c "cd /app && ./lint.sh"; \
	else \
		echo "Containers are not running. Please run 'make start' first."; \
	fi
	@echo ""
	@echo "🎨 Frontend (React) linting..."
	@cd generic_chatbot_frontend && npm run lint:fix && npm run format
	@echo ""
	@echo "✅ All linting and formatting completed!"