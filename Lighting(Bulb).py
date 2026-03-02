import network, urequests, time
from machine import Pin

# ---------- SETTINGS ----------
SSID = "Hen Sarith"
PASS = "hensarith"
BOT_TOKEN = "8415101738:AAGYO8zwir8sqOhEJwlj0l4KNwHlPmIEywU"
CHAT_ID = "-5035961178" # Your Group ID

# ---------- HARDWARE ----------
# Pin 14 as per your setup for the Relay Module
relay = Pin(14, Pin.OUT) 

# ---------- WIFI CONNECT ----------
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASS)

print("Connecting to WiFi...")
while not wifi.isconnected():
    time.sleep(1)
print("WiFi connected! IP:", wifi.ifconfig()[0])

URL = "https://api.telegram.org/bot{}/".format(BOT_TOKEN)
last_id = 0

print("Monitoring for Light commands (/light_on, /light_off)...")

while True:
    try:
        # Long polling for updates
        r = urequests.get(URL + "getUpdates?offset={}&timeout=5".format(last_id + 1))
        
        if r.status_code == 200:
            data = r.json()
            r.close()
            
            for msg in data.get("result", []):
                last_id = msg["update_id"]
                
                # Check for text in the group message
                message_data = msg.get("message") or msg.get("edited_message")
                if message_data and "text" in message_data:
                    text = message_data["text"]
                    
                    # Logic for /light_on [cite: 43]
                    if "/light_on" in text:
                        relay.value(1) # Sets GPIO 14 to High
                        print(">>> Terminal: Lights ON")
                        
                        # Forwarding confirmation to Telegram Group
                        payload = {"chat_id": CHAT_ID, "text": "Parking Lights: ON"}
                        urequests.post(URL + "sendMessage", json=payload).close()
                        print(">>> Telegram: Confirmation sent to Group")

                    # Logic for /light_off [cite: 44]
                    elif "/light_off" in text:
                        relay.value(0) # Sets GPIO 14 to Low
                        print(">>> Terminal: Lights OFF")
                        
                        # Forwarding confirmation to Telegram Group
                        payload = {"chat_id": CHAT_ID, "text": "Parking Lights: OFF"}
                        urequests.post(URL + "sendMessage", json=payload).close()
                        print(">>> Telegram: Confirmation sent to Group")
        else:
            r.close()
            
    except Exception as e:
        print("Network error. Retrying...")
    
    time.sleep(1)
