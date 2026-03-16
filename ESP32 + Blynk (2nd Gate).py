import network, urequests, time, dht
from machine import Pin, PWM, I2C
from tm1637 import TM1637
from lcd_i2c import LCD
import machine

machine.freq(240_000_000)

SSID        = "AUPP Wifi"
PASS        = ""
BLYNK_TOKEN = "YboG5Ey3U62iIilkE2vPj9xTHUqzu0TP"
BLYNK_URL   = "https://blynk.cloud/external/api"

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

# Manual override for Gate 2
ir_gate_manual   = False

def handle_ir_servo():
    global ir_last_state, ir_waiting_close, ir_clear_time, ir_gate_manual

    # If manually overridden via Blynk, skip auto IR logic
    if ir_gate_manual:
        return

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

def blynk_update(pin, value):
    try:
        r = urequests.get("{}/update?token={}&v{}={}".format(BLYNK_URL, BLYNK_TOKEN, pin, value), timeout=4)
        r.close()
    except Exception as e:
        print("Blynk update error V{}:".format(pin), e)

def blynk_get(pin):
    try:
        r = urequests.get("{}/get?token={}&v{}".format(BLYNK_URL, BLYNK_TOKEN, pin), timeout=4)
        if r.status_code == 200:
            val = r.text.strip().strip('[""]'); r.close(); return val
        r.close()
    except Exception as e:
        print("Blynk get error V{}:".format(pin), e)
    return None

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
print("WiFi Ready:", wifi.ifconfig()[0])

gate_open            = False
full_notified        = False
last_detect_time     = None
cached_temp          = None
cached_hum           = None
last_dht_time        = 0
DHT_INTERVAL_MS      = 10000
last_blynk_time      = 0
BLYNK_INTERVAL_MS    = 3000
last_blynk_btn_time  = 0
BLYNK_BTN_MS         = 1000
last_blynk_btn_val   = -1   # V5 — Gate 1 button
last_blynk_btn2_val  = -1   # V6 — Gate 2 button
last_dist            = -1

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

        dist      = get_distance()
        last_dist = dist
        print("Dist:", dist, "| Slots:", available, "/", TOTAL_SLOTS, "| Gate:", "OPEN" if gate_open else "CLOSED")

        if dist > 0 and dist < DETECT_CM:
            last_detect_time = time.ticks_ms()
            if available > 0:
                if not gate_open:
                    set_gate(DUTY_OPEN); gate_open = True; full_notified = False
            else:
                full_notified = True
        else:
            if gate_open and last_detect_time is not None:
                elapsed = time.ticks_diff(time.ticks_ms(), last_detect_time) / 1000
                if elapsed >= AUTO_CLOSE_SEC:
                    set_gate(DUTY_CLOSE); gate_open = False
                    last_detect_time = None; full_notified = False

        # --------------------------
        # Blynk push sensors every 3s
        # V0=slots  V1=temp  V2=hum  V3=gate1  V4=dist  V7=gate2
        # --------------------------
        if time.ticks_diff(time.ticks_ms(), last_blynk_time) >= BLYNK_INTERVAL_MS:
            last_blynk_time = time.ticks_ms()
            blynk_update(0, get_available())
            if cached_temp is not None: blynk_update(1, cached_temp)
            if cached_hum  is not None: blynk_update(2, cached_hum)
            blynk_update(3, 1 if gate_open else 0)
            if last_dist > 0: blynk_update(4, last_dist)
            # V7 — Gate 2 status (1=open if IR detected or manual, 0=closed)
            gate2_open = ir_gate_manual or ir_last_state == "detected"
            blynk_update(7, 1 if gate2_open else 0)

        # --------------------------
        # Blynk check V5 (Gate 1) + V6 (Gate 2) every 1s
        # --------------------------
        if time.ticks_diff(time.ticks_ms(), last_blynk_btn_time) >= BLYNK_BTN_MS:
            last_blynk_btn_time = time.ticks_ms()

            # --- V5 Gate 1 --- (unchanged behaviour)
            val = blynk_get(5)
            if val is not None:
                try:
                    btn = int(float(val))
                    if btn != last_blynk_btn_val:
                        last_blynk_btn_val = btn
                        if btn == 1:
                            if get_available() == 0:
                                blynk_update(3, 0)
                                print("Blynk: FULL - gate not opened")
                            else:
                                set_gate(DUTY_OPEN)
                                gate_open        = True
                                last_detect_time = time.ticks_ms()
                                full_notified    = False
                                blynk_update(3, 1)
                                print("Blynk: Gate 1 OPENED")
                        else:
                            set_gate(DUTY_CLOSE)
                            gate_open        = False
                            last_detect_time = None
                            blynk_update(3, 0)
                            print("Blynk: Gate 1 CLOSED")
                except: pass

            # --- V6 Gate 2 --- (new)
            val2 = blynk_get(6)
            if val2 is not None:
                try:
                    btn2 = int(float(val2))
                    if btn2 != last_blynk_btn2_val:
                        last_blynk_btn2_val = btn2
                        if btn2 == 1:
                            ir_servo.duty(IR_DUTY_OPEN)
                            ir_gate_manual   = True
                            ir_last_state    = "detected"
                            ir_waiting_close = False
                            blynk_update(7, 1)
                            print("Blynk: Gate 2 OPENED")
                        else:
                            ir_servo.duty(IR_DUTY_CLOSE)
                            ir_gate_manual   = False
                            ir_last_state    = "clear"
                            ir_waiting_close = False
                            ir_clear_time    = None
                            blynk_update(7, 0)
                            print("Blynk: Gate 2 CLOSED")
                except: pass

    except Exception as e:
        print("Error:", e); time.sleep(1)
