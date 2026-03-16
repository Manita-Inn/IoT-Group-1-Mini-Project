import network, time, dht
from machine import Pin, PWM, I2C
from tm1637 import TM1637
from lcd_i2c import LCD
import machine
import socket

machine.freq(240_000_000)

SSID = "AUPP Wifi"
PASS = ""

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
print("Web Dashboard: http://{}".format(ip))

web_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
web_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
web_server.bind(('', 80))
web_server.listen(1)
web_server.setblocking(False)

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
    --bg: #0d0f12; --surface: #161a20; --surface2: #1e2430;
    --border: rgba(255,255,255,0.07); --accent: #00e5a0; --accent2: #3b8bff;
    --warn: #ff9d00; --danger: #ff4b4b; --text: #e8ecf0; --muted: #6b7585;
    --mono: 'Space Mono', monospace; --sans: 'DM Sans', sans-serif;
  }
  body { background: var(--bg); color: var(--text); font-family: var(--sans); min-height: 100vh; padding: 24px 16px 48px; }
  header { display: flex; align-items: center; gap: 14px; margin-bottom: 32px; }
  .logo-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 12px var(--accent); animation: pulse 2s ease-in-out infinite; }
  @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.5;transform:scale(.7)} }
  h1 { font-family: var(--mono); font-size: 18px; font-weight: 700; }
  h1 span { color: var(--accent); }
  .ip-badge { margin-left: auto; font-family: var(--mono); font-size: 11px; color: var(--muted); background: var(--surface2); border: 1px solid var(--border); padding: 4px 10px; border-radius: 20px; }
  .grid { display: grid; gap: 12px; grid-template-columns: 1fr 1fr; }
  .grid-3 { display: grid; gap: 12px; grid-template-columns: repeat(3, 1fr); margin-top: 12px; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 20px; }
  .card-label { font-size: 11px; font-family: var(--mono); color: var(--muted); text-transform: uppercase; letter-spacing: .08em; margin-bottom: 10px; }
  .big-num { font-family: var(--mono); font-size: 48px; font-weight: 700; line-height: 1; color: var(--accent); }
  .big-num.warn { color: var(--warn); } .big-num.danger { color: var(--danger); }
  .sub { font-size: 13px; color: var(--muted); margin-top: 6px; }
  .gate-badge { display: inline-flex; align-items: center; gap: 7px; font-family: var(--mono); font-size: 13px; font-weight: 700; padding: 6px 14px; border-radius: 20px; margin-top: 8px; }
  .gate-badge.open { background: rgba(0,229,160,.12); color: var(--accent); border: 1px solid rgba(0,229,160,.25); }
  .gate-badge.closed { background: rgba(255,75,75,.10); color: var(--danger); border: 1px solid rgba(255,75,75,.2); }
  .gate-dot { width:7px;height:7px;border-radius:50%;background:currentColor; }
  .gate-dot.open { animation: pulse 1.5s infinite; }
  .slot-card { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 16px; text-align: center; }
  .slot-card .slot-id { font-family: var(--mono); font-size: 11px; color: var(--muted); margin-bottom: 10px; }
  .slot-icon { font-size: 28px; margin-bottom: 6px; }
  .slot-state { font-size: 12px; font-family: var(--mono); padding: 3px 10px; border-radius: 12px; display: inline-block; }
  .slot-state.free { background: rgba(0,229,160,.12); color: var(--accent); }
  .slot-state.taken { background: rgba(255,75,75,.10); color: var(--danger); }
  .dist-bar-wrap { margin-top: 10px; height: 4px; background: var(--surface2); border-radius: 2px; overflow: hidden; }
  .dist-bar { height: 100%; border-radius: 2px; background: var(--accent2); transition: width .4s ease; }
  .section-title { font-family: var(--mono); font-size: 11px; color: var(--muted); letter-spacing: .08em; text-transform: uppercase; margin: 24px 0 10px; }
  .btn-row { display: flex; gap: 10px; margin-top: 24px; }
  .btn { flex: 1; padding: 13px; border-radius: 10px; font-family: var(--mono); font-size: 13px; font-weight: 700; border: none; cursor: pointer; transition: opacity .15s, transform .1s; }
  .btn:active { transform: scale(.97); }
  .btn-open { background: var(--accent); color: #000; }
  .btn-close { background: var(--surface2); color: var(--danger); border: 1px solid rgba(255,75,75,.25); }
  .btn:disabled { opacity: .35; cursor: default; }
  .toast { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%) translateY(80px); background: var(--surface2); border: 1px solid var(--border); color: var(--text); padding: 10px 20px; border-radius: 30px; font-size: 13px; font-family: var(--mono); transition: transform .3s ease; z-index: 99; white-space: nowrap; }
  .toast.show { transform: translateX(-50%) translateY(0); }
  .temp-row { display: flex; gap: 12px; margin-top: 12px; }
  .temp-cell { flex: 1; }
  .temp-val { font-family: var(--mono); font-size: 28px; font-weight: 700; color: var(--warn); }
  .hum-val { color: var(--accent2); }
  footer { margin-top: 40px; text-align: center; font-size: 11px; color: var(--muted); font-family: var(--mono); }
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
    <div class="temp-cell"><div class="card-label">Temperature</div><div class="temp-val" id="temp-val">—</div><div class="sub">degrees C</div></div>
    <div class="temp-cell"><div class="card-label">Humidity</div><div class="temp-val hum-val" id="hum-val">—</div><div class="sub">percent RH</div></div>
  </div>
