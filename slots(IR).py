import network, urequests, time
from machine import Pin

# Settings
SSID = "Hen Sarith"
PASS = "hensarith"
BOT_TOKEN = "8415101738:AAGYO8zwir8sqOhEJwlj0l4KNwHlPmIEywU"
CHAT_ID = "-5035961178"

# 3 IR Sensors on pins 32, 33, 34 [cite: 17]
ir_sensors = [Pin(32, Pin.IN), Pin(33, Pin.IN), Pin(34, Pin.IN)] 

wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASS)
while not wifi.isconnected(): time.sleep(1)
print("WiFi Ready.")

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
                message_data = msg.get("message") or msg.get("edited_message")
                if message_data and "text" in message_data:
                    text = message_data["text"]
                    
                    if "/slots" in text: # Requirement 6 [cite: 41]
                        count = sum([p.value() for p in ir_sensors]) 
                        reply = "Slots Available: {}/3".format(count)
                        print(">>> Terminal Count: {}".format(count))
                        urequests.post(URL + "sendMessage", json={"chat_id": CHAT_ID, "text": reply}).close()
        else: r.close()
    except Exception as e: print("Error:", e)
    time.sleep(1)
