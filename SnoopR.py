import sqlite3
import folium
import json  # For parsing JSON data from the BLOB
import os
import glob
import datetime
from math import radians, cos, sin, asin, sqrt
from collections import defaultdict

# Function to calculate distance between two GPS coordinates using the haversine formula
def haversine(lon1, lat1, lon2, lat2):
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    # Radius of Earth in miles is approximately 3956
    miles = 3956 * c
    return miles

# Function to sanitize strings to prevent Jinja2 parsing errors
def sanitize_string(s):
    s = str(s)
    for c in ['{', '}', '|', '[', ']', '"', "'", '\\', '<', '>', '%']:
        s = s.replace(c, '')
    return s

# Extract device and GPS data from the Kismet .kismet SQLite3 database
def extract_data_from_kismet(kismet_file):
    conn = sqlite3.connect(kismet_file)
    cursor = conn.cursor()

    # Query for device MAC addresses, GPS data, and device BLOB from the devices table
    query = """
    SELECT devices.devmac, devices.min_lat, devices.min_lon, devices.device
    FROM devices
    WHERE devices.min_lat IS NOT NULL AND devices.min_lon IS NOT NULL;
    """
    cursor.execute(query)
    devices = cursor.fetchall()

    conn.close()

    device_list = []

    for row in devices:
        mac = row[0]
        lat = row[1] if row[1] is not None else 0.0
        lon = row[2] if row[2] is not None else 0.0
        device_blob = row[3]

        ssid_or_name = 'Unknown'
        encryption_or_type = 'Unknown'
        dev_type = 'Unknown'

        try:
            # Parse the JSON data
            device_dict = json.loads(device_blob.decode('utf-8'))

            # Extract device type
            dev_type = device_dict.get('kismet.device.base.type', 'Unknown')

            # Extract device name
            ssid_or_name = device_dict.get('kismet.device.base.name', 'Unknown')

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
                bt_class = device_dict.get('kismet.device.base.bluetooth.device_class', 'Unknown')
                encryption_or_type = bt_class
            else:
                encryption_or_type = 'Unknown'

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            print(f"Error parsing device blob for {mac}: {e}")
            continue  # Skip to the next device

        device_list.append({
            'mac': mac,
            'lat': lat,
            'lon': lon,
            'name': ssid_or_name,
            'type': encryption_or_type,
            'dev_type': dev_type
        })

    return device_list

# Function to extract alerts from the Kismet .kismet SQLite3 database
def extract_alerts_from_kismet(kismet_file):
    conn = sqlite3.connect(kismet_file)
    cursor = conn.cursor()

    # Adjusted query based on actual column names in your database
    query = """
    SELECT ts_sec, ts_usec, phyname, devmac, lat, lon, header, json
    FROM alerts
    WHERE lat IS NOT NULL AND lon IS NOT NULL;
    """
    cursor.execute(query)
    alerts = cursor.fetchall()

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
        alert_time = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')

        # Parse the JSON blob for additional details if needed
        try:
            json_data = json.loads(json_blob.decode('utf-8'))
            alert_text = json_data.get('kismet.alert.description', 'No description')
            alert_key = json_data.get('kismet.alert.name', header or 'Unknown alert')
        except (json.JSONDecodeError, AttributeError, TypeError, ValueError) as e:
            print(f"Error parsing alert JSON for alert at {alert_time}: {e}")
            alert_text = 'No description'
            alert_key = header or 'Unknown alert'

        alert_list.append({
            'timestamp': alert_time,
            'alert_key': alert_key,
            'alert_text': alert_text,
            'device_mac': devmac or 'Unknown',
            'lat': lat,
            'lon': lon
        })

    return alert_list

# Function to detect devices seen at multiple locations (SnoopR functionality)
def detect_snoopers(device_data, distance_threshold=0.05):  # Distance in miles
    snoopers = []

    # Group devices by MAC address
    device_locations = defaultdict(list)
    for device in device_data:
        mac = device['mac']
        lat = device['lat']
        lon = device['lon']
        device_locations[mac].append((lat, lon))

    # Detect devices by checking if they moved more than the threshold
    for mac, locations in device_locations.items():
        if len(locations) > 1:
            first_location = locations[0]
            for other_location in locations[1:]:
                distance_moved = haversine(first_location[1], first_location[0], other_location[1], other_location[0])
                if distance_moved > distance_threshold:
                    # Retrieve the device info
                    for device in device_data:
                        if device['mac'] == mac:
                            snoopers.append(device)
                    break

    return snoopers  # Return all detected devices

