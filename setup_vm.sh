#!/bin/bash

# Update package list and install required packages
sudo apt update
sudo apt install -y python3-pip python3-venv git

# Create project directory and virtual environment
mkdir -p /home/ubuntu/paper-trader
cd /home/ubuntu/paper-trader
python3 -m venv venv
source venv/bin/activate

# Install project dependencies
pip install -r requirements.txt
