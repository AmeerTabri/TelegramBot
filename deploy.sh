#!/bin/bash

cd ~/TelegramBot

# Step 1: Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

# Step 2: Activate venv and install dependencies
source .venv/bin/activate
pip install --upgrade pip

# Step 3: Copy the systemd service file
sudo cp telegram_bot.service /etc/systemd/system/

# Step 4: Reload and restart the service
sudo systemctl daemon-reload
sudo systemctl restart telegram_bot.service
sudo systemctl enable telegram_bot.service

# Step 5: Check if service is active
if ! systemctl is-active --quiet telegram_bot.service; then
  echo "❌ telegram_bot.service is not running."
  sudo systemctl status telegram_bot.service --no-pager
  exit 1
else
  echo "✅ telegram_bot.service is running."
fi
