import network, urequests, time, dht
from machine import Pin, PWM
from tm1637 import TM1637
import machine

machine.freq(80_000_000)

# ==============================
# SETTINGS
# ==============================
SSID      = "Hen Sarith"
PASS      = "hensarith"
BOT_TOKEN = "8415101738:AAGYO8zwir8sqOhEJwlj0l4KNwHlPmIEywU"
CHAT_ID   = "-5035961178"

URL = "https://api.telegram.org/bot{}/".format(BOT_TOKEN)

# ==============================
# DHT11 SENSOR (PIN 27)
# ==============================
dht_sensor = dht.DHT11(Pin(15))

# ==============================
# SERVO — PIN 21
# ==============================
servo = PWM(Pin(21), freq=50)

DUTY_CLOSE = 49
DUTY_OPEN  = 100

def set_gate(duty):
    servo.duty(duty)
    print("Servo duty:", duty)

# ==============================
# IR PARKING SENSORS
# ==============================
ir_sensors = [Pin(32, Pin.IN), Pin(35, Pin.IN), Pin(33, Pin.IN)]
TOTAL_SLOTS = 3

def get_available():
    return sum(p.value() for p in ir_sensors)

# ==============================
# TM1637 DISPLAY
# ==============================
tm = TM1637(clk=Pin(13), dio=Pin(12))
tm.brightness(1)

def update_display():
    available = get_available()
    tm.show(list("{:0>4}".format(available)))
    return available

# ==============================
# ULTRASONIC SENSOR
# ==============================
TRIG = Pin(17, Pin.OUT)
ECHO = Pin(16, Pin.IN)

DETECT_CM = 10
AUTO_CLOSE_SEC = 5

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

    return round(distance,1)

# ==============================
# WIFI
# ==============================
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASS)

print("Connecting WiFi...")

while not wifi.isconnected():
    time.sleep(1)

print("WiFi Ready:", wifi.ifconfig())

# ==============================
# TELEGRAM SEND MESSAGE
# ==============================
def send_msg(text):
    try:
        urequests.post(
            URL + "sendMessage",
            json={"chat_id": CHAT_ID, "text": text}
        ).close()

        print("Sent:", text)

    except Exception as e:
        print("Send error:", e)

# ==============================
# SKIP OLD TELEGRAM MESSAGES
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
            print("Skipped to ID:", last_id)

except:
    pass

# ==============================
# VARIABLES
# ==============================
gate_open = False
full_notified = False
last_detect_time = None

available = update_display()

print("Boot — Slots available:", available, "/", TOTAL_SLOTS)
print("Bot running...")

# ==============================
# MAIN LOOP
# ==============================
while True:

    try:

        # --------------------------
        # Update Parking Display
        # --------------------------
        available = update_display()
        occupied = TOTAL_SLOTS - available

        # --------------------------
        # Auto close if full
        # --------------------------
        if available == 0 and gate_open:

            set_gate(DUTY_CLOSE)

            gate_open = False
            last_detect_time = None

            send_msg(
                "Parking FULL\n"
                "Gate automatically CLOSED\n"
                "Occupied: {}/{}".format(occupied, TOTAL_SLOTS)
            )

        # --------------------------
        # Ultrasonic Detection
        # --------------------------
        dist = get_distance()

        print("Distance:", dist,
              "| Slots:", available,"/",TOTAL_SLOTS,
              "| Gate:", "OPEN" if gate_open else "CLOSED")

        if dist > 0 and dist < DETECT_CM:

            last_detect_time = time.ticks_ms()

            if available > 0:

                if not gate_open:

                    set_gate(DUTY_OPEN)
                    gate_open = True
                    full_notified = False

                    send_msg(
                        "Vehicle detected {}cm\n"
                        "Gate OPEN\n"
                        "Available: {}/{}".format(dist,available,TOTAL_SLOTS)
                    )

            else:

                if not full_notified:

                    send_msg(
                        "Vehicle detected {}cm\n"
                        "Parking FULL\n"
                        "Gate CLOSED".format(dist)
                    )

                    full_notified = True

        else:

            if gate_open and last_detect_time is not None:

                elapsed = time.ticks_diff(time.ticks_ms(), last_detect_time)/1000

                if elapsed >= AUTO_CLOSE_SEC:

                    set_gate(DUTY_CLOSE)

                    gate_open = False
                    last_detect_time = None
                    full_notified = False

                    send_msg("Gate CLOSED automatically")

        # --------------------------
        # TELEGRAM COMMANDS
        # --------------------------
        r = urequests.get(URL + "getUpdates?offset={}&timeout=3".format(last_id+1), timeout=10)

        if r.status_code == 200:

            data = r.json()
            r.close()

            for msg in data.get("result", []):

                last_id = msg["update_id"]

                message_data = msg.get("message") or msg.get("edited_message")

                if message_data and "text" in message_data:

                    text = message_data["text"]

                    print("Received:", text)

                    # --------------------------
                    # TEMPERATURE COMMAND
                    # --------------------------
                    if "/temp" in text:

                        dht_sensor.measure()
                        t = dht_sensor.temperature()
                        h = dht_sensor.humidity()

                        send_msg(
                            "Temperature: {}°C\nHumidity: {}%".format(t,h)
                        )

                    elif "/open" in text:

                        if get_available() == 0:

                            send_msg("Parking FULL — cannot open")

                        else:

                            set_gate(DUTY_OPEN)
                            gate_open = True
                            last_detect_time = time.ticks_ms()

                            send_msg("Gate OPENED manually")

                    elif "/close" in text:

                        set_gate(DUTY_CLOSE)

                        gate_open = False
                        last_detect_time = None

                        send_msg("Gate CLOSED manually")

                    elif "/slots" in text:

                        a = get_available()

                        send_msg(
                            "Parking Slots\n"
                            "Available: {}/{}\n"
                            "Occupied: {}/{}".format(a,TOTAL_SLOTS,TOTAL_SLOTS-a,TOTAL_SLOTS)
                        )

                    elif "/status" in text:

                        a = get_available()

                        send_msg(
                            "Gate: {}\nAvailable: {}/{}".format(
                                "OPEN" if gate_open else "CLOSED",
                                a,
                                TOTAL_SLOTS
                            )
                        )

    except Exception as e:

        print("Error:", e)
        time.sleep(1)

    time.sleep(0.5)
