import network, urequests, time, dht
from machine import Pin

# Settings
SSID = "Hen Sarith"
PASS = "hensarith"
BOT_TOKEN = "8415101738:AAGYO8zwir8sqOhEJwlj0l4KNwHlPmIEywU"
CHAT_ID = "-5035961178"

sensor = dht.DHT11(Pin(27)) # PIN 27 [cite: 19]
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASS)

print("Connecting to WiFi...")
while not wifi.isconnected(): time.sleep(1)
print("WiFi connected! IP:", wifi.ifconfig()[0])

URL = "https://api.telegram.org/bot{}/".format(BOT_TOKEN)
last_id = 0

while True:
    try:
        r = urequests.get(URL + "getUpdates?offset={}&timeout=5".format(last_id + 1))
        if r.status_code == 200:
            data = r.json()
            r.close()
            for msg in data.get("result", []):
                last_id = msg["update_id"]
                # Look for text in standard messages or edited messages
                message_data = msg.get("message") or msg.get("edited_message")
                if message_data and "text" in message_data:
                    text = message_data["text"]
                    
                    if "/temp" in text: # Requirement 6 [cite: 36, 42]
                        sensor.measure()
                        t, h = sensor.temperature(), sensor.humidity()
                        reply = "Group Status - Temp: {}C, Hum: {}%".format(t, h)
                        
                        print(">>> Terminal: {}C, {}%".format(t, h))
                        
                        # Sending back with explicit Chat ID
                        send_url = URL + "sendMessage"
                        payload = {"chat_id": CHAT_ID, "text": reply}
                        res = urequests.post(send_url, json=payload)
                        print(">>> Telegram Response:", res.status_code, res.text)
                        res.close()
        else: r.close()
    except Exception as e: print("Error:", e)
    time.sleep(1)
