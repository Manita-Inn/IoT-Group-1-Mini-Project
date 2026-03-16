import network, urequests, time, dht
from machine import Pin, PWM, I2C
from tm1637 import TM1637
from lcd_i2c import LCD
import machine

machine.freq(240_000_000)

SSID      = "AUPP Wifi"
PASS      = ""
BOT_TOKEN = "8415101738:AAGYO8zwir8sqOhEJwlj0l4KNwHlPmIIywU"
CHAT_ID   = "-5035961178"
URL       = "https://api.telegram.org/bot{}/".format(BOT_TOKEN)

dht_sensor = dht.DHT11(Pin(15))
servo      = PWM(Pin(21), freq=50)
DUTY_CLOSE = 51
DUTY_OPEN  = 99

def set_gate(duty):
    servo.duty(duty)
    print("Gate duty:", duty)

ir_servo         = PWM(Pin(5), freq=50)
ir_sensor        = Pin(4, Pin.IN)
IR_DUTY_CLOSE    = 99
IR_DUTY_OPEN     = 51
ir_last_state    = None
ir_waiting_close = False
ir_clear_time    = None
IR_CLOSE_DELAY   = 4

def handle_ir_servo():
    global ir_last_state, ir_waiting_close, ir_clear_time
    detected = ir_sensor.value() == 0
    if detected:
        ir_waiting_close = False; ir_clear_time = None
        if ir_last_state != "detected":
            ir_servo.duty(IR_DUTY_OPEN); ir_last_state = "detected"
    else:
        if ir_last_state == "detected" and not ir_waiting_close:
            ir_waiting_close = True; ir_clear_time = time.ticks_ms()
        if ir_waiting_close and ir_clear_time is not None:
            elapsed = time.ticks_diff(time.ticks_ms(), ir_clear_time) / 1000
            if elapsed >= IR_CLOSE_DELAY:
                if ir_sensor.value() != 0:
                    ir_servo.duty(IR_DUTY_CLOSE); ir_last_state = "clear"
                    ir_waiting_close = False; ir_clear_time = None
                else:
                    ir_waiting_close = False; ir_clear_time = None

ir_sensors  = [Pin(32, Pin.IN), Pin(35, Pin.IN), Pin(33, Pin.IN)]
TOTAL_SLOTS = 3

def get_available():
    return sum(p.value() for p in ir_sensors)

tm = TM1637(clk=Pin(13), dio=Pin(12))
tm.brightness(1)

def update_display():
    available = get_available()
    tm.show(list("{:0>4}".format(available)))
    return available

i2c = I2C(0, sda=Pin(25), scl=Pin(26), freq=400000)
lcd = LCD(i2c, addr=0x27, rows=2, cols=16)
lcd_last_update = 0
LCD_INTERVAL_MS = 2000

lcd.clear()
lcd.move_to(0, 0)
lcd.print("Welcome !       ")

last_lcd_row1 = ""

def lcd_update(available, temp, hum):
    global last_lcd_row1
    try:
        if temp is not None and hum is not None:
            new_row1 = "S:{}/{}  T:{}C H:{}%".format(available, TOTAL_SLOTS, temp, hum)[:16]
        else:
            new_row1 = "S:{}/{}  T:--C H:--%".format(available, TOTAL_SLOTS)[:16]
        if new_row1 != last_lcd_row1:
            last_lcd_row1 = new_row1
            lcd.move_to(0, 1)
            lcd.print(new_row1)
    except Exception as e:
        print("LCD error:", e)

TRIG = Pin(17, Pin.OUT)
ECHO = Pin(16, Pin.IN)
DETECT_CM      = 10
AUTO_CLOSE_SEC = 5

def get_distance():
    TRIG.value(0); time.sleep_us(5)
    TRIG.value(1); time.sleep_us(10)
    TRIG.value(0)
    t = time.ticks_us()
    while ECHO.value() == 0:
        if time.ticks_diff(time.ticks_us(), t) > 1000000: return -1
    s = time.ticks_us()
    while ECHO.value() == 1:
        if time.ticks_diff(time.ticks_us(), s) > 1000000: return -2
    return round((time.ticks_diff(time.ticks_us(), s) * 0.0343) / 2, 1)

def send_msg(text):
    try:
        urequests.post(URL + "sendMessage", json={"chat_id": CHAT_ID, "text": text}).close()
        print("Sent:", text)
    except Exception as e:
        print("Send error:", e)

# ==============================
# FORCE BOTH SERVOS CLOSED ON BOOT
# ==============================
print("Boot: Closing all gates...")
servo.duty(DUTY_CLOSE)
ir_servo.duty(IR_DUTY_CLOSE)
time.sleep(1)
print("Boot: Gates closed!")

wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASS)
print("Connecting WiFi...")
while not wifi.isconnected():
    time.sleep(1)
ip = wifi.ifconfig()[0]
print("WiFi Ready:", ip)

print("Skipping old messages...")
last_id = 0
try:
    r = urequests.get(URL + "getUpdates?offset=-1&timeout=0", timeout=5)
    if r.status_code == 200:
        data = r.json(); r.close()
        results = data.get("result", [])
        if results:
            last_id = results[-1]["update_id"]
except: pass

gate_open        = False
full_notified    = False
last_detect_time = None
cached_temp      = None
cached_hum       = None
last_dht_time    = 0
DHT_INTERVAL_MS  = 10000
last_tg_time     = 0
TG_INTERVAL_MS   = 5000
last_dist        = -1

available = update_display()
print("Boot — Slots:", available, "/", TOTAL_SLOTS)

while True:
    try:
        handle_ir_servo()
        available = update_display()
        occupied  = TOTAL_SLOTS - available

        if time.ticks_diff(time.ticks_ms(), lcd_last_update) >= LCD_INTERVAL_MS:
            lcd_last_update = time.ticks_ms()
            lcd_update(available, cached_temp, cached_hum)

        if time.ticks_diff(time.ticks_ms(), last_dht_time) >= DHT_INTERVAL_MS:
            try:
                dht_sensor.measure()
                cached_temp   = dht_sensor.temperature()
                cached_hum    = dht_sensor.humidity()
                last_dht_time = time.ticks_ms()
            except: pass

        if available == 0 and gate_open:
            set_gate(DUTY_CLOSE); gate_open = False; last_detect_time = None
            send_msg("Parking FULL\nGate auto CLOSED\nOccupied: {}/{}".format(occupied, TOTAL_SLOTS))

        dist      = get_distance()
        last_dist = dist
        print("Dist:", dist, "| Slots:", available, "/", TOTAL_SLOTS, "| Gate:", "OPEN" if gate_open else "CLOSED")

        if dist > 0 and dist < DETECT_CM:
            last_detect_time = time.ticks_ms()
            if available > 0:
                if not gate_open:
                    set_gate(DUTY_OPEN); gate_open = True; full_notified = False
                    send_msg("Vehicle detected {}cm\nGate OPEN\nAvailable: {}/{}".format(dist, available, TOTAL_SLOTS))
            else:
                if not full_notified:
                    send_msg("Vehicle detected {}cm\nParking FULL\nGate CLOSED".format(dist))
                    full_notified = True
        else:
            if gate_open and last_detect_time is not None:
                elapsed = time.ticks_diff(time.ticks_ms(), last_detect_time) / 1000
                if elapsed >= AUTO_CLOSE_SEC:
                    set_gate(DUTY_CLOSE); gate_open = False
                    last_detect_time = None; full_notified = False
                    send_msg("Gate CLOSED automatically")

        if time.ticks_diff(time.ticks_ms(), last_tg_time) >= TG_INTERVAL_MS:
            last_tg_time = time.ticks_ms()
            try:
                r = urequests.get(URL + "getUpdates?offset={}&timeout=0".format(last_id + 1), timeout=5)
                if r.status_code == 200:
                    data = r.json(); r.close()
                    for msg in data.get("result", []):
                        last_id      = msg["update_id"]
                        message_data = msg.get("message") or msg.get("edited_message")
                        if message_data and "text" in message_data:
                            text = message_data["text"]
                            print("Telegram:", text)
                            if "/open" in text:
                                if get_available() == 0:
                                    send_msg("Parking FULL - Gate cannot open!")
                                else:
                                    set_gate(DUTY_OPEN)
                                    gate_open        = True
                                    last_detect_time = time.ticks_ms()
                                    full_notified    = False
                                    send_msg("Gate OPENED via Telegram")
                            elif "/close" in text:
                                set_gate(DUTY_CLOSE)
                                gate_open        = False
                                last_detect_time = None
                                send_msg("Gate CLOSED via Telegram")
                            elif "/temp" in text:
                                dht_sensor.measure()
                                send_msg("Temperature: {}C\nHumidity: {}%".format(dht_sensor.temperature(), dht_sensor.humidity()))
                            elif "/slots" in text:
                                a = get_available()
                                send_msg("Available: {}/{}\nOccupied: {}/{}".format(a, TOTAL_SLOTS, TOTAL_SLOTS-a, TOTAL_SLOTS))
                            elif "/status" in text:
                                a = get_available()
                                send_msg("Gate: {}\nAvailable: {}/{}\nIP: {}".format("OPEN" if gate_open else "CLOSED", a, TOTAL_SLOTS, ip))
            except Exception as te:
                print("Telegram error:", te)

    except Exception as e:
        print("Error:", e); time.sleep(1)
