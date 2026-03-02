import network, urequests, time
from machine import Pin, PWM

# Settings
SSID = "Hen Sarith"
PASS = "hensarith"
BOT_TOKEN = "8415101738:AAGYO8zwir8sqOhEJwlj0l4KNwHlPmIEywU"
CHAT_ID = "-5035961178"

servo = PWM(Pin(13), freq=50) # PIN 13 [cite: 18]

def set_gate(angle):
    duty = int((angle / 180 * 75) + 40)
    servo.duty(duty)

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
                    
                    if "/open" in text: # Requirement 6 [cite: 39]
                        set_gate(90)
                        print(">>> Terminal: Gate OPENED")
                        urequests.post(URL + "sendMessage", json={"chat_id": CHAT_ID, "text": "Gate: OPENED"}).close()
                    elif "/close" in text: # Requirement 6 [cite: 40]
                        set_gate(0)
                        print(">>> Terminal: Gate CLOSED")
                        urequests.post(URL + "sendMessage", json={"chat_id": CHAT_ID, "text": "Gate: CLOSED"}).close()
        else: r.close()
    except Exception as e: print("Error:", e)
    time.sleep(1)
