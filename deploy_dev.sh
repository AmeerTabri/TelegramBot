#!/bin/bash

cd ~/TelegramBot

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

# --- Step 6: Install OpenTelemetry Collector ---
if ! command -v otelcol &> /dev/null; then
  echo "Installing OpenTelemetry Collector..."
  sudo apt-get update
  sudo apt-get -y install wget
  wget https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.127.0/otelcol_0.127.0_linux_amd64.deb
  sudo dpkg -i otelcol_0.127.0_linux_amd64.deb
  rm otelcol_0.127.0_linux_amd64.deb
else
  echo "✅ OpenTelemetry Collector already installed."
fi

# --- Step 7: Configure OpenTelemetry Collector ---
echo "Configuring OpenTelemetry Collector..."
sudo mkdir -p /etc/otelcol
sudo tee /etc/otelcol/config.yaml > /dev/null <<EOF
receivers:
  hostmetrics:
    collection_interval: 15s
    scrapers:
      cpu:
      memory:
      disk:
      filesystem:
      load:
      network:
      processes:

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"

service:
  pipelines:
    metrics:
      receivers: [hostmetrics]
      exporters: [prometheus]
EOF

# --- Step 8: Restart and enable otelcol ---
sudo systemctl restart otelcol
sudo systemctl enable otelcol

# --- Step 9: Verify otelcol is running ---
if ! systemctl is-active --quiet otelcol; then
  echo "❌ otelcol service is not running."
  sudo systemctl status otelcol --no-pager
  exit 1
else
  echo "✅ otelcol service is running and exposing metrics on port 8889."
fi