# VR Gamepad Mapper

A Linux tool that maps VR controller inputs to a virtual gamepad using OpenVR and uinput. Play non-VR games with your VR controllers.

Perfect for flight sims in VR where you need a reasonable amount of inputs without taking off your headset to find keyboard keys. With 32 buttons, 8 axes, and chord support, you can map all essential flight controls to your VR controllers.

## Features

- **Virtual Gamepad**: Creates a 32-button, 8-axis virtual joystick device
- **Flexible Mapping**: Configure any VR input to any gamepad output
- **Chord Support**: Combine buttons (e.g., Grip+Trigger = Guide)
- **Profile System**: Save and load mapping configurations
- **GUI Tools**: Visual configuration editor and gamepad monitor
- **Wine/Proton Compatible**: Full button support in Windows games

## Requirements

- Linux with uinput support
- Python 3.8+
- SteamVR
- Python packages: `evdev`, `openvr`

## Installation

### 1. Install dependencies

```bash
pip install evdev openvr
```

### 2. Setup permissions

Run the setup script (requires sudo):

```bash
sudo ./setup-script.sh
```

Or manually:

```bash
sudo modprobe uinput
sudo usermod -aG input $USER
echo 'KERNEL=="uinput", GROUP="input", MODE="0660"' | sudo tee /etc/udev/rules.d/99-uinput.rules
sudo udevadm control --reload-rules
```

Log out and back in for group changes to take effect.

## Usage

### Run with default mappings

```bash
python vr_gamepad_main.py
```

### Run with a custom profile

```bash
python vr_gamepad_main.py -c my_profile.json
```

### Open the configuration GUI

```bash
python vr_gamepad_main.py --gui
```

### Open the gamepad monitor

```bash
python vr_gamepad_main.py --monitor
```

### List available inputs/outputs

```bash
python vr_gamepad_main.py --list-inputs
python vr_gamepad_main.py --list-outputs
```

### Save default profile to file

```bash
python vr_gamepad_main.py --save-default my_profile.json
```

## Default Mapping (Quest/Index Controllers)

| VR Input | Gamepad Output |
|----------|----------------|
| Left Thumbstick | Left Stick |
| Right Thumbstick | Right Stick |
| Left Trigger | Left Trigger (LT) |
| Right Trigger | Right Trigger (RT) |
| Left Grip | Left Bumper (LB) |
| Right Grip | Right Bumper (RB) |
| A Button | A |
| B Button | B |
| X Button | X |
| Y Button | Y |
| Left Thumbstick Click | L3 |
| Right Thumbstick Click | R3 |
| Left Menu | Select |
| Right Menu | Start |
| Right Grip + Right Trigger | Guide |

## Creating Custom Mappings

### Using the GUI

1. Run `python vr_gamepad_main.py --gui`
2. Click "Add Mapping"
3. Select input controller (left/right), type (button/axis), and input name
4. Select output type and name
5. Optionally add conditions for chords
6. Save profile to JSON file

### Profile JSON Format

```json
{
  "name": "My Profile",
  "mappings": [
    {
      "name": "A Button",
      "input": { "type": "button", "controller": "right", "name": "a_button" },
      "output": { "type": "button", "name": "a" },
      "conditions": [],
      "modifiers": { "invert": false, "sensitivity": 1.0, "deadzone": 0.0 },
      "priority": 0,
      "enabled": true
    }
  ],
  "settings": {
    "global_deadzone": 0.1,
    "haptic_intensity": 0.5
  }
}
```

### Chord Example

Map Grip+Trigger to Guide button:

```json
{
  "name": "Guide (Chord)",
  "input": { "type": "button", "controller": "right", "name": "trigger_click" },
  "output": { "type": "button", "name": "guide" },
  "conditions": [
    { "type": "button_held", "controller": "right", "input": "grip_click", "value": 0.5 }
  ],
  "priority": 10
}
```

