import network
import socket
import time

# ==============================
# WiFi Credentials
# ==============================
ssid = "Map touch"
password = "goodluck2020"

# ==============================
# Parking System Variables
# ==============================
total_slots = 5
occupied_slots = 0
available_slots = total_slots - occupied_slots

temperature = 28
gate_status = "Closed"
light_status = "OFF"

# ==============================
# Connect to WiFi
# ==============================
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(ssid, password)

print("Connecting to WiFi...")
while not wifi.isconnected():
    time.sleep(1)

print("Connected!")
print("ESP32 IP Address:", wifi.ifconfig()[0])

# ==============================
# Create Web Server
# ==============================
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
server = socket.socket()
server.bind(addr)
server.listen(1)
print("Web Server Started")

# ==============================
# Web Page Function (Professional Design)
# ==============================
def webpage():
    html = f"""
    <!DOCTYPE html>
    <html>

    <head>
        <title>Smart IoT Parking System</title>
        <meta chartset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">

        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f4f6f8;
                text-align: center;
                margin: 0;
                padding: 0;
            }}

            h1 {{
                background-color: #2c3e50;
                color: white;
                padding: 20px;
                margin: 0;
            }}

            .container {{
                margin-top: 30px;
            }}

            .card {{
                background-color: white;
                width: 320px;
                margin: auto;
                padding: 25px;
                border-radius: 10px;
                box-shadow: 0px 4px 8px rgba(0,0,0,0.2);
            }}

            .info {{
                font-size: 18px;
                margin: 12px 0;
            }}

            button {{
                width: 140px;
                height: 45px;
                font-size: 16px;
                border: none;
                border-radius: 8px;
                margin: 8px;
                cursor: pointer;
            }}

            .open {{
                background-color: #27ae60;
                color: white;
            }}

            .close {{
                background-color: #e74c3c;
                color: white;
            }}

            .light {{
                background-color: #f39c12;
                color: white;
            }}
        </style>
    </head>

    <body>

        <h1>Smart IoT Parking System</h1>

        <div class="container">

            <div class="card">

                <p class="info">Total Slots: {total_slots}</p>
                <p class="info">Available Slots: {available_slots}</p>
                <p class="info">Temperature: {temperature} °C</p>

                <p class="info">Gate Status: {gate_status}</p>
                <p class="info">Light Status: {light_status}</p>

                <br>

                <a href="/open"><button class="open">Open Gate</button></a>
                <a href="/close"><button class="close">Close Gate</button></a>

                <br>

                <a href="/light_on"><button class="light">Light ON</button></a>
                <a href="/light_off"><button class="light">Light OFF</button></a>

            </div>

        </div>

    </body>

    </html>
    """
    return html

# ==============================
# Main Server Loop
# ==============================
while True:
    client, addr = server.accept()
    print("Client connected")

    request = client.recv(1024)
    request = str(request)

    # ==========================
    # Button Commands
    # ==========================
    if '/open' in request:
        print("Opening Gate")
        gate_status = "Open"

    if '/close' in request:
        print("Closing Gate")
        gate_status = "Closed"

    if '/light_on' in request:
        print("Light ON")
        light_status = "ON"

    if '/light_off' in request:
        print("Light OFF")
        light_status = "OFF"

    # ==========================
    # Send Web Page
    # ==========================
    response = webpage()
    client.send('HTTP/1.1 200 OK\n')
    client.send('Content-Type: text/html; charset=UTF-8\n')
    client.send('Connection: close\n\n')
    client.sendall(response)
    client.close()
