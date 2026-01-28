#!/bin/bash
# Deployment script for RegimeForge Trading Dashboard
# Run from local machine: ./deploy.sh

set -e

SERVER="ubuntu@51.44.94.136"
SSH_KEY="~/.ssh/LightsailDefaultKey-eu-west-3.pem"
REMOTE_DIR="/home/ubuntu/trading_dashboard"
VENV="/home/ubuntu/trading_venv"

echo "=== RegimeForge Trading Dashboard Deployment ==="

# Create remote directory
echo "[1/5] Creating remote directory..."
ssh -i $SSH_KEY $SERVER "mkdir -p $REMOTE_DIR"

# Sync project files (excluding unnecessary files)
echo "[2/5] Syncing project files..."
rsync -avz --progress \
    -e "ssh -i $SSH_KEY" \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.git' \
    --exclude '.vscode' \
    --exclude '.kiro' \
    --exclude '.DS_Store' \
    --exclude 'deploy.sh' \
    ./ $SERVER:$REMOTE_DIR/

# Install dependencies
echo "[3/5] Installing dependencies..."
ssh -i $SSH_KEY $SERVER "source $VENV/bin/activate && pip install -r $REMOTE_DIR/requirements.txt"

# Setup systemd service
echo "[4/5] Setting up systemd service..."
ssh -i $SSH_KEY $SERVER "sudo cp $REMOTE_DIR/deploy/trading-dashboard.service /etc/systemd/system/"
ssh -i $SSH_KEY $SERVER "sudo systemctl daemon-reload"
ssh -i $SSH_KEY $SERVER "sudo systemctl enable trading-dashboard"

# Restart service
echo "[5/5] Starting service..."
ssh -i $SSH_KEY $SERVER "sudo systemctl restart trading-dashboard"

echo ""
echo "=== Deployment Complete ==="
echo "Dashboard URL: http://51.44.94.136:5000"
echo ""
echo "Useful commands:"
echo "  Status: ssh -i $SSH_KEY $SERVER 'sudo systemctl status trading-dashboard'"
echo "  Logs:   ssh -i $SSH_KEY $SERVER 'sudo journalctl -u trading-dashboard -f'"
