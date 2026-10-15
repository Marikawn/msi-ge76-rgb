#!/usr/bin/env python3
"""
MSI GE76 Raider (SteelSeries KLC / ALC) Advanced RGB Controller
==============================================================
Devices:
  - 1038:113a: SteelSeries KLC (Keyboard Light Controller)
  - 1038:113e: SteelSeries ALC (Front Ambient/Aurora Lightbar)

Features:
  - Custom Hex Colors (--color)
  - Designer Themes (--theme: cyberpunk, matrix, fire, ice, gaming, sunset, rainbow)
  - Zone Overrides (--wasd, --arrows, --numpad, --lightbar-color)
  - Brightness Control (--brightness 1-100)
  - Live Animations (--animate: wave, breathe)
  - Battery Monitor Mode (--battery)
  - Factory Presets (--preset from presets.json)
"""

import sys
import os
import time
import math
import argparse
import json
import colorsys
import hid

VENDOR_ID = 0x1038
PID_KEYBOARD = 0x113a  # SteelSeries KLC
PID_LIGHTBAR = 0x113e  # SteelSeries ALC

REGION_ID_CODES = {
    "alphanum": 0x2a,
    "enter": 0x0b,
    "modifiers": 0x18,
    "numpad": 0x24,
    "nav_cluster": 0x13,
}

REGION_KEYCODES = {
    "alphanum": [
        4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
        20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34,
        35, 36, 37, 38, 39, 58, 59, 60, 61, 62, 63
    ],
    "enter": [
        40, 49, 50, 100, 135, 136, 137, 138, 139, 144, 145
    ],
    "modifiers": [
        41, 42, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56,
        57, 101, 224, 225, 226, 227, 228, 229, 230, 240
    ],
    "numpad": [
        64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77,
        78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91,
        92, 93, 94, 95, 96, 97, 98, 99
    ],
    "nav_cluster": [
        64, 65, 66, 67, 68, 69, 70, 74, 75, 76, 77, 78, 79, 80, 81, 82
    ],
}

KEYS_PER_REGION = 42
REPORT_DELAY = 0.015

# Approximate physical X-column position (0 to 17) for horizontal gradient effects
KEY_COLUMNS = {
    41: 0, 53: 0, 43: 0, 57: 0, 225: 0, 224: 0,
    30: 1, 20: 1, 4: 1, 29: 1,
    31: 2, 26: 2, 22: 2, 27: 2, 226: 2,
    32: 3, 8: 3, 7: 3, 6: 3,
    33: 4, 21: 4, 9: 4, 25: 4,
    34: 5, 23: 5, 10: 5, 5: 5, 44: 5,
    35: 6, 28: 6, 11: 6, 17: 6,
    36: 7, 24: 7, 13: 7, 16: 7,
    37: 8, 12: 8, 14: 8, 54: 8,
    38: 9, 18: 9, 15: 9, 55: 9,
    39: 10, 19: 10, 51: 10, 56: 10,
    45: 11, 47: 11, 52: 11, 230: 11,
    46: 12, 48: 12, 49: 12, 229: 12, 228: 12,
    42: 13, 40: 13, 240: 13,
    70: 14, 73: 14, 76: 14, 74: 14, 77: 14, 75: 14, 78: 14,
    80: 14, 81: 14, 82: 14, 79: 14,
    58: 2, 59: 3, 60: 4, 61: 5,
    62: 6, 63: 7, 64: 8, 65: 9,
    66: 10, 67: 11, 68: 12, 69: 13,
}
for _num in range(83, 100):
    KEY_COLUMNS[_num] = 16

# Keycode sets for zone targeting
WASD_KEYCODES = {26, 4, 22, 7}  # W, A, S, D
ARROW_KEYCODES = {82, 80, 81, 79}  # Up, Left, Down, Right
NUMPAD_KEYCODES = set(range(83, 100)) | {64, 65, 66, 67, 68, 69, 70}

