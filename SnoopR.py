#!/usr/bin/env python3
"""
SnoopR.py

A script to extract device information from a Kismet SQLite database,
detect snoopers based on movement, process alerts, and visualize the data
on an interactive Folium map.

This version includes updates to:
- Include planes (ADS-B devices) in the mapping.
- Correctly extract alerts and parse location data from the JSON field.
- Adjust the map center to the first valid device or alert location.
- Map alerts even if they have no latitude and longitude, placing them next to the first mapped device seen before the alert's timestamp.
- **Extract and display the alert type in the map popups.**
- Improve device data extraction and error handling.
- Simplify the visualization logic.

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
import json
import os
import glob
import datetime
from math import radians, cos, sin, asin, sqrt
from collections import defaultdict
import logging
import argparse
from folium.plugins import MarkerCluster

# ===========================
# Configuration and Mapping
# ===========================

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detailed logs
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("snoopr.log"),
        logging.StreamHandler()
    ]
)

# List of known drone SSIDs or MAC address prefixes (OUIs)
known_drone_ssids = [
    "DJI-Mavic", "DJI-Avata", "DJI-Thermal", "DJI", "Brinc-Lemur", "Autel-Evo", "DJI-Matrice"
]

# Known Drone MAC Address Prefixes (OUIs)
known_drone_mac_prefixes = [
    "60:60:1f", "90:3a:e6", "ac:7b:a1", "dc:a6:32", "00:1e:c0", "18:18:9f", "68:ad:2f"
]

# Mapping of device types to Folium icons and colors (all keys are lowercase)
DEVICE_TYPE_MAPPING = {
    'wi-fi ap': {'icon': 'wifi', 'color': 'blue', 'popup': 'Wi-Fi Access Point'},
    'wi-fi client': {'icon': 'user', 'color': 'lightblue', 'popup': 'Wi-Fi Client'},
    'btle': {'icon': 'bluetooth', 'color': 'green', 'popup': 'Bluetooth LE Device'},
    'br/edr': {'icon': 'bluetooth', 'color': 'darkgreen', 'popup': 'Bluetooth Classic Device'},
    'wi-fi bridged': {'icon': 'exchange-alt', 'color': 'orange', 'popup': 'Wi-Fi Bridged Device'},
    'wi-fi wds ap': {'icon': 'wifi', 'color': 'cadetblue', 'popup': 'Wi-Fi WDS Access Point'},
    'wi-fi ad-hoc': {'icon': 'users', 'color': 'purple', 'popup': 'Wi-Fi Ad-Hoc Network'},
    'wi-fi wds': {'icon': 'wifi', 'color': 'lightblue', 'popup': 'Wi-Fi WDS Device'},
    'wi-fi device': {'icon': 'wifi', 'color': 'gray', 'popup': 'Wi-Fi Device'},
    'tpms': {'icon': 'car', 'color': 'purple', 'popup': 'Tire Pressure Monitoring System'},
    'airplane': {'icon': 'plane', 'color': 'blue', 'popup': 'Airplane'},
    'ads-b': {'icon': 'plane', 'color': 'blue', 'popup': 'ADS-B Device'},
    'unknown': {'icon': 'question-circle', 'color': 'darkgray', 'popup': 'Unknown Device'}
}

# ===========================
# Helper Functions
# ===========================

def parse_arguments():
    """
    Parse command-line arguments.

    Returns:
        args: Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Visualize Kismet Devices on a Folium Map")
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
        '--movement-threshold',
        type=float,
        default=0.05,
        help='Threshold distance in miles to detect device movement (default: 0.05 miles)'
    )
    return parser.parse_args()

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points on the Earth (specified in decimal degrees).
    Returns distance in miles.
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
    Sanitize strings to prevent Jinja2 parsing errors.

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

def is_drone(ssid, mac_address):
    """
    Detect if a device is a known drone by checking SSID or MAC address prefix.

    Parameters:
        ssid (str): SSID or name of the device.
        mac_address (str): MAC address of the device.

    Returns:
        bool: True if device is a known drone, False otherwise.
    """
    if ssid and any(drone_ssid in ssid for drone_ssid in known_drone_ssids):
        return True
    mac_prefix = mac_address[:8].lower()  # First 3 octets
    if any(drone_mac_prefix in mac_prefix for drone_mac_prefix in known_drone_mac_prefixes):
        return True
    return False

