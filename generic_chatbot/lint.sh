#!/bin/bash

set -e

echo "🔍 Running Django backend linting and formatting..."

# Run ruff for linting and formatting
echo "📝 Running ruff check and format..."
pipenv run ruff check . --fix
pipenv run ruff format .

# Run isort for import sorting
echo "📦 Running isort..."
pipenv run isort . --profile black

# Run mypy for type checking (optional but recommended)
echo "🔍 Running mypy type checking..."
pipenv run mypy . --ignore-missing-imports || echo "⚠️  Mypy found type issues (non-blocking)"

echo ""
echo "✅ Django backend linting completed!"
echo ""
echo "Available commands:"
echo "  pipenv run ruff check .          # Check for issues"
echo "  pipenv run ruff check . --fix    # Fix issues"
echo "  pipenv run ruff format .         # Format code"
echo "  pipenv run isort .               # Sort imports"
echo "  pipenv run mypy .                # Type checking"