# 92-byte activation frame used by modern SteelSeries laptop controllers
ACTIVATION_FRAME_92 = bytes.fromhex(
    "1c0010c05d4a8ae5ffff000000000800010100010000024000000001"
    "09000000000000000000000000000000000000000000000000000000"
    "00000000000000000000000000000000000000000000000000000000"
    "0000000000000000002d"
)

# 0x0b effect engine configuration frames for steady mode
EFFECT_STEADY_FRAMES = [
    [0x0b, 0x00, 0x03, 0x00] + [0x00] * 520,
    [0x0b, 0x00, 0x01, 0x00] + [0x00] * 520,
    [0x0b, 0x00, 0x00, 0x00, 0x00, 0x7b, 0x00, 0x00] + [0x00] * 516,
    [0x0b, 0x00, 0x05, 0x00] + [0x00] * 520,
    [0x0b, 0x00, 0x04, 0x00] + [0x00] * 520,
    [0x0b, 0x00, 0x02, 0x00] + [0x00] * 520,
]


def parse_vid_pid(device_str, default_vid=VENDOR_ID):
    """
    Parse a hardware ID string into (vendor_id, product_id).
    Supports '1038:113a', '0x1038:0x113a', '113a', or '0x113a'.
    """
    if not device_str:
        return None
    s = device_str.strip().lower()
    if ":" in s:
        parts = s.split(":")
        vid = int(parts[0], 16)
        pid = int(parts[1], 16)
        return (vid, pid)
    else:
        pid = int(s, 16)
        return (default_vid, pid)


def enumerate_steelseries_devices():
    """Find all connected SteelSeries HID devices on the USB bus."""
    devices = []
    seen = set()
    for dev in hid.enumerate():
        mfg = (dev.get("manufacturer_string") or "").lower()
        vid = dev.get("vendor_id", 0)
        if vid == VENDOR_ID or "steelseries" in mfg:
            key = (vid, dev.get("product_id"), dev.get("interface_number"), dev.get("path"))
            if key not in seen:
                seen.add(key)
                devices.append(dev)
    return devices


def print_detected_devices():
    """Print all detected SteelSeries HID devices for the user."""
    devs = enumerate_steelseries_devices()
    print("=" * 68)
    print("Detected SteelSeries USB HID Devices")
    print("=" * 68)
    if not devs:
        print("No SteelSeries HID devices found.")
        print("Tip: If devices are visible in 'lsusb', check permissions")
        print("     or install udev rules (see README.md).")
        print("=" * 68)
        return

    for d in devs:
        vid = d.get("vendor_id", 0)
        pid = d.get("product_id", 0)
        iface = d.get("interface_number", -1)
        prod = d.get("product_string") or "Unknown"
        path = d.get("path")
        path_str = path.decode() if isinstance(path, bytes) else str(path)
        role = ""
        prod_lower = prod.lower()
        if "klc" in prod_lower or "keyboard" in prod_lower:
            role = " [Keyboard Light Controller]"
        elif "alc" in prod_lower or "lightbar" in prod_lower or "aurora" in prod_lower:
            role = " [Aurora Lightbar Controller]"

        print(f"ID: {vid:04x}:{pid:04x} | Interface: {iface} | {prod}{role}")
        print(f"    Sysfs Path: {path_str}")
    print("=" * 68)


def resolve_device(explicit_id_str, default_vid, default_pid, device_role="keyboard"):
    """
    Resolve (vendor_id, product_id) for a device role:
    1. If explicit_id_str is provided, parse it.
    2. Check if default (default_vid, default_pid) exists on interface 0.
    3. Fallback: auto-detect from connected SteelSeries devices.
    """
    if explicit_id_str:
        return parse_vid_pid(explicit_id_str, default_vid=default_vid)

    # Check default
    if find_device_path(default_vid, default_pid, 0) is not None:
        return (default_vid, default_pid)

    # Autodetect fallback
    devs = enumerate_steelseries_devices()
    for d in devs:
        if d.get("interface_number") == 0:
            prod = (d.get("product_string") or "").lower()
            vid = d.get("vendor_id", default_vid)
            pid = d.get("product_id", 0)
            if device_role == "keyboard" and ("klc" in prod or "keyboard" in prod):
                return (vid, pid)
            elif device_role == "lightbar" and ("alc" in prod or "lightbar" in prod or "aurora" in prod):
                return (vid, pid)

    return (default_vid, default_pid)


