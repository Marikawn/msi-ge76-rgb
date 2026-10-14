# MSI GE76 Raider Linux RGB Controller (SteelSeries KLC / ALC)

A lightweight, standalone Python tool to control per-key RGB keyboard backlighting and the front lightbar on the **MSI GE76 Raider** (and compatible modern MSI/SteelSeries laptops) under Linux without proprietary vendor software.

---

## Supported Hardware

| Component | Device Name | USB Vendor & Product ID |
| :--- | :--- | :--- |
| **Keyboard** | SteelSeries KLC (Keyboard Light Controller) | `1038:113a` |
| **Front Lightbar** | SteelSeries ALC (Aurora Light Controller) | `1038:113e` |

---

## Why Other Tools Fail Out of the Box

* **`msi-perkeyrgb`**: Targets older laptop generations (GE63/GE75, `1038:1122`). It lacks the modern 92-byte activation frame (`0x1c`) and `0x0b` steady effect engine setup required by newer SteelSeries controllers.
* **`OpenRGB`**: As of mainline releases, `1038:113a` and `1038:113e` are not yet included in the device detection tables (tracked under OpenRGB Issue #4827).

This utility implements the full modern handshake directly over userspace USB HID via `hidapi`, eliminating permission hurdles and detection errors.

---

## Requirements

* Linux (Kernel 5.x / 6.x)
* Python 3.8+
* `hidapi` Python library

Install dependencies:

```bash
pip install --user hidapi
```

---

## Usage

Make sure the script is executable:

```bash
chmod +x msi_keyboard_control.py
```

### 1. Steady Colors

Set both keyboard and lightbar to steady red (`#ff0000`):

```bash
./msi_keyboard_control.py --color ff0000
```

Set steady white:

```bash
./msi_keyboard_control.py --color ffffff
```

Turn off all lights:

```bash
./msi_keyboard_control.py --color 000000
```

### 2. Designer Themes

Apply pre-tuned gradients and key highlights across both devices:

* **Cyberpunk / Synthwave** (Neon Pink -> Deep Violet -> Electric Cyan):
  ```bash
  ./msi_keyboard_control.py --theme cyberpunk
  ```
* **Matrix** (Phosphor terminal green on alphas/WASD, dark forest frame):
  ```bash
  ./msi_keyboard_control.py --theme matrix
  ```
* **Fire** (Ruby Red -> Molten Orange -> Golden Yellow):
  ```bash
  ./msi_keyboard_control.py --theme fire
  ```
* **Ice** (Arctic Navy -> Frost Cyan -> Crisp White):
  ```bash
  ./msi_keyboard_control.py --theme ice
  ```
* **Gaming FPS** (WASD & 1–5 in Cyan, Arrows in Yellow, Space/Shift in Red, stealth charcoal background):
  ```bash
  ./msi_keyboard_control.py --theme gaming
  ```
* **Sunset** (Deep Indigo -> Magenta -> Warm Peach):
  ```bash
  ./msi_keyboard_control.py --theme sunset
  ```
* **Rainbow** (Full-spectrum horizontal static rainbow):
  ```bash
  ./msi_keyboard_control.py --theme rainbow
  ```

### 3. Zone Overrides & Brightness

Highlight specific key clusters with custom colors:

```bash
./msi_keyboard_control.py --color 1b002c \
--wasd 00ffff --arrows ffaa00 --brightness 80
```

### 4. Real-Time Battery Monitor on Lightbar

Keep your keyboard on your chosen color while turning the front lightbar into a live battery indicator:

* **Electric Blue**: Plugged in / Charging
* **Green**: Battery > 60%
* **Amber**: Battery 20% – 60%
* **Red Warning**: Battery < 20%

```bash
./msi_keyboard_control.py --color ff0000 --battery
```

### 5. Live Animations

Run smooth real-time software effects in your terminal (press `Ctrl + C` to stop):

* **Rainbow Wave**:
  ```bash
  ./msi_keyboard_control.py --animate wave --speed 1.2
  ```
* **Breathe / Pulse**:
  ```bash
  ./msi_keyboard_control.py --color ff0000 --animate breathe
  ```

### 6. Factory SteelSeries Presets

Apply original factory animations loaded from `presets.json`:

```bash
./msi_keyboard_control.py --preset disco
./msi_keyboard_control.py --preset aqua
./msi_keyboard_control.py --list-presets
```

---

## Hardware Backlight Brightness

On MSI GE76 Raider laptops, global backlight brightness is managed by the Embedded Controller (EC):

* **`Fn` + `F10`**: Increase keyboard backlight brightness.
* **`Fn` + `F11`**: Decrease / turn off keyboard backlight brightness.

> **Note:** If the LEDs remain dark after sending a color, press `Fn + F10` repeatedly. Holding `Fn` temporarily illuminates the function row at maximum brightness to assist in finding shortcuts in the dark.

---

## Run Automatically on System Boot (systemd)

You can set up a `systemd` user service to apply your preferred lighting profile automatically whenever your laptop powers on, without needing root permissions.

### Step 1: Create the User Service Directory

```bash
mkdir -p ~/.config/systemd/user
```

### Step 2: Install the Service Unit

Copy the provided unit template into your systemd configuration:

```bash
cp msi-keyboard-rgb.service ~/.config/systemd/user/
```

Or create `~/.config/systemd/user/msi-keyboard-rgb.service` manually:

```ini
[Unit]
Description=Set MSI GE76 Keyboard and Lightbar RGB on Boot
After=graphical-session.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/python3 %h/msi-ge76-rgb/msi_keyboard_control.py --color ff0000

[Install]
WantedBy=default.target
```

*(You can replace `--color ff0000` with `--theme cyberpunk` or any other option).*

### Step 3: Enable User Session Lingering

Enable lingering so systemd initializes user services immediately at machine boot (even before graphical login):

```bash
loginctl enable-linger
```

### Step 4: Enable and Start the Service

```bash
systemctl --user daemon-reload
systemctl --user enable --now msi-keyboard-rgb.service
```

### Step 5: Verify Service Status

```bash
systemctl --user status msi-keyboard-rgb.service
```

---

## Command Reference

| Flag | Description | Default |
| :--- | :--- | :--- |
| `--color`, `-c` | Base HTML hex color (`ff0000`, `00ff00`, etc.) | `ff0000` |
| `--theme`, `-t` | Predefined theme (`cyberpunk`, `matrix`, `fire`, etc.) | None |
| `--brightness`, `-b`| Brightness scaling percentage (`1` to `100`) | `100` |
| `--device`, `-d` | Target device (`keyboard`, `lightbar`, or `both`) | `both` |
| `--wasd` | Override color for WASD keys | None |
| `--arrows` | Override color for Arrow keys | None |
| `--numpad` | Override color for Numpad keys | None |
| `--lightbar-color`| Separate color for front lightbar only | Matches base |
| `--battery` | Map front lightbar to laptop battery percentage | Disabled |
| `--animate` | Live animation (`wave` or `breathe`) | None |
| `--speed` | Animation speed multiplier | `1.0` |
| `--preset`, `-p` | Factory preset name from `presets.json` | None |
| `--list-presets` | Show available factory presets | None |

---

## License

MIT License. See [LICENSE](LICENSE) for details.