def is_valid_lat_lon(lat, lon):
    """
    Validate latitude and longitude values.

    Parameters:
        lat (float): Latitude value.
        lon (float): Longitude value.

    Returns:
        bool: True if valid, False otherwise.
    """
    try:
        lat = float(lat)
        lon = float(lon)
        return (
            -90 <= lat <= 90 and
            -180 <= lon <= 180 and
            not (lat == 0.0 and lon == 0.0)
        )
    except (ValueError, TypeError):
        return False

# ===========================
# Data Extraction Functions
# ===========================

def extract_device_detections(kismet_file):
    """
    Extract device detections from the Kismet SQLite database.

    Parameters:
        kismet_file (str): Path to the Kismet SQLite database file.

    Returns:
        dict: Dictionary with MAC addresses as keys and lists of detection dictionaries as values.
    """
    conn = sqlite3.connect(kismet_file)
    cursor = conn.cursor()

    # Fetch all device detections with timestamps and location data
    query = """
    SELECT devmac, type, device, min_lat, min_lon, last_time
    FROM devices
    WHERE min_lat IS NOT NULL AND min_lon IS NOT NULL
    ORDER BY last_time ASC;
    """
    try:
        cursor.execute(query)
        devices = cursor.fetchall()
    except sqlite3.Error as e:
        logging.error(f"SQLite error while fetching devices: {e}")
        conn.close()
        return {}

    conn.close()

    device_detections = defaultdict(list)
    device_types = set()
    device_type_counts = defaultdict(int)

    for device in devices:
        devmac, dev_type, device_blob, min_lat, min_lon, last_time = device

        # Handle decoding the device blob
        if device_blob:
            try:
                if isinstance(device_blob, bytes):
                    device_dict = json.loads(device_blob.decode('utf-8', errors='ignore'))
                elif isinstance(device_blob, str):
                    device_dict = json.loads(device_blob)
                else:
                    device_dict = {}
            except (json.JSONDecodeError, AttributeError, TypeError, ValueError) as e:
                logging.error(f"Error parsing JSON for device {devmac}: {e}")
                device_dict = {}
        else:
            device_dict = {}

        device_type = sanitize_string(dev_type).lower() if dev_type else 'unknown'

        # Include ADS-B devices to map planes
        # No longer excluding 'airplane' or 'ads-b' device types

        # Convert timestamp
        try:
            last_seen_time = datetime.datetime.fromtimestamp(last_time).strftime('%Y-%m-%d %H:%M:%S') if last_time else 'Unknown'
        except (OSError, OverflowError, ValueError) as e:
            logging.error(f"Invalid timestamp {last_time} for device {devmac}: {e}")
            last_seen_time = 'Invalid Timestamp'

        mac = sanitize_string(devmac).lower() if devmac else 'unknown'

        lat_valid = is_valid_lat_lon(min_lat, min_lon)
        lon_valid = is_valid_lat_lon(min_lat, min_lon)

        # Skip devices with invalid coordinates
        if not lat_valid or not lon_valid:
            logging.debug(f"Skipping device {mac} due to invalid coordinates.")
            continue

        detection = {
            'mac': mac,
            'device_type': device_type,
            'name': sanitize_string(device_dict.get('kismet.device.base.commonname', 'Unknown')),
            'encryption': sanitize_string(device_dict.get('kismet.device.base.crypt', 'Unknown')),
            'lat': float(min_lat),
            'lon': float(min_lon),
            'last_seen_time': last_seen_time,
            'last_time': last_time if last_time else None,
            'drone_detected': is_drone(
                sanitize_string(device_dict.get('kismet.device.base.commonname', 'Unknown')),
                mac
            )
        }

        device_detections[mac].append(detection)
        device_types.add(device_type)
        device_type_counts[device_type] += 1

    logging.info(f"Extracted detections for {len(device_detections)} devices from the database.")
    logging.info(f"Device Types Found: {device_types}")
    logging.info(f"Device Type Counts: {dict(device_type_counts)}")
    return device_detections