def find_device_path(vendor_id, product_id, interface_number=0):
    """Enumerate USB HID devices and return device path for interface 0."""
    for dev_info in hid.enumerate(vendor_id, product_id):
        if dev_info.get("interface_number") == interface_number:
            return dev_info["path"]
    return None


def scale_color(rgb, brightness_pct):
    """Scale RGB tuple by brightness percentage (0-100)."""
    factor = max(0.0, min(100.0, brightness_pct)) / 100.0
    return [int(round(c * factor)) for c in rgb]


def parse_hex_color(hex_str, brightness=100):
    """Parse HTML hex string (#RRGGBB or RRGGBB) to scaled [R, G, B]."""
    cleaned = hex_str.lstrip("#")
    if len(cleaned) != 6:
        raise ValueError(f"Invalid hex color '{hex_str}'. Expected 6 hex digits, e.g. ff0000")
    rgb = [int(cleaned[i:i+2], 16) for i in (0, 2, 4)]
    return scale_color(rgb, brightness)


def lerp(c1, c2, t):
    """Linearly interpolate between two RGB colors (t from 0.0 to 1.0)."""
    t = max(0.0, min(1.0, t))
    return [int(round(c1[i] + (c2[i] - c1[i]) * t)) for i in range(3)]


def get_gradient_color(stops, pos):
    """Calculate color from a multi-stop gradient (stops: [(pos, rgb), ...])."""
    if pos <= stops[0][0]:
        return stops[0][1]
    if pos >= stops[-1][0]:
        return stops[-1][1]
    for i in range(len(stops) - 1):
        p1, c1 = stops[i]
        p2, c2 = stops[i+1]
        if p1 <= pos <= p2:
            t = (pos - p1) / (p2 - p1)
            return lerp(c1, c2, t)
    return stops[-1][1]


