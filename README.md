                                                           # SnoopR


                            KXXXXXXXXXXXXXX0KNO00KXXXNXXKNXKOOOOOOOOOOOOkkxxxxxdddOKkKKNXNNNXXXXKk',,
                            KKXXXXXXXXXXXXX0KXk000XXXXXXKXXKxl;........',;clodxdddkKd0XNXNNNNNNXKk.,.
                            KXXXXXXXXXXXXXX0KXk000XXXXXXKXKo.. ..............,:lddkKdkXXXXNNNNNXXX:dk
                            KKXXXXXXXXXXXKK0KXk0O0KXXXXXKXK; .',:c:,;:ccllc:c:,.;lOKkdXKXNNNNNXXXXx00
                            KKKXXXXXXXXXXKK00Xk0O0KXXXXX0X0';dxlxxcoOKKKKKKK00Od;,KKkcXXXNNNNXXXXX0kK
                            KKXXXXXXXXXXKKK0KXO0O0KXXXXX0Xx:dxxdodlOKXXXXXXKKK0OkdK0Oc0XXNXXNXXXXXXXX
                            XXXXXXKKXXKXKKK00XO0O0KXXXXXKX:'cdxxkox0NNXXXXXKK00OkxKKOlcXXXXXXXXXXXXXX
                            KXXXKKXKXKKKKKK0KXO0OO0XXXXX0X,.,ldxkxxKXXXKKKKK0000OxKK0xcKKXXXXXXXXXXXX
                            KXXXXXXXXKKKKKKOKKO0kO0KXXXK0K..;odxxxdk000000KOO000OkO0OOdOKXXXXXXXXXXXX
                            KKXXXXXKKKKKKKKO0KO0k00KXKKK0K:lll:,,,'.'';:lxdoc:;;::dKOOkOKXXXXXXXXXXXX
                            KKKKKKXKKKKKKKKO0KkOx00KKKKK00doc,...'cl..',oOx;;:l;.'dKOOOKKXXXXXXXXXXXX
                            KKKKKKKKKKKKKKKO0Kk0k00KKKKK00kdooloooooloddxOOkxdxoolk0OOOXKXXXXXXXXXXXX
                            0KKKKKKKKKKKK00O0Kk0OO0KKKKKOOkooddxkO0OOkxxxkK0xkkO0kOKO0OXKXXXXXXXXXXXX
                            0KKKKKKKKKKKK00OOKk0O00KKKKKOOolodxxkOkocclccokOoolxOO0KO0OXKXXXXXXXXXXXX
                            0KKKKKKKKKKKKK0OOKk0O00KKKKKOO;:cloodl;;:;,;'...,cccxOKKO00XKXXXXXXXXXXXX
                            0KKKKKKKKKKKKK0OkKk0O00KKKKKOk:';cclc;::;;;:c:;;:::;ok0KkO0XKXXXXXXXXXXXX
                            KKKKKKKKKKKKKKK0kKk0000KKKKKOxc.';coll:..cdxkkkd''ccdk0KO00XKXXXXXXXXXXXX
                            0KKKKKKKKKKKKKKOkKk0OO0KKKKKOdc .,;cxxdlxxxxoodxllxx:k0KOO0XKXXXXXXXXXXXX
                            0KKKKKKKKKKKKK0OxKk0kO0KKKKKOo;  .',:dxdodkOkkkxddxo.k0KOO0XKXXXXXXXXXXXX
                            KKKKKKKKKKKKKK0OxKO0OO0KKKKKOo'    ..;odxooooooodxo..OO0kk0XKXXXXXXXXXXXX
                            KKKKKKKKKKKKKKK0kKOKOO0KKKKKOo.      ..:ldxxxxxxxo' ;KO0kk0XKXXXXXXXXXXXK
                            00KKKKKKKKKKKKKOxKOK000KKKKKkl.         ..,:::::,.  lKOKkk0XKXXXXXXXXXXXX
                            KKKKKKKKKKKKKKKOdKO0000KKKKKkl.   ...               .OO0kkKKKXXXXXXXXXXXX
                            0KKKKKKKKKKK0K0OoKO0O00KXKKKxx.    ....             ;0k0xk0KKKXXXXXXXXXXX
                            00KKKKKKKKKK0K0kdKOOk00KKKKKxk     ...'.            lKk0xk0K0KXXXXXXXXXXX
                            dkO00KKKKKKKK00ko0kkOOOKKKKKkk.     ...''..         dKk0xxKKKXXXXXXXXXXXX
                            ,:coxkO000000O0Oo0Okk0OKKKK0kk.       .'';;'.     ,:KKk0xxKKKXXXXXXXXXXXX
                            ',;;:ccldxkOkOOkd0Okx0kKKKK0kO..       .,;,.     .0KXKk0kxKKKXXXXXXXXXXXX
                            ',,;;:::::clodxxlkOxx0kKKKKKkk..  ...   .c'     ..KXXKxKkxXKKXXXXK0O000KX

                                             ʎoq llnp ɐ ʞɔɐſ sǝʞɐɯ ʎɐld ou puɐ ʞɹoʍ ll∀



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

Ensure Kismet is running and capturing network traffic. Wardrive around in order to see if devices are following you. You can use this command (with appropriate adapter names):

    
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


How to Change the Detection Distance/Radius in SnoopR

The SnoopR script uses the haversine formula to calculate the distance between two GPS coordinates in miles. By default, the script is set to detect devices (snoopers) that move more than 0.05 miles (approximately 80 meters). If you wish to increase or decrease this radius to change the sensitivity of the detection, follow these steps:

  Locate the detect_snoopers Function: In the SnoopR.py script, find the function definition for detect_snoopers. It will look like this:

  
    def detect_snoopers(device_data, distance_threshold=0.05):  # Distance in miles


Change the distance_threshold Parameter:

  To increase the detection radius (detect snoopers over a larger distance), increase the value of the distance_threshold parameter. For example, setting it to 0.1 miles would track devices that have moved approximately 160 meters or more:


    def detect_snoopers(device_data, distance_threshold=0.1):  # Increased detection radius


To decrease the detection radius (detect snoopers over a shorter distance), lower the distance_threshold value. Setting it to 0.02 miles would detect devices that have moved 32 meters or more:

python


    def detect_snoopers(device_data, distance_threshold=0.02):  # Decreased detection radius


Save the Script: After modifying the distance_threshold, save the changes to the script.


Run SnoopR: Run the script as usual. The snooper detection will now use the new radius for detecting devices.

Disclaimer for SnoopR

SnoopR is provided for educational and informational purposes only. It is intended to help users understand the detection of wireless network devices and potential vulnerabilities in their own networks. The script should only be used on networks or devices that you own or have explicit permission to monitor.

Unauthorized use of this software on networks or devices without proper consent is illegal and violates local, state, and international laws. SnoopR is not intended to be used for any malicious or unethical activities, such as unauthorized network intrusion, eavesdropping, or tracking personal devices without consent.

By using SnoopR, you agree to the following:

    You assume full responsibility for any actions taken with this software.
    You understand that any misuse of this tool may result in criminal or civil penalties.
    The creator of SnoopR is not responsible for any misuse, illegal activity, or damages resulting from the use of this software.

Always respect privacy and comply with the law when using SnoopR.

Feel free to fork the repository, make changes, and open pull requests if you want to add features or improve the script!
