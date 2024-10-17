#!/usr/bin/env python3
"""
SnoopR.py

A script to extract device information from a Kismet SQLite database,
detect snoopers based on movement, process alerts, and visualize the data
on an interactive Folium map.

Enhancements:
- Increased movement threshold to reduce false positives.
- Implemented time-based filtering for movement detection.
- Aggregated movement analysis.
- Eliminated duplicate snooper entries.
- Enhanced data validation and cleaning.
- Added detailed logging for better troubleshooting.

Usage:
    python3 SnoopR.py --db-path ./Kismet-YYYYMMDD-HH-MM-SS.kismet --output-map SnoopR_Map.html
    python3 SnoopR.py --output-map ./Maps/SnoopR_Map.html  # Automatically selects the latest .kismet file

Requirements:
    - Python 3.x
    - folium
    - sqlite3
    - json
    - argparse
    - logging
    - math
    - collections
"""

import sqlite3
import folium
import json  # For parsing JSON data from the BLOB
import os
import glob
import datetime
from math import radians, cos, sin, asin, sqrt
from collections import defaultdict
import argparse
import logging

# ===========================
# Configuration and Constants
# ===========================

# Distance threshold in miles to detect movement
DISTANCE_THRESHOLD = 0.5  # Increased from 0.05 to 0.5 miles

# Time threshold in seconds to consider movement
TIME_THRESHOLD = 3600  # 1 hour

# Logging configuration
LOG_FILE = "snoopr.log"
LOG_LEVEL = logging.DEBUG  # Set to DEBUG for detailed logs

# ===========================
# Helper Functions
# ===========================

