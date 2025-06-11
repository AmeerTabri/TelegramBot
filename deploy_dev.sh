#!/bin/bash

cd ~/TelegramBot

# Step -1: Install Docker (if not already installed)
echo "Installing Docker..."
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo tee /etc/apt/keyrings/docker.asc > /dev/null
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# (Optional) Add current user to docker group so you don't need sudo
sudo usermod -aG docker $USER

# Step 0: Ensure Python 3, pip, and venv are installed
echo "Checking Python and pip..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# Step 1: Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

# Step 2: Activate venv and install dependencies
source .venv/bin/activate
pip install --upgrade pip

# Only install requirements if the file exists
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
fi

# Step 3: Copy the systemd service files
sudo cp telegram_bot_dev.service /etc/systemd/system/

# Step 4: Reload and restart both services
sudo systemctl daemon-reload
sudo systemctl restart telegram_bot_dev.service
sudo systemctl enable telegram_bot_dev.service

# Step 5: Check if services are active
for service in telegram_bot_dev; do
  if ! systemctl is-active --quiet "$service.service"; then
    echo "❌ $service.service is not running."
    sudo systemctl status "$service.service" --no-pager
    exit 1
  else
    echo "✅ $service.service is running."
  fi
done
