# SnoopR

SnoopR is a Python-based tool designed for network security professionals and enthusiasts. It detects Wi-Fi and Bluetooth devices captured by Kismet and also utilizes a GPS adapter to track device locations over time (known as "Snoopers"). The tool provides insights into the movement of these devices and maps Wi-Fi attacks logged by Kismet.
Features:

  Device Detection:
        Extracts Wi-Fi and Bluetooth device data (MAC addresses, SSID, device type, encryption) from the latest Kismet .kismet database file.
        Utilizes a GPS adapter to record the geographic coordinates of detected devices.

  Snooper Detection:
        Identifies Wi-Fi and Bluetooth devices that have been seen in multiple locations, indicating potential surveillance or unusual activity.

  Wi-Fi Attack Alerts:
        Detects Wi-Fi attack alerts (e.g., deauthentication) recorded by Kismet and plots them on a map.

  Visualization:
        Generates an interactive HTML map using Folium, marking:
            Wi-Fi and Bluetooth devices (blue markers)
            Snoopers (red markers)
            Wi-Fi attacks (orange markers)


Requirements

The following Python libraries are required to run SnoopR. They are listed in the requirements.txt file:

    folium
    pandas
    cbor2
    jinja2

Installation Guide

Follow the steps below to install and use SnoopR:
Step-by-Step Installation

First, clone the repository to your local machine:

    git clone https://github.com/AlienMajik/SnoopR.git
   
    cd SnoopR

Create a Virtual Environment (Optional but Recommended)

It’s good practice to isolate dependencies in a virtual environment. Create one by running the following:


    python3 -m venv env
  
    source env/bin/activate
    

Install Dependencies

Install the required dependencies from the requirements.txt file:


    pip install -r requirements.txt


Run Kismet

Ensure Kismet is running and capturing network traffic. You can use this command (with appropriate adapter names):

    
    sudo kismet -c wlan1 -c hci0:bluetooth
    

Running Kismet with Multiple Adapters

Kismet allows capturing traffic from multiple adapters simultaneously by specifying each adapter in the command. Here’s how users can configure multiple Wi-Fi and Bluetooth adapters:
Wi-Fi Adapters

You can specify more than one Wi-Fi adapter by listing each one with the -c flag:


    sudo kismet -c wlan0 -c wlan1
    

This will tell Kismet to capture data from both wlan0 and wlan1 Wi-Fi adapters.
Bluetooth Adapters

Similarly, for Bluetooth, use the -c flag with the Bluetooth adapter names (for example, hci0 for the first Bluetooth interface):


    sudo kismet -c wlan0 -c hci0:bluetooth


You can add multiple Bluetooth adapters like so:


    sudo kismet -c wlan0 -c hci0:bluetooth -c hci1:bluetooth


This command captures Wi-Fi traffic on wlan0 and Bluetooth traffic on both hci0 and hci1.
Replace wlan1 and hci0 with your actual Wi-Fi and Bluetooth adapter names.


Once Kismet is done capturing traffic, run SnoopR to analyze and visualize data:

    
    python3 SnoopR.py


View the Map with:
    
   
    xdg-open SnoopR_Map.html


After the script finishes processing, an HTML file named SnoopR_Map.html will be created in your working directory. Open this file in any browser to view the interactive map with device and alert data.


Usage

  Automatically Find the Most Recent .kismet File:
        SnoopR automatically selects the most recent Kismet capture file in your working directory.

  Extract and Analyze Data:
        The script extracts device information (MAC address, SSID, encryption type, location etc.) and alerts from the .kismet file.

  Detect Snoopers:
        Devices that have been detected in multiple locations are flagged as snoopers.

  Alerts for Wi-Fi Attacks:
        Wi-Fi attacks (such as deauthentication or other suspicious behavior) captured by Kismet are also flagged and marked on the map.

  Visualize Devices and Alerts:
        After processing, the script generates an interactive Openstreetmaps HTML map (SnoopR_Map.html) that marks devices and alerts.




Feel free to fork the repository, make changes, and open pull requests if you want to add features or improve the script!