def detect_snoopers(device_detections, movement_threshold=0.05):
    """
    Detect potential snoopers based on device movement.

    Parameters:
        device_detections (dict): Dictionary with MAC addresses as keys and lists of detection dictionaries as values.
        movement_threshold (float): Distance in miles to consider a device as a snooper.

    Returns:
        List[dict]: List of snooper device dictionaries.
    """
    snoopers = []

    for mac, detections in device_detections.items():
        if len(detections) < 2:
            continue  # Need at least two detections to calculate movement

        detections = sorted(detections, key=lambda x: x['last_time'] or 0)
        total_distance = 0
        for i in range(1, len(detections)):
            lat1, lon1 = detections[i-1]['lat'], detections[i-1]['lon']
            lat2, lon2 = detections[i]['lat'], detections[i]['lon']
            if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
                continue  # Skip if coordinates are invalid
            distance = haversine(lon1, lat1, lon2, lat2)
            total_distance += distance
            if distance >= movement_threshold:
                snooper = {
                    'mac': mac,
                    'detections': detections,
                    'total_distance': total_distance
                }
                snoopers.append(snooper)
                logging.info(f"Snooper detected: {mac}, moved {distance:.2f} miles.")
                break  # Stop after detecting movement beyond threshold

    logging.info(f"Detected {len(snoopers)} snoopers based on movement threshold {movement_threshold} miles.")
    return snoopers

def extract_alerts_from_kismet(kismet_file):
    """
    Extract alerts from the Kismet SQLite database.

    Parameters:
        kismet_file (str): Path to the Kismet SQLite database file.

    Returns:
        List[dict]: List of alert dictionaries.
    """
    conn = sqlite3.connect(kismet_file)
    cursor = conn.cursor()

    # Adjusted query to select only existing columns
    query = """
    SELECT devmac, json, ts_sec
    FROM alerts;
    """
    try:
        cursor.execute(query)
        alerts = cursor.fetchall()
    except sqlite3.Error as e:
        logging.error(f"SQLite error while fetching alerts: {e}")
        conn.close()
        return []

    conn.close()

    alert_list = []

    for alert in alerts:
        devmac, alert_blob, ts_sec = alert
        try:
            alert_time = datetime.datetime.fromtimestamp(ts_sec) if ts_sec else None
            alert_time_str = alert_time.strftime('%Y-%m-%d %H:%M:%S') if alert_time else 'Unknown'
        except (OSError, OverflowError, ValueError):
            alert_time_str = f"{ts_sec}"
            alert_time = None

        # Parse the JSON blob to extract message, alert type, and location
        message = 'No message'
        alert_type = 'Unknown'
        lat = None
        lon = None

        if alert_blob:
            try:
                if isinstance(alert_blob, bytes):
                    alert_dict = json.loads(alert_blob.decode('utf-8', errors='ignore'))
                elif isinstance(alert_blob, str):
                    alert_dict = json.loads(alert_blob)
                else:
                    alert_dict = {}
                
                # Updated extraction keys based on debug logs
                message = alert_dict.get('kismet.alert.text', 'No message')
                alert_type = alert_dict.get('kismet.alert.class', 'Unknown')

                # Updated location extraction
                location = alert_dict.get('kismet.common.location', {})
                geopoint = location.get('kismet.common.location.geopoint')
                
                if geopoint and isinstance(geopoint, list) and len(geopoint) == 2:
                    lon, lat = geopoint  # Kismet uses [longitude, latitude]
                else:
                    lat = location.get('kismet.common.location.lat')
                    lon = location.get('kismet.common.location.lon')
                
                # Convert to float if possible
                lat = float(lat) if lat else None
                lon = float(lon) if lon else None

            except (json.JSONDecodeError, AttributeError, TypeError, ValueError) as e:
                logging.error(f"Error parsing JSON for alert from {devmac}: {e}")
                continue  # Skip alerts with invalid JSON

        # Create the alert entry
        alert_entry = {
            'mac': sanitize_string(devmac).lower() if devmac else 'unknown',
            'message': sanitize_string(message),
            'alert_type': sanitize_string(alert_type),
            'lat': lat,
            'lon': lon,
            'time': alert_time,
            'time_str': alert_time_str
        }

        alert_list.append(alert_entry)

    logging.info(f"Extracted {len(alert_list)} alerts from the database.")
    return alert_list

# ===========================
# Visualization Function
# ===========================