def setup_logging():
    """
    Configure logging settings.
    """
    logging.basicConfig(
        level=LOG_LEVEL,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
    logging.info("Logging initialized.")

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great-circle distance between two points on the Earth.
    Parameters:
        lon1, lat1: Longitude and latitude of point 1 in decimal degrees.
        lon2, lat2: Longitude and latitude of point 2 in decimal degrees.
    Returns:
        Distance in miles.
    """
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # Haversine formula
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * asin(sqrt(a)) 
    miles = 3956 * c
    return miles

def sanitize_string(s):
    """
    Sanitize strings to prevent issues in HTML rendering.
    Parameters:
        s (str): The string to sanitize.
    Returns:
        str: Sanitized string.
    """
    if not s:
        return 'Unknown'
    try:
        s = str(s)
        for c in ['{', '}', '|', '[', ']', '"', "'", '\\', '<', '>', '%']:
            s = s.replace(c, '')
        return s
    except (AttributeError, ValueError):
        return 'Unknown'

def find_most_recent_kismet_file(directory='.'):
    """
    Find the most recently modified .kismet file in the specified directory.
    Parameters:
        directory (str): Directory path to search for .kismet files.
    Returns:
        str or None: Path to the most recent .kismet file or None if none found.
    """
    kismet_files = glob.glob(os.path.join(directory, '*.kismet'))
    if not kismet_files:
        logging.error("No .kismet files found in the directory.")
        return None
    latest_file = max(kismet_files, key=os.path.getmtime)
    logging.info(f"Most recent Kismet file found: {latest_file}")
    return latest_file

# ===========================
# Data Extraction Functions
# ===========================

def extract_data_from_kismet(kismet_file):
    """
    Extract device and GPS data from the Kismet SQLite database.
    Parameters:
        kismet_file (str): Path to the Kismet SQLite database file.
    Returns:
        List[dict]: List of device dictionaries.
    """
    logging.info(f"Connecting to Kismet database: {kismet_file}")
    try:
        conn = sqlite3.connect(kismet_file)
    except sqlite3.Error as e:
        logging.error(f"Failed to connect to the database: {e}")
        return []
    
    cursor = conn.cursor()

    # Query for device MAC addresses, GPS data, and device BLOB from the devices table
    query = """
    SELECT devices.devmac, devices.min_lat, devices.min_lon, devices.device, devices.last_time
    FROM devices
    WHERE devices.min_lat IS NOT NULL AND devices.min_lon IS NOT NULL;
    """
    try:
        cursor.execute(query)
        devices = cursor.fetchall()
        logging.info(f"Fetched {len(devices)} device records from the database.")
    except sqlite3.Error as e:
        logging.error(f"SQLite error while fetching devices: {e}")
        conn.close()
        return []
    
    conn.close()

    device_list = []

    for row in devices:
        mac = row[0]
        lat = row[1] if row[1] is not None else 0.0
        lon = row[2] if row[2] is not None else 0.0
        device_blob = row[3]
        last_time = row[4] if row[4] is not None else 0

        ssid_or_name = 'Unknown'
        encryption_or_type = 'Unknown'
        dev_type = 'Unknown'

        try:
            # Parse the JSON data
            device_dict = json.loads(device_blob.decode('utf-8'))
            
            # Extract device type
            dev_type = sanitize_string(device_dict.get('kismet.device.base.type', 'Unknown'))
            
            # Extract device name
            ssid_or_name = sanitize_string(device_dict.get('kismet.device.base.name', 'Unknown'))
            
            # Extract encryption or type information
            if dev_type in ['Wi-Fi AP', 'Wi-Fi Client', 'Wi-Fi Base Station', 'Wi-Fi Client Device']:
                encryption_data = device_dict.get('kismet.device.base.crypt')
                if not encryption_data:
                    # Try alternative keys for encryption
                    encryption_data = device_dict.get('dot11.device', {}).get('dot11.device.last_beaconed_ssid', {}).get('dot11.ssid.cryptset')
                if isinstance(encryption_data, list):
                    encryption_or_type = ', '.join(encryption_data)
                elif isinstance(encryption_data, str):
                    encryption_or_type = encryption_data
                else:
                    encryption_or_type = 'Unknown'
            elif dev_type in ['Bluetooth', 'Bluetooth LE', 'Bluetooth Low Energy Device']:
                bt_class = sanitize_string(device_dict.get('kismet.device.base.bluetooth.device_class', 'Unknown'))
                encryption_or_type = bt_class
            else:
                encryption_or_type = 'Unknown'

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            logging.error(f"Error parsing device blob for {mac}: {e}")
            continue  # Skip to the next device

        device_list.append({
            'mac': sanitize_string(mac).lower() if mac else 'unknown',
            'lat': lat,
            'lon': lon,
            'name': ssid_or_name,
            'type': encryption_or_type,
            'dev_type': dev_type,
            'last_time': last_time
        })
        logging.debug(f"Device added: {mac}, Type: {dev_type}, Location: ({lat}, {lon})")

    logging.info(f"Extracted {len(device_list)} devices from the database.")
    return device_list

def extract_alerts_from_kismet(kismet_file):
    """
    Extract alerts from the Kismet SQLite database.
    Parameters:
        kismet_file (str): Path to the Kismet SQLite database file.
    Returns:
        List[dict]: List of alert dictionaries.
    """
    logging.info(f"Connecting to Kismet database for alerts: {kismet_file}")
    try:
        conn = sqlite3.connect(kismet_file)
    except sqlite3.Error as e:
        logging.error(f"Failed to connect to the database for alerts: {e}")
        return []
    
    cursor = conn.cursor()

    # Query to select relevant alert data
    query = """
    SELECT ts_sec, ts_usec, phyname, devmac, lat, lon, header, json
    FROM alerts
    WHERE lat IS NOT NULL AND lon IS NOT NULL;
    """
    try:
        cursor.execute(query)
        alerts = cursor.fetchall()
        logging.info(f"Fetched {len(alerts)} alert records from the database.")
    except sqlite3.Error as e:
        logging.error(f"SQLite error while fetching alerts: {e}")
        conn.close()
        return []
    
    conn.close()

    alert_list = []

    for row in alerts:
        ts_sec = row[0]
        ts_usec = row[1]
        phyname = row[2]
        devmac = row[3]
        lat = row[4]
        lon = row[5]
        header = row[6]
        json_blob = row[7]

        # Combine ts_sec and ts_usec to get the full timestamp
        timestamp = ts_sec + ts_usec / 1_000_000

        # Convert timestamp to readable format
        try:
            alert_time = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')
        except (OSError, OverflowError, ValueError):
            alert_time = 'Invalid Timestamp'

        # Parse the JSON blob for additional details if needed
        try:
            json_data = json.loads(json_blob.decode('utf-8'))
            alert_text = sanitize_string(json_data.get('kismet.alert.description', 'No description'))
            alert_key = sanitize_string(json_data.get('kismet.alert.name', header or 'Unknown alert'))
        except (json.JSONDecodeError, AttributeError, TypeError, ValueError) as e:
            logging.error(f"Error parsing alert JSON for alert at {alert_time}: {e}")
            alert_text = 'No description'
            alert_key = sanitize_string(header) if header else 'Unknown alert'

        alert_list.append({
            'timestamp': alert_time,
            'alert_key': alert_key,
            'alert_text': alert_text,
            'device_mac': sanitize_string(devmac).lower() if devmac else 'unknown',
            'lat': lat,
            'lon': lon
        })
        logging.debug(f"Alert added: {alert_key}, Device MAC: {devmac}, Location: ({lat}, {lon})")

    logging.info(f"Extracted {len(alert_list)} alerts from the database.")
    return alert_list

# ===========================
# Snoopers Detection Function
# ===========================

def detect_snoopers(device_data, distance_threshold=DISTANCE_THRESHOLD, time_threshold=TIME_THRESHOLD):
    """
    Detect potential snoopers based on device movement over a specified distance and time.
    Parameters:
        device_data (List[dict]): List of device detection dictionaries.
        distance_threshold (float): Distance in miles to consider a device as a snooper.
        time_threshold (int): Time in seconds to consider movement.
    Returns:
        List[dict]: List of snooper device dictionaries.
    """
    snoopers = []
    identified_snoopers = set()
    device_locations = defaultdict(list)

    # Group devices by MAC address with timestamps
    for device in device_data:
        mac = device['mac']
        lat = device['lat']
        lon = device['lon']
        last_time = device.get('last_time', 0)
        device_locations[mac].append((lat, lon, last_time))

    # Detect devices by checking movement within time threshold
    for mac, locations in device_locations.items():
        if len(locations) > 1 and mac not in identified_snoopers:
            # Sort locations by timestamp
            sorted_locations = sorted(locations, key=lambda x: x[2] or 0)
            first_location = sorted_locations[0]
            for other_location in sorted_locations[1:]:
                time_diff = other_location[2] - first_location[2]
                if time_diff <= time_threshold:
                    distance_moved = haversine(first_location[1], first_location[0], other_location[1], other_location[0])
                    logging.debug(f"Device {mac}: Moved {distance_moved:.2f} miles in {time_diff} seconds.")
                    if distance_moved > distance_threshold:
                        # Retrieve the latest detection
                        latest_detection = max(
                            [d for d in device_data if d['mac'] == mac],
                            key=lambda x: x['last_time'] or 0
                        )
                        snoopers.append(latest_detection)
                        identified_snoopers.add(mac)
                        logging.info(f"Snooper detected: {mac}, moved {distance_moved:.2f} miles in {time_diff} seconds.")
                        break  # Stop after first detection beyond threshold

    logging.info(f"Total snoopers detected: {len(snoopers)} based on movement threshold {distance_threshold} miles and time threshold {time_threshold} seconds.")
    return snoopers

# ===========================
# Visualization Function
# ===========================

def visualize_devices_snoopers_and_alerts(device_data, snoopers, alerts, output_map_file="SnoopR_Map.html"):
    """
    Visualizes devices, snoopers, and alerts on a Folium map.
    Parameters:
        device_data (List[dict]): List of device dictionaries.
        snoopers (List[dict]): List of snooper device dictionaries.
        alerts (List[dict]): List of alert dictionaries.
        output_map_file (str): Filename for the output HTML map.
    """
    if not device_data and not snoopers and not alerts:
        logging.warning("No devices, snoopers, or alerts to display.")
        return

    # Filter out devices with invalid coordinates
    device_data = [d for d in device_data if d['lat'] != 0.0 and d['lon'] != 0.0]
    alerts = [a for a in alerts if a['lat'] != 0.0 and a['lon'] != 0.0]

    logging.info(f"Total valid devices to map: {len(device_data)}")
    logging.info(f"Total snoopers to map: {len(snoopers)}")
    logging.info(f"Total alerts to map: {len(alerts)}")

    # Use the first valid device or alert location as the map center
    if device_data:
        center_lat = device_data[0]['lat']
        center_lon = device_data[0]['lon']
    elif alerts:
        center_lat = alerts[0]['lat']
        center_lon = alerts[0]['lon']
    else:
        logging.warning("No valid coordinates to center the map. Using default location.")
        center_lat, center_lon = 0.0, 0.0  # Default to Equator
    
    # Create the map
    device_map = folium.Map(location=(center_lat, center_lon), zoom_start=15, tiles="OpenStreetMap")
    logging.info(f"Map centered at latitude {center_lat}, longitude {center_lon}.")

    # Add all devices to the map
    for device in device_data:
        mac = device['mac']
        lat = device['lat']
        lon = device['lon']
        name = device['name']
        dev_type = device['dev_type']
        type_info = device['type']
        popup_info = (
            f"MAC: {mac}<br>"
            f"Name/SSID: {name}<br>"
            f"Type/Encryption: {type_info}<br>"
            f"Device Type: {dev_type}<br>"
            f"Location: ({lat}, {lon})"
        )

        folium.Marker(
            location=(lat, lon),
            popup=folium.Popup(popup_info, parse_html=False, max_width=300),
            icon=folium.Icon(color='blue', icon='signal', prefix='fa')
        ).add_to(device_map)
        logging.debug(f"Device marker added for {mac} at ({lat}, {lon}).")

    # Highlight detected snoopers differently
    for snooper in snoopers:
        if snooper['lat'] == 0.0 and snooper['lon'] == 0.0:
            continue  # Skip devices with zero coordinates
        mac = snooper['mac']
        lat = snooper['lat']
        lon = snooper['lon']
        name = snooper['name']
        dev_type = snooper['dev_type']
        type_info = snooper['type']
        popup_info = (
            f"<b>Snooper Detected!</b><br>"
            f"MAC: {mac}<br>"
            f"Name/SSID: {name}<br>"
            f"Type/Encryption: {type_info}<br>"
            f"Device Type: {dev_type}<br>"
            f"Location: ({lat}, {lon})"
        )

        folium.Marker(
            location=(lat, lon),
            popup=folium.Popup(popup_info, parse_html=False, max_width=300),
            icon=folium.Icon(color='red', icon='exclamation-triangle', prefix='fa')
        ).add_to(device_map)
        logging.debug(f"Snooper marker added for {mac} at ({lat}, {lon}).")

    # Add alerts to the map
    for alert in alerts:
        lat = alert['lat']
        lon = alert['lon']
        alert_key = alert['alert_key']
        alert_text = alert['alert_text']
        device_mac = alert['device_mac']
        timestamp = alert['timestamp']

        popup_info = (
            f"<b>Wi-Fi Attack Alert!</b><br>"
            f"Timestamp: {timestamp}<br>"
            f"Alert Type: {alert_key}<br>"
            f"Details: {alert_text}<br>"
            f"Associated Device MAC: {device_mac}<br>"
            f"Location: ({lat}, {lon})"
        )

        folium.Marker(
            location=(lat, lon),
            popup=folium.Popup(popup_info, parse_html=False, max_width=300),
            icon=folium.Icon(color='orange', icon='bolt', prefix='fa')
        ).add_to(device_map)
        logging.debug(f"Alert marker added for {device_mac} at ({lat}, {lon}).")

    # Save the map to an HTML file
    try:
        device_map.save(output_map_file)
        logging.info(f"Map successfully saved to {output_map_file}")
    except Exception as e:
        logging.error(f"Failed to save the map: {e}")

# ===========================
# Main Execution Flow
# ===========================

def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Visualize Kismet Devices on a Folium Map with Snoopers Detection")
    parser.add_argument(
        '--db-path',
        type=str,
        help='Path to the Kismet SQLite database file (e.g., ./Kismet-YYYYMMDD-HH-MM-SS.kismet). If omitted, the script will attempt to find the most recent .kismet file in the current directory.'
    )
    parser.add_argument(
        '--output-map',
        type=str,
        default="SnoopR_Map.html",
        help='Filename for the output HTML map (default: SnoopR_Map.html)'
    )
    parser.add_argument(
        '--distance-threshold',
        type=float,
        default=DISTANCE_THRESHOLD,
        help=f'Distance threshold in miles to detect movement (default: {DISTANCE_THRESHOLD} miles)'
    )
    parser.add_argument(
        '--time-threshold',
        type=int,
        default=TIME_THRESHOLD,
        help=f'Time threshold in seconds to consider movement (default: {TIME_THRESHOLD} seconds)'
    )
    args = parser.parse_args()

    # Initialize logging
    setup_logging()

    # Determine which Kismet file to use
    if args.db_path:
        kismet_file = args.db_path
        if not os.path.exists(kismet_file):
            logging.error(f"Specified database file '{kismet_file}' does not exist.")
            return
        else:
            logging.info(f"Using specified Kismet file: {kismet_file}")
    else:
        # Automatically find the most recent .kismet file
        kismet_file = find_most_recent_kismet_file()
        if not kismet_file:
            logging.error("No Kismet database file to process.")
            return
        else:
            logging.info(f"Using most recent Kismet file: {kismet_file}")

    # Extract device detections
    device_data = extract_data_from_kismet(kismet_file)
    if not device_data:
        logging.warning("No device data extracted.")
    else:
        logging.info(f"Extracted {len(device_data)} devices.")
        # Optionally, print device data for inspection
        # for device in device_data:
        #     print(device)

    # Detect snoopers based on movement
    snoopers = detect_snoopers(
        device_data,
        distance_threshold=args.distance_threshold,
        time_threshold=args.time_threshold
    )
    if snoopers:
        logging.info(f"Detected {len(snoopers)} snoopers:")
        for snooper in snoopers:
            logging.info(f"Snooper MAC: {snooper['mac']}, Location: ({snooper['lat']}, {snooper['lon']}), Last Seen Time: {datetime.datetime.fromtimestamp(snooper['last_time']).strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        logging.info("No snoopers detected.")

    # Extract alerts
    alerts = extract_alerts_from_kismet(kismet_file)
    if not alerts:
        logging.info("No alerts extracted.")
    else:
        logging.info(f"Extracted {len(alerts)} alerts.")
        # Optionally, print alert data for inspection
        # for alert in alerts:
        #     print(alert)

    # Visualize all devices, snoopers, and alerts on the map
    visualize_devices_snoopers_and_alerts(
        device_data=device_data,
        snoopers=snoopers,
        alerts=alerts,
        output_map_file=args.output_map
    )

    logging.info("Script completed successfully.")

if __name__ == "__main__":
    main()
