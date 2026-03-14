import network, urequests, time, dht
from machine import Pin, PWM
from tm1637 import TM1637
import machine
import socket

machine.freq(80_000_000)

# ==============================
# SETTINGS
# ==============================
SSID      = "Hen Sarith"
PASS      = "hensarith"
BOT_TOKEN = "8415101738:AAGYO8zwir8sqOhEJwlj0l4KNwHlPmIIywU"
CHAT_ID   = "-5035961178"

BLYNK_TOKEN  = "your_blynk_token_here"
BLYNK_URL    = "https://blynk.cloud/external/api"

URL = "https://api.telegram.org/bot{}/".format(BOT_TOKEN)

# ==============================
# DHT11 SENSOR — PIN 15
# ==============================
dht_sensor = dht.DHT11(Pin(15))

# ==============================
# SERVO 1 — PARKING GATE — PIN 21
# ==============================
servo = PWM(Pin(21), freq=50)

DUTY_CLOSE = 51
DUTY_OPEN  = 99

def set_gate(duty):
    servo.duty(duty)
    print("Parking gate duty:", duty)

# ==============================
# SERVO 2 — IR GATE — PIN 5
# ==============================
ir_servo  = PWM(Pin(5), freq=50)
ir_sensor = Pin(4, Pin.IN)

IR_DUTY_OPEN  = 99
IR_DUTY_CLOSE = 51

ir_servo.duty(IR_DUTY_CLOSE)

ir_last_state      = None
ir_waiting_close   = False
ir_clear_time      = None
IR_CLOSE_DELAY_SEC = 4

def handle_ir_servo():
    global ir_last_state, ir_waiting_close, ir_clear_time

    detected = ir_sensor.value() == 0

    if detected:
        ir_waiting_close = False
        ir_clear_time    = None
        if ir_last_state != "detected":
            ir_servo.duty(IR_DUTY_OPEN)
            print("IR Gate: DETECTED → OPEN (duty {})".format(IR_DUTY_OPEN))
            ir_last_state = "detected"
    else:
        if ir_last_state == "detected" and not ir_waiting_close:
            ir_waiting_close = True
            ir_clear_time    = time.ticks_ms()
            print("IR Gate: Clear → Waiting {}s before closing...".format(IR_CLOSE_DELAY_SEC))

        if ir_waiting_close and ir_clear_time is not None:
            elapsed = time.ticks_diff(time.ticks_ms(), ir_clear_time) / 1000
            if elapsed >= IR_CLOSE_DELAY_SEC:
                if ir_sensor.value() != 0:
                    ir_servo.duty(IR_DUTY_CLOSE)
                    print("IR Gate: Confirmed clear → CLOSED (duty {})".format(IR_DUTY_CLOSE))
                    ir_last_state    = "clear"
                    ir_waiting_close = False
                    ir_clear_time    = None
                else:
                    ir_waiting_close = False
                    ir_clear_time    = None
                    print("IR Gate: Object returned during wait → Staying OPEN")

# ==============================
# IR PARKING SENSORS — PIN 32, 35, 33
# ==============================
ir_sensors  = [Pin(32, Pin.IN), Pin(35, Pin.IN), Pin(33, Pin.IN)]
TOTAL_SLOTS = 3

def get_available():
    return sum(p.value() for p in ir_sensors)

# ==============================
# TM1637 DISPLAY — PIN 13, 12
# ==============================
tm = TM1637(clk=Pin(13), dio=Pin(12))
tm.brightness(1)

def update_display():
    available = get_available()
    tm.show(list("{:0>4}".format(available)))
    return available

# ==============================
# ULTRASONIC SENSOR — PIN 17, 16
# ==============================
TRIG = Pin(17, Pin.OUT)
ECHO = Pin(16, Pin.IN)

DETECT_CM      = 10
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

    end      = time.ticks_us()
    duration = time.ticks_diff(end, start)
    distance = (duration * 0.0343) / 2
    return round(distance, 1)

# ==============================
# WIFI
# ==============================
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASS)

print("Connecting WiFi...")
while not wifi.isconnected():
    time.sleep(1)

ip = wifi.ifconfig()[0]
print("WiFi Ready:", wifi.ifconfig())
print("Web Dashboard: http://{}".format(ip))

