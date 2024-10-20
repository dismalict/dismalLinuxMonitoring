#!/bin/bash

# Update package list and install pip if not already installed
echo "Updating package list..."
sudo apt update

echo "Checking if pip is installed..."
if ! command -v pip &> /dev/null
then
    echo "pip not found, installing pip..."
    sudo apt install -y python3-pip
else
    echo "pip is already installed."
fi

# Install required Python packages
echo "Installing required Python packages..."
sudo pip3 install mysql-connector-python psutil configparser

# Verify installation
echo "Verifying installed packages..."
pip3 list | grep -E "mysql-connector-python|psutil|configparser"

echo "Dependencies installed successfully!"
