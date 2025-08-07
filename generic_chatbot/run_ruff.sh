#!/bin/bash

# Run ruff on the Django project
echo "Running ruff check..."
pipenv run ruff check . --fix

echo ""
echo "Ruff check completed!"
echo ""
echo "To run ruff without fixing issues: pipenv run ruff check ."
echo "To run ruff with unsafe fixes: pipenv run ruff check . --fix --unsafe-fixes"
echo "To format code with ruff: pipenv run ruff format ." 