def get_theme_colors(theme_name, brightness=100):
    """Return key color mapping function and lightbar color for a theme."""
    tname = theme_name.lower()

    if tname == "cyberpunk":
        # Neon Pink -> Deep Purple -> Electric Cyan
        stops = [
            (0.0, [255, 0, 128]),
            (0.5, [140, 0, 255]),
            (1.0, [0, 240, 255]),
        ]
        def key_fn(kc):
            col = KEY_COLUMNS.get(kc, 8) / 16.0
            return scale_color(get_gradient_color(stops, col), brightness)
        lightbar_color = scale_color([0, 240, 255], brightness)
        return key_fn, lightbar_color

    elif tname == "matrix":
        # Terminal Green on alphas/WASD, deep dark green on modifiers
        bright_green = scale_color([0, 255, 40], brightness)
        dim_green = scale_color([0, 45, 10], brightness)
        wasd_white = scale_color([200, 255, 210], brightness)
        def key_fn(kc):
            if kc in WASD_KEYCODES:
                return wasd_white
            if kc in REGION_KEYCODES["alphanum"]:
                return bright_green
            return dim_green
        lightbar_color = bright_green
        return key_fn, lightbar_color

    elif tname == "fire":
        # Fiery Red -> Molten Orange -> Golden Yellow
        stops = [
            (0.0, [255, 0, 0]),
            (0.5, [255, 85, 0]),
            (1.0, [255, 210, 0]),
        ]
        def key_fn(kc):
            col = KEY_COLUMNS.get(kc, 8) / 16.0
            return scale_color(get_gradient_color(stops, col), brightness)
        lightbar_color = scale_color([255, 70, 0], brightness)
        return key_fn, lightbar_color

    elif tname in ("ice", "glacier"):
        # Arctic Navy -> Frost Cyan -> Pure Frost White
        stops = [
            (0.0, [0, 25, 90]),
            (0.6, [0, 210, 255]),
            (1.0, [240, 250, 255]),
        ]
        def key_fn(kc):
            col = KEY_COLUMNS.get(kc, 8) / 16.0
            return scale_color(get_gradient_color(stops, col), brightness)
        lightbar_color = scale_color([0, 210, 255], brightness)
        return key_fn, lightbar_color

    elif tname == "gaming":
        # High-contrast FPS: WASD/Numbers in Cyan/Yellow, rest in stealth dark blue
        wasd_color = scale_color([0, 255, 255], brightness)  # Cyan
        arrow_color = scale_color([255, 220, 0], brightness)  # Yellow
        action_color = scale_color([255, 0, 40], brightness)  # Red (Space/Shift/Enter)
        bg_color = scale_color([5, 12, 35], brightness)       # Midnight Charcoal
        def key_fn(kc):
            if kc in WASD_KEYCODES:
                return wasd_color
            if kc in ARROW_KEYCODES:
                return arrow_color
            if kc in (44, 225, 224, 40):  # Space, LShift, LCtrl, Enter
                return action_color
            if kc in range(30, 35):  # 1-5 keys
                return wasd_color
            return bg_color
        lightbar_color = wasd_color
        return key_fn, lightbar_color

    elif tname == "sunset":
        # Deep Indigo -> Sunset Magenta -> Warm Peach
        stops = [
            (0.0, [80, 0, 140]),
            (0.5, [230, 0, 80]),
            (1.0, [255, 120, 30]),
        ]
        def key_fn(kc):
            col = KEY_COLUMNS.get(kc, 8) / 16.0
            return scale_color(get_gradient_color(stops, col), brightness)
        lightbar_color = scale_color([230, 0, 80], brightness)
        return key_fn, lightbar_color

    elif tname == "rainbow":
        # Full spectrum horizontal rainbow
        def key_fn(kc):
            col = KEY_COLUMNS.get(kc, 8) / 16.0
            r, g, b = colorsys.hsv_to_rgb(col, 1.0, 1.0)
            return scale_color([int(r * 255), int(g * 255), int(b * 255)], brightness)
        lightbar_color = scale_color([255, 0, 255], brightness)
        return key_fn, lightbar_color

    else:
        raise ValueError(
            f"Unknown theme '{theme_name}'. Available: cyberpunk, matrix, fire, ice, gaming, sunset, rainbow"
        )


def read_battery_status():
    """Read laptop battery percentage and status from Linux sysfs."""
    cap_path = "/sys/class/power_supply/BAT1/capacity"
    stat_path = "/sys/class/power_supply/BAT1/status"
    capacity = 100
    charging = False
    if os.path.exists(cap_path):
        try:
            with open(cap_path, "r") as f:
                capacity = int(f.read().strip())
        except Exception:
            pass
    if os.path.exists(stat_path):
        try:
            with open(stat_path, "r") as f:
                charging = f.read().strip().lower() in ("charging", "full")
        except Exception:
            pass
    return capacity, charging


def get_battery_color(capacity, charging, brightness=100):
    """Determine RGB color based on battery capacity and charging status."""
    if charging:
        return scale_color([0, 180, 255], brightness)  # Electric Blue when charging
    if capacity > 60:
        return scale_color([0, 255, 0], brightness)    # Green
    elif capacity > 20:
        return scale_color([255, 170, 0], brightness)  # Amber
    else:
        return scale_color([255, 0, 0], brightness)    # Red Warning


