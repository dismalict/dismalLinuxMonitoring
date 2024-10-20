#!/bin/bash

# Update package list
echo "Updating package list..."
sudo apt update

# Check if Python3 is installed
echo "Checking if Python3 is installed..."
if ! command -v python3 &> /dev/null
then
    echo "Python3 not found, installing Python3..."
    sudo apt install -y python3
else
    echo "Python3 is already installed."
fi

# Check if pip is installed
echo "Checking if pip is installed..."
if ! command -v pip3 &> /dev/null
then
    echo "pip3 not found, installing pip3..."
    sudo apt install -y python3-pip
else
    echo "pip3 is already installed."
fi

# Install required Python packages
echo "Installing required Python packages..."
sudo pip3 install mysql-connector-python psutil configparser requests glances

# Verify installation
echo "Verifying installed packages..."
pip3 list | grep -E "mysql-connector-python|psutil|configparser|requests|glances"

echo "Dependencies installed successfully!"