# Function to map all devices, including snoopers and alerts
def visualize_devices_snoopers_and_alerts(device_data, snoopers, alerts, output_map_file="SnoopR_Map.html"):
    if device_data or alerts:
        # Filter out devices with zero coordinates
        device_data = [d for d in device_data if d['lat'] != 0.0 and d['lon'] != 0.0]
        alerts = [a for a in alerts if a['lat'] != 0.0 and a['lon'] != 0.0]

        # Use the first valid device or alert location as the map center
        if device_data:
            center_lat = device_data[0]['lat']
            center_lon = device_data[0]['lon']
        elif alerts:
            center_lat = alerts[0]['lat']
            center_lon = alerts[0]['lon']
        else:
            print("No valid coordinates to display on the map.")
            return

        # Create the map
        device_map = folium.Map(location=(center_lat, center_lon), zoom_start=15, tiles="OpenStreetMap")

        # Add all devices to the map
        for device in device_data:
            mac = sanitize_string(device['mac']) or 'Unknown'
            lat = device['lat']
            lon = device['lon']
            name = sanitize_string(device['name']) or 'Unknown'
            dev_type = sanitize_string(device['dev_type']) or 'Unknown'
            type_info = sanitize_string(device['type']) or 'Unknown'
            popup_info = (
                f"MAC: {mac}<br>"
                f"Name/SSID: {name}<br>"
                f"Type/Encryption: {type_info}<br>"
                f"Device Type: {dev_type}<br>"
                f"Location: {lat}, {lon}"
            )

            # Use folium.Popup with parse_html=False to avoid Jinja2 parsing
            folium.Marker(
                location=(lat, lon),
                popup=folium.Popup(popup_info, parse_html=False, max_width=300),
                icon=folium.Icon(color='blue', icon='signal', prefix='fa')
            ).add_to(device_map)

        # Highlight detected snoopers differently
        for snooper in snoopers:
            if snooper['lat'] == 0.0 and snooper['lon'] == 0.0:
                continue  # Skip devices with zero coordinates
            mac = sanitize_string(snooper['mac']) or 'Unknown'
            lat = snooper['lat']
            lon = snooper['lon']
            name = sanitize_string(snooper['name']) or 'Unknown'
            dev_type = sanitize_string(snooper['dev_type']) or 'Unknown'
            type_info = sanitize_string(snooper['type']) or 'Unknown'
            popup_info = (
                f"<b>SnoopR Detected!</b><br>"
                f"MAC: {mac}<br>"
                f"Name/SSID: {name}<br>"
                f"Type/Encryption: {type_info}<br>"
                f"Device Type: {dev_type}<br>"
                f"Location: {lat}, {lon}"
            )

            folium.Marker(
                location=(lat, lon),
                popup=folium.Popup(popup_info, parse_html=False, max_width=300),
                icon=folium.Icon(color='red', icon='exclamation-triangle', prefix='fa')
            ).add_to(device_map)

        # Add alerts to the map
        for alert in alerts:
            lat = alert['lat']
            lon = alert['lon']
            alert_key = sanitize_string(alert['alert_key']) or 'Unknown'
            alert_text = sanitize_string(alert['alert_text']) or 'No description'
            device_mac = sanitize_string(alert['device_mac']) or 'Unknown'
            timestamp = alert['timestamp']

            popup_info = (
                f"<b>Wi-Fi Attack Alert!</b><br>"
                f"Timestamp: {timestamp}<br>"
                f"Alert Type: {alert_key}<br>"
                f"Details: {alert_text}<br>"
                f"Associated Device MAC: {device_mac}<br>"
                f"Location: {lat}, {lon}"
            )

            folium.Marker(
                location=(lat, lon),
                popup=folium.Popup(popup_info, parse_html=False, max_width=300),
                icon=folium.Icon(color='orange', icon='bolt', prefix='fa')
            ).add_to(device_map)

        # Save the map to an HTML file
        device_map.save(output_map_file)
        print(f"Map saved to {output_map_file}")
    else:
        print("No devices or alerts detected.")

# Function to find the most recent .kismet file
def find_most_recent_kismet_file(directory='.'):
    # Find all .kismet files in the specified directory
    kismet_files = glob.glob(os.path.join(directory, '*.kismet'))

    if not kismet_files:
        print("No .kismet files found in the directory.")
        return None

    # Get the most recently modified file
    latest_file = max(kismet_files, key=os.path.getmtime)
    return latest_file

# Example usage
if __name__ == "__main__":
    # Find the most recent .kismet file
    kismet_file = find_most_recent_kismet_file()

    if kismet_file:
        print(f"Using Kismet file: {kismet_file}")

        # Extract Wi-Fi and Bluetooth device data from the Kismet database
        device_data = extract_data_from_kismet(kismet_file)

        # Print the raw device data to inspect the information
        for device in device_data:
            print(device)

        # Detect devices seen across multiple locations
        snoopers = detect_snoopers(device_data)

        # Extract alerts from the Kismet database
        alerts = extract_alerts_from_kismet(kismet_file)

        # Print the alerts to inspect the information
        for alert in alerts:
            print(alert)

        # Visualize all devices, snoopers, and alerts
        visualize_devices_snoopers_and_alerts(device_data, snoopers, alerts)
    else:
        print("No Kismet database file to process.")