def make_key_colors_packet(region_name, keycodes, color_source):
    """
    Build the 524-byte feature report for a keyboard region.
    color_source can be an [R, G, B] list or a callable key_color_fn(keycode).
    """
    region_hex = REGION_ID_CODES[region_name]
    header = [0x0e, 0x00, region_hex, 0x00]

    packet = list(header)
    count = 0
    for kc in keycodes:
        if callable(color_source):
            rgb = color_source(kc)
        else:
            rgb = color_source
        key_fragment = rgb + [0x00, 0x00, 0x00, 0x2c, 0x01, 0x00, 0x01, 0x00, kc]
        packet.extend(key_fragment)
        count += 1

    while count < KEYS_PER_REGION:
        packet.extend([0x00] * 12)
        count += 1

    footer = [0x00] * 16
    packet.extend(footer)
    return packet


def make_refresh_packet():
    """Build the 64-byte output report that commits RGB changes."""
    return [0x09] + [0x00] * 63


def send_keyboard_data(dev, color_source):
    """Send color maps, effect frames, activation frame, and commit to keyboard."""
    for region_name, keycodes in REGION_KEYCODES.items():
        pkt = make_key_colors_packet(region_name, keycodes, color_source)
        dev.send_feature_report(pkt)
        time.sleep(REPORT_DELAY)

    for eff_frame in EFFECT_STEADY_FRAMES:
        dev.send_feature_report(eff_frame)
        time.sleep(REPORT_DELAY)

    dev.send_feature_report(ACTIVATION_FRAME_92)
    time.sleep(REPORT_DELAY)
    dev.write(make_refresh_packet())
    time.sleep(REPORT_DELAY)


def send_lightbar_data(dev, color):
    """Send color map and commit report to front ALC lightbar."""
    for region_name, keycodes in REGION_KEYCODES.items():
        pkt = make_key_colors_packet(region_name, keycodes, color)
        dev.send_feature_report(pkt)
        time.sleep(REPORT_DELAY)

    dev.write(make_refresh_packet())
    time.sleep(REPORT_DELAY)


def animate_wave(speed=1.0, brightness=100, kb_target=None, lb_target=None):
    """Continuous smooth rainbow wave sweeping horizontally across keys."""
    kb_vid, kb_pid = kb_target if kb_target else (VENDOR_ID, PID_KEYBOARD)
    lb_vid, lb_pid = lb_target if lb_target else (VENDOR_ID, PID_LIGHTBAR)

    kb_path = find_device_path(kb_vid, kb_pid, 0)
    lb_path = find_device_path(lb_vid, lb_pid, 0)
    if not kb_path:
        print(f"[!] Keyboard ({kb_vid:04x}:{kb_pid:04x}) not found at interface 0!")
        return

    kb = hid.device()
    kb.open_path(kb_path)
    lb = None
    if lb_path:
        lb = hid.device()
        lb.open_path(lb_path)

    print("[*] Running Rainbow Wave animation. Press Ctrl+C to stop.")
    phase = 0.0
    try:
        while True:
            def wave_fn(kc):
                col = KEY_COLUMNS.get(kc, 8) / 16.0
                hue = (col + phase) % 1.0
                r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                return scale_color([int(r*255), int(g*255), int(b*255)], brightness)

            send_keyboard_data(kb, wave_fn)
            if lb:
                lb_r, lb_g, lb_b = colorsys.hsv_to_rgb(phase % 1.0, 1.0, 1.0)
                send_lightbar_data(lb, scale_color([int(lb_r*255), int(lb_g*255), int(lb_b*255)], brightness))

            phase += 0.04 * speed
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n[*] Animation stopped.")
    finally:
        kb.close()
        if lb:
            lb.close()


