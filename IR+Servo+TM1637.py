import network, urequests, time
from machine import Pin, PWM
import machine

machine.freq(80_000_000)

# ==============================
# SETTINGS
# ==============================
SSID      = "Hen Sarith"
PASS      = "hensarith"
BOT_TOKEN = "8415101738:AAGYO8zwir8sqOhEJwlj0l4KNwHlPmIEywU"
CHAT_ID   = "-5035961178"

# ==============================
# TM1637 LIBRARY (built-in)
# ==============================
from tm1637 import TM1637
tm = TM1637(clk=Pin(13), dio=Pin(12))
tm.brightness(1)

# ==============================
# SERVO SETUP — PIN 21
# ==============================
servo = PWM(Pin(21), freq=50)
DUTY_CLOSE = 49
DUTY_OPEN  = 100

def set_gate(duty):
    servo.duty(duty)
    print("Servo duty: {}".format(duty))

# ==============================
# IR SENSORS — PIN 32, 35, 33
# ==============================
ir_sensors = [Pin(32, Pin.IN), Pin(35, Pin.IN), Pin(33, Pin.IN)]
TOTAL_SLOTS = 3

def get_available():
    # 1 = empty, 0 = occupied
    return sum(p.value() for p in ir_sensors)

def update_display():
    available = get_available()
    tm_number = "{:0>4}".format(available)
    tm.show(list(tm_number))
    return available

# ==============================
# WIFI SETUP
# ==============================
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASS)

print("Connecting to WiFi...")
while not wifi.isconnected():
    time.sleep(1)
print("WiFi Ready. IP:", wifi.ifconfig()[0])

URL = "https://api.telegram.org/bot{}/".format(BOT_TOKEN)
gate_open = False

def send_msg(text):
    try:
        urequests.post(
            URL + "sendMessage",
            json={"chat_id": CHAT_ID, "text": text}
        ).close()
        print("Sent: {}".format(text))
    except Exception as e:
        print("Send error:", e)

# ==============================
# SKIP OLD MESSAGES ON BOOT
# ==============================
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
            print("Skipped up to ID: {}".format(last_id))
        else:
            print("No old messages found.")
    else:
        r.close()
except Exception as e:
    print("Skip error:", e)

# Show slot count on boot
available = update_display()
print("Slots available on boot: {}/{}".format(available, TOTAL_SLOTS))
print("Bot running... Only NEW messages will be processed.")

# ==============================
# MAIN LOOP
# ==============================
while True:
    try:
        # ── Update TM1637 display ─────────────────────────────
        available = update_display()

        # ── Auto close gate if parking full ───────────────────
        if available == 0 and gate_open:
            set_gate(DUTY_CLOSE)
            gate_open = False
            print(">>> Parking FULL — Gate auto CLOSED")
            send_msg("Parking FULL! Gate automatically CLOSED.")

        # ── Telegram Commands ─────────────────────────────────
        r = urequests.get(URL + "getUpdates?offset={}&timeout=3".format(last_id + 1), timeout=10)

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
                        available = get_available()
                        if available == 0:
                            # Parking full — deny entry
                            print(">>> Parking FULL — Gate denied")
                            send_msg("Parking FULL! No slots available. Gate remains CLOSED.")
                        else:
                            # Slots available — open gate
                            set_gate(DUTY_OPEN)
                            gate_open = True
                            occupied = TOTAL_SLOTS - available
                            print(">>> Gate OPENED — {}/{} slots available".format(available, TOTAL_SLOTS))
                            send_msg("Gate OPENED\nAvailable: {}/{}\nOccupied: {}/{}".format(
                                available, TOTAL_SLOTS, occupied, TOTAL_SLOTS))

                    elif "/close" in text:
                        set_gate(DUTY_CLOSE)
                        gate_open = False
                        print(">>> Gate CLOSED")
                        send_msg("Gate: CLOSED")

                    elif "/slots" in text:
                        available = get_available()
                        occupied = TOTAL_SLOTS - available
                        print(">>> Slots: Available={} Occupied={}".format(available, occupied))
                        send_msg("Parking Slots:\nAvailable: {}/{}\nOccupied: {}/{}".format(
                            available, TOTAL_SLOTS, occupied, TOTAL_SLOTS))

                    elif "/status" in text:
                        available = get_available()
                        occupied = TOTAL_SLOTS - available
                        gate_status = "OPEN" if gate_open else "CLOSED"
                        send_msg("Gate: {}\nAvailable: {}/{}\nOccupied: {}/{}".format(
                            gate_status, available, TOTAL_SLOTS, occupied, TOTAL_SLOTS))
        else:
            r.close()

    except Exception as e:
        print("Error:", e)
        time.sleep(2)

    time.sleep(1)