# ==============================
# WEB SERVER SETUP (non-blocking)
# ==============================
web_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
web_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
web_server.bind(('', 80))
web_server.listen(1)
web_server.setblocking(False)
print("Web server listening on port 80")

# ==============================
# DASHBOARD HTML PAGE
# ==============================
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Smart Parking</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0d0f12;
    --surface: #161a20;
    --surface2: #1e2430;
    --border: rgba(255,255,255,0.07);
    --accent: #00e5a0;
    --accent2: #3b8bff;
    --warn: #ff9d00;
    --danger: #ff4b4b;
    --text: #e8ecf0;
    --muted: #6b7585;
    --mono: 'Space Mono', monospace;
    --sans: 'DM Sans', sans-serif;
  }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--sans);
    min-height: 100vh;
    padding: 24px 16px 48px;
  }
  header {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 32px;
  }
  .logo-dot {
    width: 10px; height: 10px;
    border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 12px var(--accent);
    animation: pulse 2s ease-in-out infinite;
  }
  @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.5;transform:scale(.7)} }
  h1 { font-family: var(--mono); font-size: 18px; font-weight: 700; letter-spacing: .04em; }
  h1 span { color: var(--accent); }
  .ip-badge {
    margin-left: auto;
    font-family: var(--mono);
    font-size: 11px;
    color: var(--muted);
    background: var(--surface2);
    border: 1px solid var(--border);
    padding: 4px 10px;
    border-radius: 20px;
  }
  .grid { display: grid; gap: 12px; grid-template-columns: 1fr 1fr; }
  .grid-3 { display: grid; gap: 12px; grid-template-columns: repeat(3, 1fr); margin-top: 12px; }
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 20px;
  }
  .card-label {
    font-size: 11px;
    font-family: var(--mono);
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: .08em;
    margin-bottom: 10px;
  }
  .big-num {
    font-family: var(--mono);
    font-size: 48px;
    font-weight: 700;
    line-height: 1;
    color: var(--accent);
  }
  .big-num.warn { color: var(--warn); }
  .big-num.danger { color: var(--danger); }
  .sub { font-size: 13px; color: var(--muted); margin-top: 6px; }
  .gate-badge {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    font-family: var(--mono);
    font-size: 13px;
    font-weight: 700;
    padding: 6px 14px;
    border-radius: 20px;
    margin-top: 8px;
    letter-spacing: .05em;
  }
  .gate-badge.open { background: rgba(0,229,160,.12); color: var(--accent); border: 1px solid rgba(0,229,160,.25); }
  .gate-badge.closed { background: rgba(255,75,75,.10); color: var(--danger); border: 1px solid rgba(255,75,75,.2); }
  .gate-dot { width:7px;height:7px;border-radius:50%;background:currentColor; }
  .gate-dot.open { animation: pulse 1.5s infinite; }
  .slot-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 16px;
    text-align: center;
  }
  .slot-card .slot-id {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--muted);
    margin-bottom: 10px;
    letter-spacing: .06em;
  }
  .slot-icon { font-size: 28px; margin-bottom: 6px; }
  .slot-state {
    font-size: 12px;
    font-family: var(--mono);
    padding: 3px 10px;
    border-radius: 12px;
    display: inline-block;
  }
  .slot-state.free { background: rgba(0,229,160,.12); color: var(--accent); }
  .slot-state.taken { background: rgba(255,75,75,.10); color: var(--danger); }
  .dist-bar-wrap {
    margin-top: 10px;
    height: 4px;
    background: var(--surface2);
    border-radius: 2px;
    overflow: hidden;
  }
  .dist-bar { height: 100%; border-radius: 2px; background: var(--accent2); transition: width .4s ease; }
  .section-title {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--muted);
    letter-spacing: .08em;
    text-transform: uppercase;
    margin: 24px 0 10px;
  }
  .btn-row { display: flex; gap: 10px; margin-top: 24px; }
  .btn {
    flex: 1;
    padding: 13px;
    border-radius: 10px;
    font-family: var(--mono);
    font-size: 13px;
    font-weight: 700;
    letter-spacing: .05em;
    border: none;
    cursor: pointer;
    transition: opacity .15s, transform .1s;
  }
  .btn:active { transform: scale(.97); }
  .btn-open { background: var(--accent); color: #000; }
  .btn-close { background: var(--surface2); color: var(--danger); border: 1px solid rgba(255,75,75,.25); }
  .btn:disabled { opacity: .35; cursor: default; }
  .toast {
    position: fixed;
    bottom: 24px; left: 50%;
    transform: translateX(-50%) translateY(80px);
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 10px 20px;
    border-radius: 30px;
    font-size: 13px;
    font-family: var(--mono);
    transition: transform .3s ease;
    z-index: 99;
    white-space: nowrap;
  }
  .toast.show { transform: translateX(-50%) translateY(0); }
  .temp-row { display: flex; gap: 12px; margin-top: 12px; }
  .temp-cell { flex: 1; }
  .temp-val {
    font-family: var(--mono);
    font-size: 28px;
    font-weight: 700;
    color: var(--warn);
  }
  .hum-val { color: var(--accent2); }
  footer {
    margin-top: 40px;
    text-align: center;
    font-size: 11px;
    color: var(--muted);
    font-family: var(--mono);
  }
</style>
</head>
<body>

<header>
  <div class="logo-dot"></div>
  <h1>SMART<span>PARK</span></h1>
  <div class="ip-badge" id="ip-label">loading...</div>
</header>

<div class="grid">
  <div class="card">
    <div class="card-label">Available Slots</div>
    <div class="big-num" id="avail-num">—</div>
    <div class="sub" id="avail-sub">of 3 total</div>
  </div>
  <div class="card">
    <div class="card-label">Parking Gate</div>
    <div id="gate-badge" class="gate-badge closed"><span class="gate-dot"></span><span id="gate-text">CLOSED</span></div>
    <div class="sub" style="margin-top:10px">Ultrasonic: <span id="dist-val" style="font-family:var(--mono);color:var(--text)">—</span> cm</div>
    <div class="dist-bar-wrap"><div class="dist-bar" id="dist-bar" style="width:0%"></div></div>
  </div>
</div>

<div class="section-title">Slot Occupancy</div>
<div class="grid-3" id="slot-grid">
  <div class="slot-card"><div class="slot-id">SLOT 1</div><div class="slot-icon" id="s0-icon">&#128663;</div><div class="slot-state" id="s0-state">—</div></div>
  <div class="slot-card"><div class="slot-id">SLOT 2</div><div class="slot-icon" id="s1-icon">&#128663;</div><div class="slot-state" id="s1-state">—</div></div>
  <div class="slot-card"><div class="slot-id">SLOT 3</div><div class="slot-icon" id="s2-icon">&#128663;</div><div class="slot-state" id="s2-state">—</div></div>
</div>

<div class="section-title">Environment</div>
<div class="card">
  <div class="temp-row">
    <div class="temp-cell">
      <div class="card-label">Temperature</div>
      <div class="temp-val" id="temp-val">—</div>
      <div class="sub">degrees C</div>
    </div>
    <div class="temp-cell">
      <div class="card-label">Humidity</div>
      <div class="temp-val hum-val" id="hum-val">—</div>
      <div class="sub">percent RH</div>
    </div>
  </div>
</div>

<div class="btn-row">
  <button class="btn btn-open" id="btn-open" onclick="gateCmd('open')">OPEN GATE</button>
  <button class="btn btn-close" id="btn-close" onclick="gateCmd('close')">CLOSE GATE</button>
</div>

<footer>Auto-refreshes every 2 seconds &bull; SmartPark ESP32</footer>
<div class="toast" id="toast"></div>

<script>
var POLL_MS = 2000;
var timer;

function showToast(msg) {
  var t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(function(){ t.classList.remove('show'); }, 2500);
}

function gateCmd(cmd) {
  clearTimeout(timer);
  document.getElementById('btn-open').disabled = true;
  document.getElementById('btn-close').disabled = true;
  fetch('/cmd?action=' + cmd)
    .then(function(r){ return r.json(); })
    .then(function(d){
      showToast(d.message || 'Done');
      fetchStatus();
    })
    .catch(function(){ showToast('Error sending command'); fetchStatus(); });
}

function fetchStatus() {
  fetch('/api/status')
    .then(function(r){ return r.json(); })
    .then(function(d){ updateUI(d); })
    .catch(function(){})
    .finally(function(){
      document.getElementById('btn-open').disabled = false;
      document.getElementById('btn-close').disabled = false;
      timer = setTimeout(fetchStatus, POLL_MS);
    });
}

function updateUI(d) {
  var avail = d.available;
  var total = d.total;

  var numEl = document.getElementById('avail-num');
  numEl.textContent = avail;
  numEl.className = 'big-num' + (avail === 0 ? ' danger' : avail === 1 ? ' warn' : '');

  document.getElementById('avail-sub').textContent = 'of ' + total + ' total — ' + (total - avail) + ' occupied';

  var gOpen = d.gate_open;
  var badge = document.getElementById('gate-badge');
  var dot   = badge.querySelector('.gate-dot');
  badge.className = 'gate-badge ' + (gOpen ? 'open' : 'closed');
  dot.className   = 'gate-dot ' + (gOpen ? 'open' : '');
  document.getElementById('gate-text').textContent = gOpen ? 'OPEN' : 'CLOSED';

  var dist = d.distance;
  document.getElementById('dist-val').textContent = dist > 0 ? dist : '—';
  var pct = dist > 0 ? Math.min(100, Math.max(0, (1 - dist / 200) * 100)) : 0;
  document.getElementById('dist-bar').style.width = pct + '%';

  var slots = d.slots;
  for (var i = 0; i < 3; i++) {
    var free = slots[i];
    var icon  = document.getElementById('s' + i + '-icon');
    var state = document.getElementById('s' + i + '-state');
    icon.innerHTML  = free ? '&#x1F7E2;' : '&#x1F697;';
    state.textContent = free ? 'FREE' : 'TAKEN';
    state.className = 'slot-state ' + (free ? 'free' : 'taken');
  }

  document.getElementById('temp-val').textContent = d.temp !== null ? d.temp : '—';
  document.getElementById('hum-val').textContent  = d.hum  !== null ? d.hum  : '—';

  document.getElementById('ip-label').textContent = d.ip || '';
}

fetchStatus();
</script>
</body>
</html>"""

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
    r = urequests.get(URL + "getUpdates?offset=-1&timeout=0", timeout=5)
    if r.status_code == 200:
        data    = r.json()
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
gate_open        = False
full_notified    = False
last_detect_time = None

# DHT cache (updated every 10s to avoid sensor fatigue)
cached_temp      = None
cached_hum       = None
last_dht_time    = 0
DHT_INTERVAL_MS  = 10000

# Telegram poll interval — every 5s, non-blocking (timeout=0)
last_tg_time     = 0
TG_INTERVAL_MS   = 5000

# Blynk push interval — send sensor data every 3s
last_blynk_time  = 0
BLYNK_INTERVAL_MS = 3000

# Blynk gate button poll — check V5 every 1s
last_blynk_btn_time = 0
BLYNK_BTN_MS        = 1000
last_blynk_btn_val  = -1

available = update_display()

print("Boot — Slots available:", available, "/", TOTAL_SLOTS)
print("Servo 1 (Parking Gate) → GPIO21 | Servo 2 (IR Gate) → GPIO5 | IR Sensor → GPIO4")
print("Bot running...")

# ==============================
# WEB SERVER HANDLER (non-blocking)
# ==============================
def build_json():
    slots_state = [ir_sensors[i].value() for i in range(3)]
    return (
        '{{"available":{a},"total":{t},"gate_open":{g},"distance":{d},'
        '"slots":[{s0},{s1},{s2}],"temp":{tm},"hum":{h},"ip":"{ip}"}}'
    ).format(
        a  = get_available(),
        t  = TOTAL_SLOTS,
        g  = "true" if gate_open else "false",
        d  = last_dist if last_dist else -1,
        s0 = slots_state[0],
        s1 = slots_state[1],
        s2 = slots_state[2],
        tm = cached_temp if cached_temp is not None else "null",
        h  = cached_hum  if cached_hum  is not None else "null",
        ip = ip
    )

def handle_web():
    global gate_open, last_detect_time, full_notified

    try:
        conn, addr = web_server.accept()
        conn.settimeout(2.0)
        try:
            request = conn.recv(512).decode('utf-8')
        except:
            conn.close()
            return

        first_line = request.split('\r\n')[0] if '\r\n' in request else request[:80]
        path = first_line.split(' ')[1] if ' ' in first_line else '/'

        if path == '/' or path == '/index.html':
            resp = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n" + DASHBOARD_HTML
            conn.sendall(resp.encode())

        elif path == '/api/status':
            body = build_json()
            resp = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n" + body
            conn.sendall(resp.encode())

        elif path.startswith('/cmd'):
            action  = 'open' if 'action=open' in path else 'close'
            avail   = get_available()
            message = ""

            if action == 'open':
                if avail == 0:
                    message = "Parking FULL — cannot open"
                else:
                    set_gate(DUTY_OPEN)
                    gate_open        = True
                    last_detect_time = time.ticks_ms()
                    full_notified    = False
                    message          = "Gate opened via web"
                    send_msg("Gate OPENED via web dashboard")
            else:
                set_gate(DUTY_CLOSE)
                gate_open        = False
                last_detect_time = None
                message          = "Gate closed via web"
                send_msg("Gate CLOSED via web dashboard")

            body = '{{"ok":true,"message":"{}"}}'.format(message)
            resp = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n" + body
            conn.sendall(resp.encode())

        else:
            conn.sendall(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\nNot Found")

        conn.close()

    except OSError:
        pass  # No client waiting — normal for non-blocking

# ==============================
# BLYNK HTTPS API HELPERS
# ==============================
def blynk_update(pin, value):
    """Push one value to a Blynk virtual pin (fire-and-forget)."""
    try:
        url = "{}/update?token={}&v{}={}".format(BLYNK_URL, BLYNK_TOKEN, pin, value)
        r = urequests.get(url, timeout=4)
        r.close()
    except Exception as e:
        print("Blynk update error (V{}): {}".format(pin, e))

def blynk_get(pin):
    """Read one virtual pin value from Blynk. Returns string or None."""
    try:
        url = "{}/get?token={}&v{}".format(BLYNK_URL, BLYNK_TOKEN, pin)
        r = urequests.get(url, timeout=4)
        if r.status_code == 200:
            val = r.text.strip().strip('[""]')
            r.close()
            return val
        r.close()
    except Exception as e:
        print("Blynk get error (V{}): {}".format(pin, e))
    return None

def blynk_push_sensors():
    """Push all sensor data to Blynk virtual pins."""
    a = get_available()
    blynk_update(0, a)                                          # V0 — available slots
    if cached_temp is not None:
        blynk_update(1, cached_temp)                            # V1 — temperature
    if cached_hum is not None:
        blynk_update(2, cached_hum)                             # V2 — humidity
    blynk_update(3, 1 if gate_open else 0)                     # V3 — gate status
    if last_dist and last_dist > 0:
        blynk_update(4, last_dist)                              # V4 — distance

def blynk_check_gate_btn():
    """Read V5 from Blynk — button widget controls the gate."""
    global gate_open, last_detect_time, full_notified, last_blynk_btn_val
    val = blynk_get(5)
    if val is None:
        return
    try:
        btn = int(float(val))
    except:
        return
    if btn == last_blynk_btn_val:
        return                      # no change, skip
    last_blynk_btn_val = btn
    if btn == 1:
        if get_available() == 0:
            blynk_update(3, 0)
            send_msg("Blynk: Parking FULL — gate not opened")
        else:
            set_gate(DUTY_OPEN)
            gate_open        = True
            last_detect_time = time.ticks_ms()
            full_notified    = False
            print("Blynk: Gate OPENED")
            send_msg("Gate OPENED via Blynk")
    else:
        set_gate(DUTY_CLOSE)
        gate_open        = False
        last_detect_time = None
        print("Blynk: Gate CLOSED")
        send_msg("Gate CLOSED via Blynk")

# ==============================
# MAIN LOOP
# ==============================
last_dist = -1

while True:

    try:

        # --------------------------
        # SERVO 2 — IR Gate (fully independent)
        # --------------------------
        handle_ir_servo()

        # --------------------------
        # Update Parking Display
        # --------------------------
        available = update_display()
        occupied  = TOTAL_SLOTS - available

        # --------------------------
        # DHT11 — Read every 10s
        # --------------------------
        if time.ticks_diff(time.ticks_ms(), last_dht_time) >= DHT_INTERVAL_MS:
            try:
                dht_sensor.measure()
                cached_temp = dht_sensor.temperature()
                cached_hum  = dht_sensor.humidity()
                last_dht_time = time.ticks_ms()
            except:
                pass

        # --------------------------
        # Auto close if full
        # --------------------------
        if available == 0 and gate_open:
            set_gate(DUTY_CLOSE)
            gate_open        = False
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
        last_dist = dist

        print("Distance:", dist,
              "| Slots:", available, "/", TOTAL_SLOTS,
              "| Gate:", "OPEN" if gate_open else "CLOSED")

        if dist > 0 and dist < DETECT_CM:
            last_detect_time = time.ticks_ms()

            if available > 0:
                if not gate_open:
                    set_gate(DUTY_OPEN)
                    gate_open     = True
                    full_notified = False
                    send_msg(
                        "Vehicle detected {}cm\n"
                        "Gate OPEN\n"
                        "Available: {}/{}".format(dist, available, TOTAL_SLOTS)
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
                elapsed = time.ticks_diff(time.ticks_ms(), last_detect_time) / 1000
                if elapsed >= AUTO_CLOSE_SEC:
                    set_gate(DUTY_CLOSE)
                    gate_open        = False
                    last_detect_time = None
                    full_notified    = False
                    send_msg("Gate CLOSED automatically")

        # --------------------------
        # WEB SERVER — handle one request per loop
        # --------------------------
        handle_web()

        # --------------------------
        # BLYNK — push sensor data every 3s
        # --------------------------
        if time.ticks_diff(time.ticks_ms(), last_blynk_time) >= BLYNK_INTERVAL_MS:
            last_blynk_time = time.ticks_ms()
            blynk_push_sensors()

        # --------------------------
        # BLYNK — check gate button (V5) every 1s
        # --------------------------
        if time.ticks_diff(time.ticks_ms(), last_blynk_btn_time) >= BLYNK_BTN_MS:
            last_blynk_btn_time = time.ticks_ms()
            blynk_check_gate_btn()

        # --------------------------
        # TELEGRAM — poll every 5s, timeout=0 (non-blocking)
        # Inbound: /temp /slots /status only — gate control via web dashboard
        # --------------------------
        if time.ticks_diff(time.ticks_ms(), last_tg_time) >= TG_INTERVAL_MS:
            last_tg_time = time.ticks_ms()
            try:
                r = urequests.get(
                    URL + "getUpdates?offset={}&timeout=0".format(last_id + 1),
                    timeout=5
                )
                if r.status_code == 200:
                    data = r.json()
                    r.close()

                    for msg in data.get("result", []):
                        last_id      = msg["update_id"]
                        message_data = msg.get("message") or msg.get("edited_message")

                        if message_data and "text" in message_data:
                            text = message_data["text"]
                            print("Telegram:", text)

                            if "/temp" in text:
                                dht_sensor.measure()
                                t = dht_sensor.temperature()
                                h = dht_sensor.humidity()
                                send_msg("Temperature: {}°C\nHumidity: {}%".format(t, h))

                            elif "/slots" in text:
                                a = get_available()
                                send_msg(
                                    "Parking Slots\n"
                                    "Available: {}/{}\n"
                                    "Occupied: {}/{}".format(a, TOTAL_SLOTS, TOTAL_SLOTS - a, TOTAL_SLOTS)
                                )

                            elif "/status" in text:
                                a = get_available()
                                send_msg(
                                    "Gate: {}\nAvailable: {}/{}\n"
                                    "Control gate via web: http://{}".format(
                                        "OPEN" if gate_open else "CLOSED",
                                        a, TOTAL_SLOTS, ip
                                    )
                                )

                            elif "/open" in text or "/close" in text:
                                send_msg(
                                    "Gate control moved to web dashboard\n"
                                    "http://{}".format(ip)
                                )

            except Exception as te:
                print("Telegram poll error:", te)

    except Exception as e:
        print("Error:", e)
        time.sleep(1)
