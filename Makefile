setup_local:
	@echo "Setting up local environment..."
	@echo "Installing uv"
	@curl -LsSf https://astral.sh/uv/install.sh | sh
	uv venv
	
