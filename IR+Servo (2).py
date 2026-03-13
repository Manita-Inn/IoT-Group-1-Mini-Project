from machine import Pin, PWM
import time

# --- Servo Setup ---
servo_pwm = PWM(Pin(5), freq=50)

# --- IR Sensor Setup ---
ir_sensor = Pin(15, Pin.IN)

# --- Calibration ---
DUTY_MIN = 50
DUTY_MAX = 100

# --- IR Duty values ---
DUTY_DETECTED = 100
DUTY_DEFAULT  = 50

# --- Conversion helpers ---
def duty_to_degree(duty):
    return round((duty - DUTY_MIN) * 180 / (DUTY_MAX - DUTY_MIN))

def degree_to_duty(degree):
    return round(DUTY_MIN + degree * (DUTY_MAX - DUTY_MIN) / 180)

# --- Start position ---
current_duty = DUTY_DEFAULT
servo_pwm.duty(current_duty)
time.sleep(1)

print("IR + Servo Manual Control")
print("=" * 40)
print("IR sensor active in background.")
print("Commands:")
print("  '75'   → type any number to set duty directly")
print("  'd90'  → set by degree  (0–180)")
print("  'u75'  → set by duty    (0–1023)")
print("  '+'    → duty +1")
print("  '-'    → duty -1")
print("  '>>'   → degree +1")
print("  '<<'   → degree -1")
print("  'ir'   → toggle IR auto mode ON/OFF")
print("  'q'    → quit")
print("=" * 40)
print(f"Starting → Duty: {current_duty} | Degree: {duty_to_degree(current_duty)}°")
print(f"IR auto mode: ON")

ir_mode = True
last_state = None

while True:

    # --- IR auto mode ---
    if ir_mode:
        detected = ir_sensor.value() == 0

        if detected and last_state != "detected":
            current_duty = DUTY_DETECTED
            servo_pwm.duty(current_duty)
            print(f"IR: Object DETECTED → Duty: {current_duty} | Degree: {duty_to_degree(current_duty)}°")
            last_state = "detected"

        elif not detected and last_state != "clear":
            print("IR: No object → Waiting 4 seconds before closing...")
            time.sleep(4)
            # Re-check after delay — if object came back, don't close
            if ir_sensor.value() != 0:
                current_duty = DUTY_DEFAULT
                servo_pwm.duty(current_duty)
                print(f"IR: Confirmed clear → Duty: {current_duty} | Degree: {duty_to_degree(current_duty)}°")
                last_state = "clear"
            else:
                print("IR: Object returned during wait → Staying open")

    # --- Manual input (non-blocking) ---
    import select
    import sys
    r, _, _ = select.select([sys.stdin], [], [], 0.1)

    if not r:
        continue

    cmd = sys.stdin.readline().strip()

    if cmd == 'q':
        servo_pwm.deinit()
        print("Servo stopped. Goodbye!")
        break

    elif cmd == 'ir':
        ir_mode = not ir_mode
        last_state = None
        status = "ON" if ir_mode else "OFF"
        print(f"IR auto mode: {status}")

    elif cmd == '+':
        if not ir_mode:
            current_duty = min(1023, current_duty + 1)
            servo_pwm.duty(current_duty)
            print(f"Duty: {current_duty} | Degree: {duty_to_degree(current_duty)}°")
        else:
            print("Turn off IR mode first. Type 'ir' to toggle.")

    elif cmd == '-':
        if not ir_mode:
            current_duty = max(0, current_duty - 1)
            servo_pwm.duty(current_duty)
            print(f"Duty: {current_duty} | Degree: {duty_to_degree(current_duty)}°")
        else:
            print("Turn off IR mode first. Type 'ir' to toggle.")

    elif cmd == '>>':
        if not ir_mode:
            new_degree = min(180, duty_to_degree(current_duty) + 1)
            current_duty = degree_to_duty(new_degree)
            servo_pwm.duty(current_duty)
            print(f"Duty: {current_duty} | Degree: {new_degree}°")
        else:
            print("Turn off IR mode first. Type 'ir' to toggle.")

    elif cmd == '<<':
        if not ir_mode:
            new_degree = max(0, duty_to_degree(current_duty) - 1)
            current_duty = degree_to_duty(new_degree)
            servo_pwm.duty(current_duty)
            print(f"Duty: {current_duty} | Degree: {new_degree}°")
        else:
            print("Turn off IR mode first. Type 'ir' to toggle.")

    elif cmd.startswith('d'):
        if not ir_mode:
            try:
                degree = int(cmd[1:])
                if 0 <= degree <= 180:
                    current_duty = degree_to_duty(degree)
                    servo_pwm.duty(current_duty)
                    print(f"Duty: {current_duty} | Degree: {degree}°")
                else:
                    print("Out of range! Degree must be 0–180.")
            except ValueError:
                print("Invalid degree. Example: d90")
        else:
            print("Turn off IR mode first. Type 'ir' to toggle.")

    elif cmd.startswith('u'):
        if not ir_mode:
            try:
                duty = int(cmd[1:])
                if 0 <= duty <= 1023:
                    current_duty = duty
                    servo_pwm.duty(current_duty)
                    print(f"Duty: {current_duty} | Degree: {duty_to_degree(current_duty)}°")
                else:
                    print("Out of range! Duty must be 0–1023.")
            except ValueError:
                print("Invalid duty. Example: u49")
        else:
            print("Turn off IR mode first. Type 'ir' to toggle.")

    elif cmd.lstrip('-').isdigit():
        if not ir_mode:
            duty = int(cmd)
            if 0 <= duty <= 1023:
                current_duty = duty
                servo_pwm.duty(current_duty)
                print(f"Duty: {current_duty} | Degree: {duty_to_degree(current_duty)}°")
            else:
                print("Out of range! Duty must be 0–1023.")
        else:
            print("Turn off IR mode first. Type 'ir' to toggle.")

    else:
        print("Unknown command. Use a number, d<deg>, u<duty>, +, -, >>, <<, ir, or q.")