Higher priority mappings are checked first, so chords take precedence over regular mappings.

## VR Inputs

**Buttons** (left/right controller):
- `trigger_click`, `trigger_touch`
- `grip_click`, `grip_touch`
- `trackpad_click`, `trackpad_touch`
- `thumbstick_click`, `thumbstick_touch`
- `menu`, `system`
- `a_button`, `b_button` (right) / `x_button`, `y_button` (left)

**Axes** (left/right controller):
- `trigger`, `grip`
- `trackpad_x`, `trackpad_y`
- `thumbstick_x`, `thumbstick_y`

## Gamepad Outputs

**Buttons**:
- Face: `a`, `b`, `x`, `y`
- Bumpers: `lb`, `rb`
- Sticks: `ls`, `rs`
- Menu: `start`, `select`, `guide`
- D-pad: `dpad_up`, `dpad_down`, `dpad_left`, `dpad_right`
- Directional clicks: `ls_up`, `ls_down`, `ls_left`, `ls_right`, `rs_up`, `rs_down`, `rs_left`, `rs_right`
- Back paddles: `back_lu`, `back_ll`, `back_ru`, `back_rl`
- Generic: `btn_1` through `btn_32`

**Axes**:
- Sticks: `left_stick_x`, `left_stick_y`, `right_stick_x`, `right_stick_y`
- Triggers: `left_trigger`, `right_trigger`
- D-pad: `dpad_x`, `dpad_y`
- Generic: `axis_1` through `axis_8`

## Wine/Proton Setup

By default, Wine uses SDL which limits detection to ~10 XInput buttons. To enable full 32-button support:

```bash
# Enable evdev mode (full button support)
python wine_setup.py evdev

# For Proton games, specify the prefix
python wine_setup.py --prefix ~/.steam/steam/steamapps/compatdata/<APPID>/pfx evdev

# Revert to SDL mode if needed
python wine_setup.py sdl

# Check current configuration
python wine_setup.py status
```

Test with Wine's joystick control panel:

```bash
wine control joy.cpl
```

## Testing

Test the virtual gamepad without VR:

```bash
# Automated test
python test_gamepad.py

# Interactive keyboard test
python test_gamepad.py --interactive
```

Test evdev and 32-button support (including Wine compatibility):

```bash
# Basic evdev test
python test_wine_evdev.py

# Verbose output
python test_wine_evdev.py -v

# Include Wine detection test
python test_wine_evdev.py --wine

# Include stress test
python test_wine_evdev.py --stress

# All tests
python test_wine_evdev.py -v --wine --stress
```

Verify with evtest:

```bash
evtest /dev/input/eventX  # where X is your device
```

## Troubleshooting

### Permission denied for /dev/uinput

```bash
sudo modprobe uinput
sudo usermod -aG input $USER
# Log out and back in
```

### SteamVR not detected

Make sure SteamVR is running before starting the mapper.

### Controllers not found

The mapper searches for controllers when they're available. Make sure your VR headset is on and controllers are paired.

### Game doesn't see all buttons

Run `python wine_setup.py evdev` to enable full button detection in Wine/Proton games.

## Files

| File | Description |
|------|-------------|
| `vr_gamepad_main.py` | Main entry point |
| `_linuxgamepad.py` | Virtual gamepad via uinput |
| `_mapping.py` | Mapping profile system |
| `_mapping_engine.py` | Input processing engine |
| `config_gui.py` | Configuration GUI |
| `monitor_gui.py` | Gamepad state monitor |
| `test_gamepad.py` | Testing utility |
| `test_wine_evdev.py` | evdev and Wine compatibility test |
| `wine_joy_test.c` | Windows joystick test source (for Wine) |
| `wine_joy_test.exe` | Compiled Windows test (auto-built if missing) |
| `setup-script.sh` | Permission setup script |
| `wine_setup.py` | Wine/Proton configuration |

## License

MIT
