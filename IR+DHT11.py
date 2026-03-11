import network, urequests, time, machine, dht
from machine import Pin

machine.freq(80_000_000)

# --- WiFi & Telegram ---
SSID      = "Hen Sarith"
PASS      = "hensarith"
BOT_TOKEN = "8415101738:AAGYO8zwir8sqOhEJwlj0l4KNwHlPmIEywU"
CHAT_ID   = "-5035961178"

# --- Sensors ---
ir_sensors = [Pin(14, Pin.IN), Pin(33, Pin.IN), Pin(34, Pin.IN)]
dht_sensor = dht.DHT11(Pin(12))  # Use separate pin from IR sensors

# --- Connect WiFi ---
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASS)
print("Connecting to WiFi...")
while not wifi.isconnected():
    time.sleep(0.5)
    print(".", end="")
print("\nWiFi connected! IP:", wifi.ifconfig()[0])

# --- Telegram URLs ---
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"
GET_URL  = BASE_URL + "getUpdates"
SEND_URL = BASE_URL + "sendMessage"
last_update_id = 0

def send_message(text):
    try:
        r = urequests.get(f"{SEND_URL}?chat_id={CHAT_ID}&text={text}")
        print("Sent:", text)
        r.close()
    except Exception as e:
        print("Telegram Error:", e)

# --- Main loop ---
while True:
    try:
        # --- Check Telegram messages ---
        r = urequests.get(f"{GET_URL}?offset={last_update_id + 1}&timeout=5")
        if r.status_code == 200:
            data = r.json()
            r.close()
            for msg in data.get("result", []):
                last_update_id = msg["update_id"]
                message_data = msg.get("message") or msg.get("edited_message")
                if message_data and "text" in message_data:
                    text = message_data["text"].lower()

                    # /slots command
                    if "/slots" in text:
                        count = sum([p.value() for p in ir_sensors])
                        reply = f"Slots Available: {count}/3"
                        print(">>> Terminal Count:", count)
                        send_message(reply)

                    # /temp command
                    elif "/temp" in text:
                        try:
                            dht_sensor.measure()
                            t, h = dht_sensor.temperature(), dht_sensor.humidity()
                            reply = f"Temp: {t}C, Hum: {h}%"
                            print(f">>> Terminal: {t}C, {h}%")
                            send_message(reply)
                        except Exception as e:
                            print("DHT11 Error:", e)
                            send_message("Error reading DHT11 sensor!")

        else:
            r.close()
    except Exception as e:
        print("Error:", e)

    time.sleep(1)
