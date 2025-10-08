# Makefile for Quran Ayah Lookup Package

# Variables
VENV_NAME = venv
PYTHON = python3
PIP = $(VENV_NAME)/bin/pip
PYTHON_VENV = $(VENV_NAME)/bin/python

# Default target
.DEFAULT_GOAL := help

# Help target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Initialize virtual environment
init: ## Initialize virtual environment
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv $(VENV_NAME)
	@echo "Virtual environment created at ./$(VENV_NAME)"
	@echo "To activate: source $(VENV_NAME)/bin/activate"

# Install production dependencies
install:deps: ## Install production dependencies
	@echo "Installing production dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "Production dependencies installed."

# Install development dependencies
install:deps:dev: ## Install development dependencies
	@echo "Installing development dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -e .
	@echo "Development dependencies installed."

# Run tests
test: ## Run unit tests
	@echo "Running unit tests..."
	$(PYTHON_VENV) -m pytest tests/ -v
	@echo "Tests completed."

# Run tests with coverage
test:coverage: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	$(PYTHON_VENV) -m pytest tests/ --cov=src/quran_ayah_lookup --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/"

# Format code with black
format: ## Format code with black
	@echo "Formatting code with black..."
	$(PYTHON_VENV) -m black src/ tests/
	@echo "Code formatting completed."

# Lint code with flake8
lint: ## Lint code with flake8
	@echo "Linting code with flake8..."
	$(PYTHON_VENV) -m flake8 src/ tests/
	@echo "Linting completed."

# Type check with mypy
typecheck: ## Type check with mypy
	@echo "Type checking with mypy..."
	$(PYTHON_VENV) -m mypy src/
	@echo "Type checking completed."

# Run all checks (format, lint, typecheck, test)
check: format lint typecheck test ## Run all checks (format, lint, typecheck, test)
	@echo "All checks completed."

# Build package
build: ## Build the package
	@echo "Building package..."
	$(PYTHON_VENV) -m build
	@echo "Package built in dist/"

# Clean build artifacts
clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "Cleanup completed."

# Clean everything including virtual environment
clean:all: clean ## Clean everything including virtual environment
	@echo "Removing virtual environment..."
	rm -rf $(VENV_NAME)
	@echo "Complete cleanup finished."

# Install package in development mode
install:dev: ## Install package in development mode
	@echo "Installing package in development mode..."
	$(PIP) install -e .
	@echo "Package installed in development mode."

# Publish to PyPI (test)
publish:test: ## Publish to test PyPI
	@echo "Publishing to test PyPI..."
	$(PYTHON_VENV) -m twine upload --repository testpypi dist/*
	@echo "Published to test PyPI."

# Publish to PyPI (production)
publish: ## Publish to PyPI
	@echo "Publishing to PyPI..."
	$(PYTHON_VENV) -m twine upload dist/*
	@echo "Published to PyPI."

# Development setup (complete setup for development)
setup:dev: init install:deps:dev ## Complete development setup
	@echo "Development environment setup completed!"
	@echo "To activate the virtual environment: source $(VENV_NAME)/bin/activate"

.PHONY: help init install:deps install:deps:dev test test:coverage format lint typecheck check build clean clean:all install:dev publish:test publish setup:dev