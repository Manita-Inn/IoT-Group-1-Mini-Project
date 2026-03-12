import network, urequests, time
from machine import Pin
from tm1637 import TM1637  # Make sure tm1637.py is uploaded to ESP32

# --------------------------
# WiFi & Telegram Settings
# --------------------------
SSID = "Hen Sarith"
PASS = "hensarith"
BOT_TOKEN = "8415101738:AAGYO8zwir8sqOhEJwlj0l4KNwHlPmIEywU"
CHAT_ID = "-5035961178"
URL = "https://api.telegram.org/bot{}/".format(BOT_TOKEN)

# --------------------------
# IR Sensors
# --------------------------
ir_sensors = [Pin(32, Pin.IN), Pin(35, Pin.IN), Pin(33, Pin.IN)] 

# --------------------------
# TM1637 Display (4-digit)
# --------------------------
tm = TM1637(clk=Pin(13), dio=Pin(12))
tm.brightness(1)  # 0-7 brightness

# --------------------------
# Connect WiFi
# --------------------------
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASS)
while not wifi.isconnected():
    time.sleep(1)
print("WiFi Ready:", wifi.ifconfig())

last_id = 0

# --------------------------
# Main Loop
# --------------------------
while True:
    try:
        # Update Telegram messages
        r = urequests.get(URL + "getUpdates?offset={}&timeout=5".format(last_id + 1))
        if r.status_code == 200:
            data = r.json()
            r.close()
            for msg in data.get("result", []):
                last_id = msg["update_id"]
                message_data = msg.get("message") or msg.get("edited_message")
                if message_data and "text" in message_data:
                    text = message_data["text"]
                    if "/slots" in text:
                        count = sum([p.value() for p in ir_sensors])
                        reply = "Slots Available: {}/3".format(count)
                        print(">>> Terminal Count:", count)
                        urequests.post(URL + "sendMessage", json={"chat_id": CHAT_ID, "text": reply}).close()
        else:
            r.close()
    except Exception as e:
        print("Error:", e)
    
    # --------------------------
    # Update TM1637 Display
    # --------------------------
    count = sum([p.value() for p in ir_sensors])
    # Convert count to 4-character string, then to list of chars for TM1637
    tm_number = "{:0>4}".format(count)  # e.g., '0001'
    digits = list(tm_number)             # ['0','0','0','1']
    tm.show(digits)
    
    time.sleep(1)