def animate_breathe(base_rgb, speed=1.0, max_brightness=100, kb_target=None, lb_target=None):
    """Continuous smooth breathing/pulsing animation."""
    kb_vid, kb_pid = kb_target if kb_target else (VENDOR_ID, PID_KEYBOARD)
    lb_vid, lb_pid = lb_target if lb_target else (VENDOR_ID, PID_LIGHTBAR)

    kb_path = find_device_path(kb_vid, kb_pid, 0)
    lb_path = find_device_path(lb_vid, lb_pid, 0)
    if not kb_path:
        print(f"[!] Keyboard ({kb_vid:04x}:{kb_pid:04x}) not found at interface 0!")
        return

    kb = hid.device()
    kb.open_path(kb_path)
    lb = None
    if lb_path:
        lb = hid.device()
        lb.open_path(lb_path)

    print(f"[*] Running Breathe animation for color {base_rgb}. Press Ctrl+C to stop.")
    angle = 0.0
    try:
        while True:
            # Sine wave from 0.05 to 1.0
            factor = (math.sin(angle) + 1.0) / 2.0
            curr_brightness = 5 + int(factor * (max_brightness - 5))
            color = scale_color(base_rgb, curr_brightness)

            send_keyboard_data(kb, color)
            if lb:
                send_lightbar_data(lb, color)

            angle += 0.12 * speed
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n[*] Animation stopped.")
    finally:
        kb.close()
        if lb:
            lb.close()