def visualize_devices_snoopers_and_alerts(device_detections, snoopers, alerts, output_map_file="SnoopR_Map.html"):
    """
    Visualizes devices, snoopers, and alerts on a Folium map.

    Parameters:
    - device_detections (dict): Dictionary of device detections.
    - snoopers (List[dict]): List of snooper device dictionaries.
    - alerts (List[dict]): List of alert dictionaries.
    - output_map_file (str): Filename for the output HTML map.
    """
    if not device_detections and not snoopers and not alerts:
        logging.info("No devices, snoopers, or alerts to display.")
        return

    # Flatten device detections for mapping
    device_data = []
    for detections in device_detections.values():
        device_data.extend(detections)

    # Filter out devices with invalid coordinates
    device_data = [
        d for d in device_data
        if is_valid_lat_lon(d['lat'], d['lon'])
    ]
    # Sort devices by last_time for chronological order
    device_data = sorted(device_data, key=lambda x: x['last_time'] or 0)

    # Filter out snoopers with invalid coordinates
    snoopers = [
        s for s in snoopers
        if all(is_valid_lat_lon(d['lat'], d['lon']) for d in s['detections'])
    ]
    # Alerts will be handled even if they have invalid coordinates

    if not device_data and not snoopers and not alerts:
        logging.info("No valid devices, snoopers, or alerts with geolocation data to display.")
        return

    # Determine the center of the map
    center_lat, center_lon = None, None

    # Try to find the first valid GPS location from devices, snoopers, or alerts
    all_locations = []

    # Collect all valid locations
    for d in device_data:
        all_locations.append((d['lat'], d['lon'], d['last_time']))

    for s in snoopers:
        for d in s['detections']:
            all_locations.append((d['lat'], d['lon'], d['last_time']))

    for a in alerts:
        if is_valid_lat_lon(a['lat'], a['lon']):
            all_locations.append((float(a['lat']), float(a['lon']), a['time']))

    if all_locations:
        # Use the first valid location
        all_locations.sort(key=lambda x: x[2] or 0)
        center_lat, center_lon, _ = all_locations[0]
    else:
        # Default to a predefined location if no valid GPS data is available
        center_lat, center_lon = -80.56899, -30.08869  # Antarctica (Flying saucer coordinates)

    # Initialize the Folium map
    device_map = folium.Map(location=(center_lat, center_lon), zoom_start=15, tiles="OpenStreetMap")
    device_marker_cluster = MarkerCluster(name='Devices').add_to(device_map)
    snooper_marker_cluster = MarkerCluster(name='Snoopers').add_to(device_map)
    alert_marker_cluster = MarkerCluster(name='Alerts').add_to(device_map)

    # Add device markers
    for device in device_data:
        mac = device['mac']
        lat = device['lat']
        lon = device['lon']
        name = device['name']
        dev_type = device['device_type']
        encryption = device['encryption']
        last_seen = device['last_seen_time']
        drone_detected = device['drone_detected']

        # Get mapping details
        mapping = DEVICE_TYPE_MAPPING.get(dev_type, DEVICE_TYPE_MAPPING['unknown'])
        icon_color = mapping['color']
        icon_symbol = mapping['icon']
        popup_title = mapping['popup']

        # Modify icon and popup if a drone is detected
        if drone_detected:
            icon_color = 'red'
            icon_symbol = 'plane'  # Use a valid Font Awesome icon
            popup_title = 'Drone Detected!'

        # Customize the popup information
        popup_info = (
            f"<b>{popup_title}</b><br>"
            f"MAC: {mac}<br>"
            f"Name/SSID: {name}<br>"
            f"Encryption: {encryption}<br>"
            f"Device Type: {dev_type}<br>"
            f"Location: {lat}, {lon}<br>"
            f"Last Seen: {last_seen}"
        )

        # Log the icon assignment for debugging
        logging.debug(f"Device {mac}: Type={dev_type}, Icon={icon_symbol}, Color={icon_color}")

        # Add the marker to the device cluster
        folium.Marker(
            location=(lat, lon),
            popup=folium.Popup(popup_info, parse_html=True, max_width=300),
            icon=folium.Icon(color=icon_color, icon=icon_symbol, prefix='fa')
        ).add_to(device_marker_cluster)

    # Add snooper markers and paths
    for snooper in snoopers:
        mac = snooper['mac']
        detections = snooper['detections']
        total_distance = snooper['total_distance']

        # Sort detections by time
        detections = sorted(detections, key=lambda x: x['last_time'] or 0)

        # Add markers for each detection
        for i, detection in enumerate(detections):
            lat = detection['lat']
            lon = detection['lon']
            last_seen = detection['last_seen_time']

            popup_info = (
                f"<b>Snooper</b><br>"
                f"MAC: {mac}<br>"
                f"Last Seen: {last_seen}<br>"
                f"Total Movement: {total_distance:.2f} miles"
            )

            folium.CircleMarker(
                location=(lat, lon),
                radius=5,
                color='orange',
                fill=True,
                fill_color='orange',
                fill_opacity=0.7,
                popup=folium.Popup(popup_info, parse_html=True, max_width=300)
            ).add_to(snooper_marker_cluster)

            # Draw lines between detections to show movement
            if i > 0:
                prev_detection = detections[i - 1]
                prev_lat = prev_detection['lat']
                prev_lon = prev_detection['lon']
                folium.PolyLine(
                    locations=[(prev_lat, prev_lon), (lat, lon)],
                    color='orange',
                    weight=2,
                    opacity=0.6
                ).add_to(device_map)

    # Add alert markers
    for alert in alerts:
        mac = alert['mac']
        lat = alert['lat']
        lon = alert['lon']
        message = alert['message']
        alert_type = alert.get('alert_type', 'Unknown')
        alert_time = alert['time']
        alert_time_str = alert['time_str']

        # If lat/lon are invalid, place the alert near the first mapped device before the alert's timestamp
        if not is_valid_lat_lon(lat, lon):
            # Find the first device seen before the alert's timestamp
            if alert_time and device_data:
                devices_before_alert = [d for d in device_data if d['last_time'] and d['last_time'] <= alert_time.timestamp()]
                if devices_before_alert:
                    # Use the last device before the alert time
                    reference_device = devices_before_alert[-1]
                    lat = reference_device['lat'] + 0.0005  # Slight offset to avoid overlap
                    lon = reference_device['lon'] + 0.0005
                else:
                    # No devices before the alert time; use the first device
                    reference_device = device_data[0]
                    lat = reference_device['lat'] + 0.0005
                    lon = reference_device['lon'] + 0.0005
            else:
                # No devices or no alert time; place at the center
                lat = center_lat
                lon = center_lon

        popup_info = (
            f"<b>Alert: {alert_type}</b><br>"
            f"MAC: {mac}<br>"
            f"Message: {message}<br>"
            f"Time: {alert_time_str}"
        )

        # Log alert information for debugging
        logging.debug(f"Alert from {mac}: {alert_type} - {message} at {alert_time_str}")

        folium.Marker(
            location=(lat, lon),
            popup=folium.Popup(popup_info, parse_html=True, max_width=300),
            icon=folium.Icon(color='black', icon='exclamation-triangle', prefix='fa')
        ).add_to(alert_marker_cluster)

    # Add layer control to toggle visibility
    folium.LayerControl().add_to(device_map)

    # Ensure the output directory exists
    output_dir = os.path.dirname(output_map_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Save the map to an HTML file
    device_map.save(output_map_file)
    logging.info(f"Map saved to {output_map_file}")

# ===========================
# Utility Functions
# ===========================

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
    return latest_file

# ===========================
# Main Execution Flow
# ===========================

def main():
    # Parse command-line arguments
    args = parse_arguments()

    # Determine which Kismet file to use
    if args.db_path:
        kismet_file = args.db_path
        if not os.path.exists(kismet_file):
            logging.error(f"Specified database file '{kismet_file}' does not exist.")
            return
    else:
        # Automatically find the most recent .kismet file
        kismet_file = find_most_recent_kismet_file()
        if not kismet_file:
            logging.error("No Kismet database file to process.")
            return

    logging.info(f"Using Kismet file: {kismet_file}")

    # Extract device detections
    device_detections = extract_device_detections(kismet_file)

    if not device_detections:
        logging.warning("No device data extracted.")
    else:
        logging.info("Extracted Device Detections:")
        for mac, detections in device_detections.items():
            logging.info(f"Device {mac}: {len(detections)} detections")

    # Detect snoopers based on movement
    movement_threshold = args.movement_threshold
    snoopers = detect_snoopers(device_detections, movement_threshold)
    if snoopers:
        logging.info("\nDetected Snoopers:")
        for snooper in snoopers:
            logging.info(f"Snooper {snooper['mac']}: Moved {snooper['total_distance']:.2f} miles")
    else:
        logging.info("No snoopers detected.")

    # Extract alerts
    alerts = extract_alerts_from_kismet(kismet_file)
    if alerts:
        logging.info("\nExtracted Alerts:")
        for alert in alerts:
            logging.info(alert)
    else:
        logging.info("No alerts extracted.")

    # Visualize devices, snoopers, and alerts on the map
    visualize_devices_snoopers_and_alerts(device_detections, snoopers, alerts, output_map_file=args.output_map)

if __name__ == "__main__":
    main()

