import requests
import mysql.connector
import configparser
import time
import socket
import os
import logging

# Set the base directory to "backEnd"
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backEnd")

# Paths to config and log files
CONFIG_FILE = os.path.join(BASE_DIR, 'config.ini')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'metrics_error.log')

# Glances API endpoint
GLANCES_API_URL = 'http://localhost:61208/api/3/all'

# Get the machine's hostname
hostname = socket.gethostname()

# Ensure the logs directory exists
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)  # Create logs directory if it doesn't exist

# Setup the logging configuration
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Function to read database config from the config.ini in backEnd folder
def read_db_config(filename=CONFIG_FILE, section='mysql'):
    parser = configparser.ConfigParser()
    parser.read(filename)
    
    db_config = {}
    if parser.has_section(section):
        items = parser.items(section)
        for item in items:
            db_config[item[0]] = item[1]
    else:
        raise Exception(f'{section} not found in {filename}')
    
    return db_config

# Function to create database connection
def create_connection():
    db_config = read_db_config()
    try:
        connection = mysql.connector.connect(**db_config)
        print("Connected to the database.")
        return connection
    except mysql.connector.Error as e:
        logging.error(f"Error connecting to MySQL: {e}")
        print(f"Error connecting to the database: {e}")
        return None

# Function to create the necessary tables if they do not exist
def create_tables():
    connection = create_connection()
    if connection is None:
        return
    
    cursor = connection.cursor()

    # Long-term storage table
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {hostname}_longterm (
        id INT AUTO_INCREMENT PRIMARY KEY,
        cpu_total FLOAT,
        memory_percent FLOAT,
        swap_percent FLOAT,
        disk_usage FLOAT,
        disk_io_read INT,
        disk_io_write INT,
        network_tx INT,
        network_rx INT,
        cpu_temp FLOAT,
        gpu_usage FLOAT,
        cpu_freq INT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Limited table (50 most recent rows)
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {hostname}_limited (
        id INT AUTO_INCREMENT PRIMARY KEY,
        cpu_total FLOAT,
        memory_percent FLOAT,
        swap_percent FLOAT,
        disk_usage FLOAT,
        disk_io_read INT,
        disk_io_write INT,
        network_tx INT,
        network_rx INT,
        cpu_temp FLOAT,
        gpu_usage FLOAT,
        cpu_freq INT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    connection.commit()
    cursor.close()
    connection.close()

    print(f"Tables {hostname}_longterm and {hostname}_limited created (if they didn't already exist).")

# Function to gather metrics from the Glances API
def get_glances_metrics():
    try:
        response = requests.get(GLANCES_API_URL)
        data = response.json()
        print("Fetched metrics from Glances API.")
        return data
    except Exception as e:
        logging.error(f"Error fetching data from Glances API: {e}")
        print(f"Error fetching data from Glances API: {e}")
        return None

# Function to insert data into long-term and limited tables
def insert_data(cpu_total, memory_percent, swap_percent, disk_usage, disk_io_read, disk_io_write, network_tx, network_rx, cpu_temp, gpu_usage, cpu_freq):
    connection = create_connection()
    if connection is None:
        return
    
    cursor = connection.cursor()

    # Insert into long-term table
    try:
        cursor.execute(f"""
        INSERT INTO {hostname}_longterm (cpu_total, memory_percent, swap_percent, disk_usage, disk_io_read, disk_io_write, network_tx, network_rx, cpu_temp, gpu_usage, cpu_freq)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (cpu_total, memory_percent, swap_percent, disk_usage, disk_io_read, disk_io_write, network_tx, network_rx, cpu_temp, gpu_usage, cpu_freq))

        # Insert into limited table (and ensure only 50 rows exist)
        cursor.execute(f"""
        INSERT INTO {hostname}_limited (cpu_total, memory_percent, swap_percent, disk_usage, disk_io_read, disk_io_write, network_tx, network_rx, cpu_temp, gpu_usage, cpu_freq)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (cpu_total, memory_percent, swap_percent, disk_usage, disk_io_read, disk_io_write, network_tx, network_rx, cpu_temp, gpu_usage, cpu_freq))

        # Limit to 50 rows in the limited table
        cursor.execute(f"""
        DELETE FROM {hostname}_limited
        WHERE id NOT IN (
            SELECT id FROM (SELECT id FROM {hostname}_limited ORDER BY id DESC LIMIT 50) as t
        );
        """)

        connection.commit()
        print(f"Inserted data into {hostname}_longterm and {hostname}_limited tables.")
    except mysql.connector.Error as e:
        logging.error(f"Error inserting data into MySQL: {e}")
        print(f"Error inserting data into MySQL: {e}")
    finally:
        cursor.close()
        connection.close()

# Main function to periodically collect and insert data
def main():
    create_tables()

    while True:
        metrics = get_glances_metrics()

        if metrics:
            cpu_total = metrics['cpu']['total']
            memory_percent = metrics['mem']['percent']
            swap_percent = metrics['swap']['percent']
            disk_usage = metrics['fs'][0]['percent']  # Disk usage for the first filesystem
            disk_io_read = metrics['diskio'][0]['read_bytes']
            disk_io_write = metrics['diskio'][0]['write_bytes']
            network_tx = metrics['network']['tx']
            network_rx = metrics['network']['rx']

            # Additional data points: CPU temperature, GPU usage, CPU frequency
            sensors = metrics.get('sensors', [])
            cpu_temp = next((s['value'] for s in sensors if 'cpu' in s['label'].lower()), None) or 0.0
            gpu_usage = metrics.get('gpu', {}).get('gpu_util', 0.0)
            cpu_freq = metrics.get('cpu', {}).get('current', 0)

            # Insert the data into both tables
            insert_data(cpu_total, memory_percent, swap_percent, disk_usage, disk_io_read, disk_io_write, network_tx, network_rx, cpu_temp, gpu_usage, cpu_freq)
        
        time.sleep(2)  # Collect data every 2 seconds

if __name__ == '__main__':
    main()