def load_presets():
    """Load presets.json from the script directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, "presets.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def scale_preset_frames(raw_hex_list, speed=1.0):
    """
    Scale transition and hold durations within 0x0b hardware effect frames.
    speed > 1.0 accelerates the effect; speed < 1.0 decelerates it.
    """
    if speed <= 0:
        speed = 1.0
    if abs(speed - 1.0) < 0.01:
        return [bytearray.fromhex(h) for h in raw_hex_list]

    factor = 1.0 / speed
    result = []
    for h in raw_hex_list:
        b = bytearray.fromhex(h)
        if b[0] == 0x0b:
            pos = 4
            scaled_durations = []
            while pos + 8 <= len(b):
                if b[pos:pos+2] == b'\xf0\x0f' or (
                    b[pos] == 0 and b[pos+1] == 0 and b[pos+2] == 0 and
                    b[pos+3] == 0 and b[pos+4] == 0 and b[pos+5] == 0
                ):
                    break
                orig_dur = b[pos+4] | (b[pos+5] << 8)
                if 5 <= orig_dur <= 5000:
                    new_dur = max(5, min(65535, int(round(orig_dur * factor))))
                    b[pos+4] = new_dur & 0xff
                    b[pos+5] = (new_dur >> 8) & 0xff
                    scaled_durations.append(new_dur)
                pos += 8

            idx = b.find(b'\xf0\x0f')
            if idx != -1 and len(scaled_durations) > 0:
                if idx + 22 <= len(b):
                    old_tot = b[idx+20] | (b[idx+21] << 8)
                    if old_tot > 0:
                        new_tot = max(10, min(65535, int(round(old_tot * factor))))
                        b[idx+20] = new_tot & 0xff
                        b[idx+21] = (new_tot >> 8) & 0xff
        result.append(b)
    return result


def apply_hardware_preset(preset_name, presets_dict, target_device="both", speed=1.0, kb_target=None, lb_target=None):
    """Send factory SteelSeries preset frames from presets.json with optional speed scaling."""
    if preset_name not in presets_dict:
        print(f"[!] Unknown preset '{preset_name}'. Available: {list(presets_dict.keys())}")
        return False

    kb_vid, kb_pid = kb_target if kb_target else (VENDOR_ID, PID_KEYBOARD)
    lb_vid, lb_pid = lb_target if lb_target else (VENDOR_ID, PID_LIGHTBAR)

    targets = []
    if target_device in ("keyboard", "both"):
        targets.append((f"Keyboard ({kb_vid:04x}:{kb_pid:04x})", kb_vid, kb_pid))
    if target_device in ("lightbar", "both"):
        targets.append((f"Lightbar ({lb_vid:04x}:{lb_pid:04x})", lb_vid, lb_pid))

    frames_to_send = scale_preset_frames(presets_dict[preset_name], speed=speed)
    speed_info = f" (Speed: {speed}x)" if abs(speed - 1.0) >= 0.01 else ""

    for name, vid, pid in targets:
        path = find_device_path(vid, pid, 0)
        if not path:
            print(f"[!] {name} not found at interface 0.")
            continue
        dev = hid.device()
        try:
            dev.open_path(path)
            print(f"[*] Applying preset '{preset_name}'{speed_info} to {name}...")
            for frame_data in frames_to_send:
                dev.send_feature_report(frame_data)
                time.sleep(REPORT_DELAY)
            dev.write(make_refresh_packet())
            time.sleep(REPORT_DELAY)
            print(f"[+] Preset '{preset_name}' applied to {name}!")
        finally:
            dev.close()
    return True


def main():
    parser = argparse.ArgumentParser(
        description="MSI GE76 Raider SteelSeries Advanced RGB Controller"
    )
    parser.add_argument(
        "--color", "-c",
        help="Hex color (e.g. ff0000, 00ffff, ffffff, 000000 for off)"
    )
    parser.add_argument(
        "--theme", "-t",
        choices=["cyberpunk", "matrix", "fire", "ice", "gaming", "sunset", "rainbow"],
        help="Curated designer lighting theme"
    )
    parser.add_argument(
        "--brightness", "-b",
        type=int,
        default=100,
        help="Brightness percentage (1-100, default: 100)"
    )
    parser.add_argument(
        "--device", "-d",
        choices=["keyboard", "lightbar", "both"],
        default="both",
        help="Target device (default: both keyboard and lightbar)"
    )
    parser.add_argument(
        "--wasd",
        help="Override WASD keys color (e.g. 00ffff, ff0055)"
    )
    parser.add_argument(
        "--arrows",
        help="Override Arrow keys color (e.g. ffaa00, 00ff00)"
    )
    parser.add_argument(
        "--numpad",
        help="Override Numpad keys color"
    )
    parser.add_argument(
        "--lightbar-color",
        help="Set a different color for the front lightbar only"
    )
    parser.add_argument(
        "--battery",
        action="store_true",
        help="Color the lightbar based on real-time battery status"
    )
    parser.add_argument(
        "--animate",
        choices=["wave", "breathe"],
        help="Run live animation (wave or breathe)"
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Animation speed multiplier (default: 1.0)"
    )
    parser.add_argument(
        "--keyboard-id", "--kb-id",
        dest="keyboard_id",
        help="Custom Keyboard USB Vendor & Product ID (e.g. 1038:113a or 113a)"
    )
    parser.add_argument(
        "--lightbar-id", "--lb-id",
        dest="lightbar_id",
        help="Custom Lightbar USB Vendor & Product ID (e.g. 1038:113e or 113e)"
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="Scan and list all detected SteelSeries HID devices and IDs"
    )
    parser.add_argument(
        "--preset", "-p",
        help="Factory SteelSeries preset from presets.json"
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="List available factory presets in presets.json"
    )

    args = parser.parse_args()

    # 1. Device listing
    if args.list_devices:
        print_detected_devices()
        return

    # 2. Preset listing
    presets = load_presets()
    if args.list_presets:
        if presets:
            print("Available factory presets in presets.json:")
            for p in presets.keys():
                print(f"  - {p}")
        else:
            print("No presets.json found.")
        return

    # Resolve hardware targets
    kb_target = resolve_device(args.keyboard_id, VENDOR_ID, PID_KEYBOARD, "keyboard")
    lb_target = resolve_device(args.lightbar_id, VENDOR_ID, PID_LIGHTBAR, "lightbar")

    # 3. Live Animations
    if args.animate == "wave":
        animate_wave(speed=args.speed, brightness=args.brightness, kb_target=kb_target, lb_target=lb_target)
        return
    elif args.animate == "breathe":
        base_color = parse_hex_color(args.color if args.color else "ff0000", brightness=100)
        animate_breathe(base_color, speed=args.speed, max_brightness=args.brightness, kb_target=kb_target, lb_target=lb_target)
        return

    # 4. Factory Preset application
    if args.preset:
        apply_hardware_preset(
            args.preset,
            presets,
            target_device=args.device,
            speed=args.speed,
            kb_target=kb_target,
            lb_target=lb_target
        )
        return

    # 5. Themes or Custom Static Colors
    overrides = {}
    if args.wasd:
        overrides["wasd"] = parse_hex_color(args.wasd, args.brightness)
    if args.arrows:
        overrides["arrows"] = parse_hex_color(args.arrows, args.brightness)
    if args.numpad:
        overrides["numpad"] = parse_hex_color(args.numpad, args.brightness)

    lightbar_custom = None
    if args.lightbar_color:
        lightbar_custom = parse_hex_color(args.lightbar_color, args.brightness)
    elif args.battery:
        cap, chg = read_battery_status()
        lightbar_custom = get_battery_color(cap, chg, args.brightness)
        chg_str = " (Charging)" if chg else " (Discharging)"
        print(f"[*] Battery Mode: {cap}%{chg_str} -> Lightbar: {lightbar_custom}")

    # Determine keyboard color function
    if args.theme:
        theme_key_fn, theme_lb = get_theme_colors(args.theme, args.brightness)
        if lightbar_custom is None:
            lightbar_custom = theme_lb
        def final_key_fn(kc):
            if "wasd" in overrides and kc in WASD_KEYCODES:
                return overrides["wasd"]
            if "arrows" in overrides and kc in ARROW_KEYCODES:
                return overrides["arrows"]
            if "numpad" in overrides and kc in NUMPAD_KEYCODES:
                return overrides["numpad"]
            return theme_key_fn(kc)
        kb_color_source = final_key_fn
        print(f"[*] Applying Theme: {args.theme.upper()} (Brightness: {args.brightness}%)")

    else:
        # Default color is ff0000 if none provided
        color_hex = args.color if args.color else "ff0000"
        base_color = parse_hex_color(color_hex, args.brightness)
        if lightbar_custom is None:
            lightbar_custom = base_color

        if overrides:
            def final_key_fn(kc):
                if "wasd" in overrides and kc in WASD_KEYCODES:
                    return overrides["wasd"]
                if "arrows" in overrides and kc in ARROW_KEYCODES:
                    return overrides["arrows"]
                if "numpad" in overrides and kc in NUMPAD_KEYCODES:
                    return overrides["numpad"]
                return base_color
            kb_color_source = final_key_fn
        else:
            kb_color_source = base_color
        print(f"[*] Setting color #{color_hex.lstrip('#')} (RGB: {base_color}, Brightness: {args.brightness}%)")

    # Apply to devices
    if args.device in ("keyboard", "both"):
        path = find_device_path(kb_target[0], kb_target[1], 0)
        if path:
            dev = hid.device()
            try:
                dev.open_path(path)
                print(f"[*] Programming Keyboard ({kb_target[0]:04x}:{kb_target[1]:04x})...")
                send_keyboard_data(dev, kb_color_source)
                print(f"[+] Keyboard ({kb_target[0]:04x}:{kb_target[1]:04x}) programmed successfully!")
            finally:
                dev.close()
        else:
            print(f"[!] Keyboard device ({kb_target[0]:04x}:{kb_target[1]:04x}) interface 0 not found.")

    if args.device in ("lightbar", "both"):
        path = find_device_path(lb_target[0], lb_target[1], 0)
        if path:
            dev = hid.device()
            try:
                dev.open_path(path)
                print(f"[*] Programming Front Lightbar ({lb_target[0]:04x}:{lb_target[1]:04x})...")
                send_lightbar_data(dev, lightbar_custom)
                print(f"[+] Front Lightbar ({lb_target[0]:04x}:{lb_target[1]:04x}) programmed successfully!")
            finally:
                dev.close()
        else:
            if args.device == "lightbar":
                print(f"[!] Front Lightbar device ({lb_target[0]:04x}:{lb_target[1]:04x}) interface 0 not found.")


if __name__ == "__main__":
    main()
