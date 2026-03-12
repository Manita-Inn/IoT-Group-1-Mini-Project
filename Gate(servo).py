import network, urequests, time
from machine import Pin, PWM
import machine

machine.freq(80_000_000)

# Settings
SSID = "Hen Sarith"
PASS = "hensarith"
BOT_TOKEN = "8415101738:AAGYO8zwir8sqOhEJwlj0l4KNwHlPmIEywU"
CHAT_ID = "-5035961178"

# Servo setup on PIN 21
servo = PWM(Pin(21), freq=50)

# Calibrated Duty Values
DUTY_CLOSE = 49
DUTY_OPEN  = 100

def set_gate(duty):
    servo.duty(duty)
    print("Servo duty: {}".format(duty))

def send_msg(text):
    try:
        urequests.post(
            URL + "sendMessage",
            json={"chat_id": CHAT_ID, "text": text}
        ).close()
        print("Sent: {}".format(text))
    except Exception as e:
        print("Send error:", e)

# Connect to WiFi
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASS)

print("Connecting to WiFi...")
while not wifi.isconnected():
    time.sleep(1)
print("WiFi Ready. IP:", wifi.ifconfig()[0])

URL = "https://api.telegram.org/bot{}/".format(BOT_TOKEN)
gate_open = False

# ── Skip all existing messages on boot ──────────────────────
print("Skipping old messages...")
last_id = 0
try:
    r = urequests.get(URL + "getUpdates?offset=-1&timeout=3", timeout=10)
    if r.status_code == 200:
        data = r.json()
        r.close()
        results = data.get("result", [])
        if results:
            last_id = results[-1]["update_id"]
            print("Skipped up to message ID: {}".format(last_id))
        else:
            print("No old messages found.")
    else:
        r.close()
except Exception as e:
    print("Skip error:", e)

print("Bot running... Only NEW messages will be processed.")

while True:
    try:
        r = urequests.get(URL + "getUpdates?offset={}&timeout=5".format(last_id + 1), timeout=10)

        if r.status_code == 200:
            data = r.json()
            r.close()

            for msg in data.get("result", []):
                last_id = msg["update_id"]
                message_data = msg.get("message") or msg.get("edited_message")

                if message_data and "text" in message_data:
                    text = message_data["text"]
                    print("Received:", text)

                    if "/open" in text:
                        set_gate(DUTY_OPEN)
                        gate_open = True
                        print(">>> Gate OPENED (duty={})".format(DUTY_OPEN))
                        send_msg("Gate: OPENED")

                    elif "/close" in text:
                        set_gate(DUTY_CLOSE)
                        gate_open = False
                        print(">>> Gate CLOSED (duty={})".format(DUTY_CLOSE))
                        send_msg("Gate: CLOSED")

                    elif "/status" in text:
                        gate_status = "OPEN" if gate_open else "CLOSED"
                        print(">>> Status: {}".format(gate_status))
                        send_msg("Gate Status: {}".format(gate_status))
        else:
            r.close()

    except Exception as e:
        print("Error:", e)
        time.sleep(2)

    time.sleep(1)
