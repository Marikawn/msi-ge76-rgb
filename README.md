# MSI GE76 Raider Linux RGB Controller (SteelSeries KLC / ALC)

A lightweight, standalone Python tool to control per-key RGB keyboard backlighting and the front lightbar on the **MSI GE76 Raider** (and compatible modern MSI/SteelSeries laptops) under Linux without proprietary vendor software.

---

## Supported Hardware

| Component | Device Name | Default USB ID | Configurable Flags |
| :--- | :--- | :--- | :--- |
| **Keyboard** | SteelSeries KLC (Keyboard Light Controller) | `1038:113a` | `--keyboard-id` / `--kb-id` |
| **Front Lightbar** | SteelSeries ALC (Aurora Light Controller) | `1038:113e` | `--lightbar-id` / `--lb-id` |

> Other MSI / SteelSeries models (such as GE66, GP66, GP76, GS66, Raider GE77/GE78, Vector GP68/GP76, Stealth 15/17, and Titan GT77) can be auto-detected or specified via custom IDs. See [Finding & Configuring Hardware IDs](#finding-and-configuring-hardware-ids-for-other-laptop-models) below.

---

## Background & Technical Context

This project builds upon the open-source community's ongoing efforts to support per-key RGB on Linux:

* **[msi-perkeyrgb](https://github.com/Askannz/msi-perkeyrgb)** pioneered early reverse engineering of MSI SteelSeries laptop keyboards, focusing on earlier laptop generations (such as GE63/GS65, `1038:1122`) that use an older 64-byte protocol. Modern MSI laptops (such as the GE76/GE66 series) introduced an updated 524-byte feature report architecture requiring a new activation handshake.
* **[OpenRGB](https://openrgb.org)** is an exceptional multi-vendor RGB management suite supporting thousands of devices. Upstream integration for these newer laptop IDs (`1038:113a` and `1038:113e`) is currently tracked in the community (e.g. OpenRGB Issue #4827).

This standalone utility was created to provide a lightweight, immediate solution tailored specifically to modern MSI GE-series laptops, communicating directly with the hardware via userspace USB HID without requiring external daemons.

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

### Quick Help

To display all available flags, arguments, and options at any time:

```bash
./msi_keyboard_control.py -h
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

Apply original factory animations loaded from `presets.json`. You can control the hardware playback speed of any preset using the `--speed` multiplier (`2.0` for 2x faster, `0.5` for half speed):

```bash
# Run disco preset at default speed
./msi_keyboard_control.py --preset disco

# Run disco preset at double speed (fast flash)
./msi_keyboard_control.py --preset disco --speed 2.0

# Run aqua preset at half speed (slow wave)
./msi_keyboard_control.py --preset aqua --speed 0.5

# List all available factory presets
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

## Finding and Configuring Hardware IDs for Other Laptop Models

MSI laptops across different models and sub-series (such as GE66, GE76, GP66, GP76, GS66, Raider GE77/GE78, Vector GP68/GP76/GP77, Stealth 15/17, and Titan GT77) share SteelSeries USB HID controller hardware, but individual product lines may use differing USB Product IDs.

### 1. Identify Your Connected SteelSeries Devices

#### Method A: Built-in Hardware Scanner (Recommended)

Run the script with `--list-devices` to scan the USB bus and display connected SteelSeries HID controllers, interface numbers, and IDs:

```bash
./msi_keyboard_control.py --list-devices
```

Example output:

```text
====================================================================
Detected SteelSeries USB HID Devices
====================================================================
ID: 1038:113a | Interface: 0 | SteelSeries KLC [Keyboard Light Controller]
    Sysfs Path: 3-9:1.0
ID: 1038:113a | Interface: 1 | SteelSeries KLC [Keyboard Light Controller]
    Sysfs Path: 3-9:1.1
ID: 1038:113e | Interface: 0 | SteelSeries ALC [Aurora Lightbar Controller]
    Sysfs Path: 3-8:1.0
ID: 1038:113e | Interface: 1 | SteelSeries ALC [Aurora Lightbar Controller]
    Sysfs Path: 3-8:1.1
====================================================================
```

#### Method B: Using `lsusb`

Query connected SteelSeries USB devices:

```bash
lsusb | grep -i steelseries
```

Example output:

```text
Bus 003 Device 005: ID 1038:113e SteelSeries ApS SteelSeries ALC
Bus 003 Device 006: ID 1038:113a SteelSeries ApS SteelSeries KLC
```

#### Method C: Querying sysfs

Inspect the kernel USB device tree directly:

```bash
grep -s . /sys/bus/usb/devices/*/product | \
grep -i steelseries
```

---

### 2. Configure Your Custom IDs

If your laptop uses different Product IDs (for example, `1038:1126`, `1038:113c`, or `1038:1167`):

#### CLI Flags
Pass your custom IDs using `--keyboard-id` (or `--kb-id`) and `--lightbar-id` (or `--lb-id`). Both `1038:XXXX` and short `XXXX` formats are accepted:

```bash
./msi_keyboard_control.py \
--keyboard-id 1038:113a \
--lightbar-id 1038:113e \
--color ff0000
```

#### Automatic Discovery Fallback
If you omit `--keyboard-id` or `--lightbar-id` and your laptop is not using the default GE76 IDs (`1038:113a`/`1038:113e`), the controller automatically scans the USB bus for any connected SteelSeries KLC (keyboard) or ALC (lightbar) devices on interface 0.

#### Systemd Service Configuration
Update your unit file (`~/.config/systemd/user/msi-keyboard-rgb.service`) with your specific flags in `ExecStart`:

```ini
[Unit]
Description=Set MSI Keyboard and Lightbar RGB on Boot
After=graphical-session.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/python3 %h/msi-ge76-rgb/msi_keyboard_control.py --keyboard-id 1038:113a --lightbar-id 1038:113e --color ff0000

[Install]
WantedBy=default.target
```

---

## OS & Distribution Compatibility

### Technical Compatibility Guarantee

| Environment | Supported? | Details & Setup |
| :--- | :---: | :--- |
| **RHEL 8 / 9 & Derivatives**<br>(CentOS Stream, Rocky Linux, AlmaLinux) | **Yes** | Fully supported. Uses system Python 3 (`python3`) and `pip install --user hidapi`. Operates cleanly in userspace. |
| **Fedora (Workstation & Server)** | **Yes** | Fully supported out of the box with `hidapi`. |
| **Ubuntu / Debian / Linux Mint / Pop!_OS** | **Yes** | Fully supported. Standard package `python3-pip` and `hidapi`. |
| **Arch Linux / Manjaro** | **Yes** | Fully supported. `python-hidapi` can be installed via `pacman -S python-hidapi` or pip. |
| **openSUSE (Tumbleweed & Leap)** | **Yes** | Fully supported with standard Python 3 and `hidapi`. |
| **Non-systemd Systems**<br>(Alpine OpenRC, Void runit, Artix, Slackware) | **Yes** | The core script is 100% standalone and does **not** depend on systemd. For autostart, use desktop autostart, `.xprofile`, or `/etc/rc.local`. |

---

### Why It Works Across All Distributions

1. **Pure Userspace USB HID Protocol**:
   This tool communicates directly with the controller hardware via USB Control Transfers (`SET_REPORT` on Endpoint 0) and interrupt endpoints using `hidapi` (`libusb` / `hidraw`). It does **not** rely on custom kernel modules, out-of-tree DKMS drivers, or manufacturer daemons. Any Linux kernel from version 3.x onward natively supports this.

2. **Systemd vs Non-Systemd Autostart**:
   * **On systemd systems** (RHEL, Fedora, Ubuntu, Debian, Arch, openSUSE):
     The included user unit runs via `systemctl --user` with `loginctl enable-linger`, applying colors at system startup without root privileges.
   * **On non-systemd systems** (OpenRC, runit, s6, sysvinit):
     Add the command to your session autostart (`~/.config/autostart/msi-rgb.desktop`), user profile (`~/.xprofile` or `~/.xinitrc`), or system startup script (`/etc/rc.local`).

3. **User Permissions & Optional udev Rule**:
   On distributions with standard desktop sessions (GNOME, KDE, etc.), `systemd-logind` automatically grants the active local console user access to HID devices.
   
   If you run on a headless, minimal, or server install (e.g. minimal RHEL server without an active graphical seat) and receive permission errors when running without `sudo`, install a udev rule to grant read/write access:

```bash
sudo tee /etc/udev/rules.d/99-steelseries.rules << 'EOF'
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="1038", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="1038", MODE="0666"
EOF
```

Then reload udev rules:

```bash
sudo udevadm control --reload-rules && \
sudo udevadm trigger
```

---

### Hardware Generation & Protocol Compatibility

Modern MSI laptops with SteelSeries per-key RGB fall into two main hardware architectures:

* **Modern Protocol (Supported by this tool)**:
  - Models: GE76, GE66, GP76, GP66, GS66, Raider GE77/78, Vector GP68/76/77, Stealth 15/17, Titan GT77 (2020 to present).
  - Protocol: 524-byte feature reports (Report ID `0x0E`), 6-frame steady effect setup (`0x0B`), and 92-byte activation frame (`0x1C`).
* **Legacy Protocol (Supported by `msi-perkeyrgb`)**:
  - Models: Older GE63, GE75, GS65 series (2017–2019, typical Product ID `1038:1122`).
  - Protocol: Legacy 64-byte chunks with Report IDs `0x00`/`0x01`.

---

## Command Reference

| Flag | Description | Default |
| :--- | :--- | :--- |
| `-h`, `--help` | Show command-line help message and exit | None |
| `--color`, `-c` | Base HTML hex color (`ff0000`, `00ff00`, etc.) | `ff0000` |
| `--theme`, `-t` | Predefined theme (`cyberpunk`, `matrix`, `fire`, etc.) | None |
| `--brightness`, `-b`| Brightness scaling percentage (`1` to `100`) | `100` |
| `--device`, `-d` | Target device (`keyboard`, `lightbar`, or `both`) | `both` |
| `--keyboard-id`, `--kb-id` | Custom Keyboard USB ID (`1038:113a` or `113a`) | `1038:113a` |
| `--lightbar-id`, `--lb-id` | Custom Lightbar USB ID (`1038:113e` or `113e`) | `1038:113e` |
| `--list-devices` | Scan and display connected SteelSeries HID devices | None |
| `--wasd` | Override color for WASD keys | None |
| `--arrows` | Override color for Arrow keys | None |
| `--numpad` | Override color for Numpad keys | None |
| `--lightbar-color`| Separate color for front lightbar only | Matches base |
| `--battery` | Map front lightbar to laptop battery percentage | Disabled |
| `--animate` | Live animation (`wave` or `breathe`) | None |
| `--speed` | Speed multiplier for presets & animations (`0.5`, `2.0`, etc.) | `1.0` |
| `--preset`, `-p` | Factory preset name from `presets.json` | None |
| `--list-presets` | Show available factory presets | None |

---

## Acknowledgements & Credits

* **[OpenRGB](https://openrgb.org)** for their tremendous work providing a universal, vendor-neutral RGB ecosystem across Linux.
* **[msi-perkeyrgb](https://github.com/Askannz/msi-perkeyrgb)** for pioneering early reverse engineering of MSI laptop keyboard protocols.
* **Design & Presets**: All curated designer themes (`cyberpunk`, `matrix`, `fire`, `ice`, `gaming`, `sunset`) and live animations (`wave`, `breathe`) are original custom profiles created specifically for this project. The factory presets (`aqua`, `disco`, etc.) correspond to the laptop's built-in onboard firmware animation profiles.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
