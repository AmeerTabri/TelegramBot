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

# Only install requirements if the file exists
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
fi

# Step 3: Copy the systemd service files
sudo cp telegram_bot.service /etc/systemd/system/
sudo cp ngrok.service /etc/systemd/system/

# Step 4: Reload and restart both services
sudo systemctl daemon-reload
sudo systemctl restart telegram_bot.service
sudo systemctl enable telegram_bot.service

sudo systemctl restart ngrok.service
sudo systemctl enable ngrok.service

# Step 5: Check if services are active
for service in telegram_bot ngrok; do
  if ! systemctl is-active --quiet "$service.service"; then
    echo "❌ $service.service is not running."
    sudo systemctl status "$service.service" --no-pager
    exit 1
  else
    echo "✅ $service.service is running."
  fi
done

# --- Step 6: Install OpenTelemetry Collector ---
OTEL_VERSION="0.94.0"
if ! command -v otelcol &> /dev/null; then
  echo "Installing OpenTelemetry Collector..."
  wget https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v${OTEL_VERSION}/otelcol_${OTEL_VERSION}_amd64.deb
  sudo dpkg -i otelcol_${OTEL_VERSION}_amd64.deb || { echo "dpkg install failed"; exit 1; }
  rm otelcol_${OTEL_VERSION}_amd64.deb
else
  echo "OpenTelemetry Collector already installed."
fi

# --- Step 7: Configure OpenTelemetry Collector ---
echo "Configuring OpenTelemetry Collector..."
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