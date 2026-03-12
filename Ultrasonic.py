import network, urequests, time
from machine import Pin
import machine

machine.freq(80_000_000)

# Settings
SSID = "Hen Sarith"
PASS = "hensarith"
BOT_TOKEN = "8415101738:AAGYO8zwir8sqOhEJwlj0l4KNwHlPmIEywU"
CHAT_ID = "-5035961178"

# TRIG = GPIO13 | ECHO = GPIO12
TRIG = Pin(23, Pin.OUT)
ECHO = Pin(22, Pin.IN)

def get_distance():
    TRIG.value(0)
    time.sleep_us(5)
    TRIG.value(1)
    time.sleep_us(10)
    TRIG.value(0)

    start_wait = time.ticks_us()
    while ECHO.value() == 0:
        if time.ticks_diff(time.ticks_us(), start_wait) > 1000000:
            return -1

    start = time.ticks_us()
    while ECHO.value() == 1:
        if time.ticks_diff(time.ticks_us(), start) > 1000000:
            return -2

    end = time.ticks_us()
    duration = time.ticks_diff(end, start)
    distance = (duration * 0.0343) / 2
    return round(distance, 1)

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

print("Sending distance every 2 seconds...")

while True:
    dist = get_distance()

    if dist == -1:
        msg = "ERROR: No echo received"
        print(msg)
    elif dist == -2:
        msg = "ERROR: Echo stuck HIGH"
        print(msg)
    elif dist < 2:
        msg = "TOO CLOSE: {}cm".format(dist)
        print(msg)
    elif dist > 400:
        msg = "OUT OF RANGE"
        print(msg)
    else:
        msg = "Distance: {} cm".format(dist)
        print(msg)

    send_msg(msg)
    time.sleep(2)