</div>
<div class="btn-row">
  <button class="btn btn-open" id="btn-open" onclick="gateCmd('open')">OPEN GATE</button>
  <button class="btn btn-close" id="btn-close" onclick="gateCmd('close')">CLOSE GATE</button>
</div>
<footer>Auto-refreshes every 2 seconds &bull; SmartPark ESP32</footer>
<div class="toast" id="toast"></div>
<script>
var POLL_MS=2000,timer;
function showToast(msg){var t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');setTimeout(function(){t.classList.remove('show');},2500);}
function gateCmd(cmd){
  clearTimeout(timer);
  document.getElementById('btn-open').disabled=true;
  document.getElementById('btn-close').disabled=true;
  fetch('/cmd?action='+cmd)
    .then(function(r){return r.json();})
    .then(function(d){showToast(d.message||'Done');fetchStatus();})
    .catch(function(){showToast('Error sending command');fetchStatus();});
}
function fetchStatus(){
  fetch('/api/status')
    .then(function(r){return r.json();})
    .then(function(d){updateUI(d);})
    .catch(function(){})
    .finally(function(){
      document.getElementById('btn-open').disabled=false;
      document.getElementById('btn-close').disabled=false;
      timer=setTimeout(fetchStatus,POLL_MS);
    });
}
function updateUI(d){
  var avail=d.available,total=d.total,numEl=document.getElementById('avail-num');
  numEl.textContent=avail;
  numEl.className='big-num'+(avail===0?' danger':avail===1?' warn':'');
  document.getElementById('avail-sub').textContent='of '+total+' total — '+(total-avail)+' occupied';
  var gOpen=d.gate_open,badge=document.getElementById('gate-badge'),dot=badge.querySelector('.gate-dot');
  badge.className='gate-badge '+(gOpen?'open':'closed');
  dot.className='gate-dot '+(gOpen?'open':'');
  document.getElementById('gate-text').textContent=gOpen?'OPEN':'CLOSED';
  var dist=d.distance;
  document.getElementById('dist-val').textContent=dist>0?dist:'—';
  var pct=dist>0?Math.min(100,Math.max(0,(1-dist/200)*100)):0;
  document.getElementById('dist-bar').style.width=pct+'%';
  for(var i=0;i<3;i++){
    var free=d.slots[i];
    document.getElementById('s'+i+'-icon').innerHTML=free?'&#x1F7E2;':'&#x1F697;';
    document.getElementById('s'+i+'-state').textContent=free?'FREE':'TAKEN';
    document.getElementById('s'+i+'-state').className='slot-state '+(free?'free':'taken');
  }
  document.getElementById('temp-val').textContent=d.temp!==null?d.temp:'—';
  document.getElementById('hum-val').textContent=d.hum!==null?d.hum:'—';
  document.getElementById('ip-label').textContent=d.ip||'';
}
fetchStatus();
</script>
</body>
</html>"""

gate_open        = False
full_notified    = False
last_detect_time = None
cached_temp      = None
cached_hum       = None
last_dht_time    = 0
DHT_INTERVAL_MS  = 10000
last_dist        = -1

available = update_display()
print("Boot — Slots:", available, "/", TOTAL_SLOTS)

def build_json():
    slots_state = [ir_sensors[i].value() for i in range(3)]
    return ('{{"available":{a},"total":{t},"gate_open":{g},"distance":{d},"slots":[{s0},{s1},{s2}],"temp":{tm},"hum":{h},"ip":"{ip}"}}').format(
        a=get_available(), t=TOTAL_SLOTS,
        g="true" if gate_open else "false",
        d=last_dist if last_dist else -1,
        s0=slots_state[0], s1=slots_state[1], s2=slots_state[2],
        tm=cached_temp if cached_temp is not None else "null",
        h=cached_hum if cached_hum is not None else "null", ip=ip)

def handle_web():
    global gate_open, last_detect_time, full_notified
    try:
        conn, addr = web_server.accept()
        conn.settimeout(2.0)
        try:
            request = conn.recv(512).decode('utf-8')
        except:
            conn.close(); return
        first_line = request.split('\r\n')[0] if '\r\n' in request else request[:80]
        path = first_line.split(' ')[1] if ' ' in first_line else '/'

        if path == '/' or path == '/index.html':
            conn.sendall(("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n" + DASHBOARD_HTML).encode())

        elif path == '/api/status':
            conn.sendall(("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n" + build_json()).encode())

        elif path.startswith('/cmd'):
            action = 'open' if 'action=open' in path else 'close'
            avail  = get_available()
            if action == 'open':
                if avail == 0:
                    msg = "Parking FULL - cannot open"
                else:
                    set_gate(DUTY_OPEN)
                    gate_open        = True
                    last_detect_time = time.ticks_ms()
                    full_notified    = False
                    msg              = "Gate OPENED"
                    print("Web: Gate OPENED")
            else:
                set_gate(DUTY_CLOSE)
                gate_open        = False
                last_detect_time = None
                msg              = "Gate CLOSED"
                print("Web: Gate CLOSED")
            conn.sendall(("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n" + '{{"ok":true,"message":"{}"}}'.format(msg)).encode())
        else:
            conn.sendall(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\nNot Found")
        conn.close()
    except OSError:
        pass

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

        handle_web()

    except Exception as e:
        print("Error:", e); time.sleep(1)
