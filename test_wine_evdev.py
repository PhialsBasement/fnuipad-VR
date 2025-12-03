#!/usr/bin/env python3
"""
Automated test for evdev virtual gamepad and Wine compatibility.

Tests:
1. Virtual gamepad creation with 32 buttons and 8 axes
2. All button presses are registered via evdev
3. All axis movements are registered via evdev
4. Wine detection of the device (if Wine is available)

Usage:
    python test_wine_evdev.py           # Run all tests
    python test_wine_evdev.py --wine    # Include Wine joystick test
    python test_wine_evdev.py -v        # Verbose output
"""

import sys
import time
import argparse
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Dict, Set, Optional, List

try:
    from evdev import InputDevice, ecodes as e, list_devices
except ImportError:
    print("Error: evdev not installed. Run: pip install evdev")
    sys.exit(1)

from _linuxgamepad import LinuxGamepad


@dataclass
class TestResults:
    """Tracks test results"""
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: List[str] = field(default_factory=list)

    def ok(self, name: str, verbose: bool = False):
        self.passed += 1
        if verbose:
            print(f"  [PASS] {name}")

    def fail(self, name: str, reason: str = ""):
        self.failed += 1
        msg = f"  [FAIL] {name}"
        if reason:
            msg += f": {reason}"
        print(msg)
        self.errors.append(f"{name}: {reason}")

    def skip(self, name: str, reason: str = ""):
        self.skipped += 1
        print(f"  [SKIP] {name}: {reason}")

    def summary(self) -> bool:
        total = self.passed + self.failed + self.skipped
        print()
        print("=" * 50)
        print(f"Results: {self.passed}/{total} passed", end="")
        if self.skipped:
            print(f", {self.skipped} skipped", end="")
        if self.failed:
            print(f", {self.failed} FAILED", end="")
        print()
        if self.errors:
            print()
            print("Failures:")
            for err in self.errors:
                print(f"  - {err}")
        print("=" * 50)
        return self.failed == 0


def find_test_device(name_pattern: str = "Test Gamepad") -> Optional[InputDevice]:
    """Find the virtual gamepad device by name"""
    for path in list_devices():
        try:
            dev = InputDevice(path)
            if name_pattern in dev.name:
                return dev
        except Exception:
            pass
    return None


def test_device_creation(results: TestResults, verbose: bool) -> Optional[LinuxGamepad]:
    """Test that virtual gamepad can be created"""
    print("\n[Test] Device Creation")

    try:
        gamepad = LinuxGamepad(name="Test Gamepad", device_id=99)
        results.ok("Create LinuxGamepad instance", verbose)
    except PermissionError:
        results.fail("Create LinuxGamepad", "Permission denied - run setup-script.sh")
        return None
    except Exception as ex:
        results.fail("Create LinuxGamepad", str(ex))
        return None

    # Give udev time to create device node
    time.sleep(0.2)

    # Find the device
    dev = find_test_device("Test Gamepad")
    if dev:
        results.ok(f"Device visible at {dev.path}", verbose)
    else:
        results.fail("Device visibility", "Device not found in /dev/input/")
        gamepad.close()
        return None

    return gamepad


def test_device_capabilities(gamepad: LinuxGamepad, results: TestResults, verbose: bool):
    """Test that device reports correct capabilities"""
    print("\n[Test] Device Capabilities")

    dev = find_test_device("Test Gamepad")
    if not dev:
        results.fail("Find device", "Device not found")
        return

    if verbose:
        print(f"  Device: {dev.name} at {dev.path}")

    # Get capabilities without verbose mode - returns {event_type: [codes...]}
    caps = dev.capabilities()

    if verbose:
        print(f"  Capability types: {list(caps.keys())}")

    # Check axes - EV_ABS returns list of (code, AbsInfo) tuples
    abs_caps = caps.get(e.EV_ABS, [])
    # Extract just the codes from the tuples
    abs_codes = []
    for item in abs_caps:
        if isinstance(item, tuple):
            abs_codes.append(item[0])
        else:
            abs_codes.append(item)

    expected_axes = [
        (e.ABS_X, "ABS_X (left stick X)"),
        (e.ABS_Y, "ABS_Y (left stick Y)"),
        (e.ABS_RX, "ABS_RX (right stick X)"),
        (e.ABS_RY, "ABS_RY (right stick Y)"),
        (e.ABS_Z, "ABS_Z (left trigger)"),
        (e.ABS_RZ, "ABS_RZ (right trigger)"),
        (e.ABS_HAT0X, "ABS_HAT0X (dpad X)"),
        (e.ABS_HAT0Y, "ABS_HAT0Y (dpad Y)"),
    ]

    for code, name in expected_axes:
        if code in abs_codes:
            results.ok(f"Has axis {name}", verbose)
        else:
            results.fail(f"Has axis {name}", "Not found in capabilities")

    # Check buttons - EV_KEY returns list of codes directly
    key_caps = caps.get(e.EV_KEY, [])

    # Standard buttons
    standard_buttons = [
        (e.BTN_A, "BTN_A"),
        (e.BTN_B, "BTN_B"),
        (e.BTN_X, "BTN_X"),
        (e.BTN_Y, "BTN_Y"),
        (e.BTN_TL, "BTN_TL (LB)"),
        (e.BTN_TR, "BTN_TR (RB)"),
        (e.BTN_THUMBL, "BTN_THUMBL (LS)"),
        (e.BTN_THUMBR, "BTN_THUMBR (RS)"),
        (e.BTN_START, "BTN_START"),
        (e.BTN_SELECT, "BTN_SELECT"),
        (e.BTN_MODE, "BTN_MODE (Guide)"),
    ]

    for code, name in standard_buttons:
        if code in key_caps:
            results.ok(f"Has button {name}", verbose)
        else:
            results.fail(f"Has button {name}", "Not found")

    # Check TRIGGER_HAPPY buttons (for 32 button support)
    trigger_happy_count = 0
    for i in range(40):
        if (e.BTN_TRIGGER_HAPPY1 + i) in key_caps:
            trigger_happy_count += 1

    if trigger_happy_count >= 32:
        results.ok(f"Has {trigger_happy_count} TRIGGER_HAPPY buttons (32+ required)", verbose)
    else:
        results.fail(f"TRIGGER_HAPPY buttons", f"Only {trigger_happy_count} found, need 32+")

    dev.close()


def test_button_events(gamepad: LinuxGamepad, results: TestResults, verbose: bool):
    """Test that button presses generate correct events"""
    print("\n[Test] Button Events (32 buttons)")

    dev = find_test_device("Test Gamepad")
    if not dev:
        results.fail("Find device", "Device not found")
        return

    # Set device to non-blocking
    dev.grab()

    received_buttons: Set[int] = set()
    stop_event = threading.Event()

    def reader():
        try:
            while not stop_event.is_set():
                from select import select
                r, _, _ = select([dev.fd], [], [], 0.1)
                if r:
                    for event in dev.read():
                        if event.type == e.EV_KEY and event.value == 1:
                            received_buttons.add(event.code)
        except Exception:
            pass

    # Start reader thread
    reader_thread = threading.Thread(target=reader, daemon=True)
    reader_thread.start()

    # Test all 32 generic buttons
    time.sleep(0.1)
    for i in range(1, 33):
        btn_name = f"btn_{i}"
        gamepad.press(btn_name)
        gamepad.sync()
        time.sleep(0.02)
        gamepad.release(btn_name)
        gamepad.sync()
        time.sleep(0.02)

    # Wait for events
    time.sleep(0.2)
    stop_event.set()
    reader_thread.join(timeout=1)

    dev.ungrab()
    dev.close()

    # Check results
    expected_codes = set(e.BTN_TRIGGER_HAPPY1 + i - 1 for i in range(1, 33))
    received_trigger_happy = received_buttons & expected_codes

    if len(received_trigger_happy) == 32:
        results.ok("All 32 buttons received", verbose)
    else:
        missing = 32 - len(received_trigger_happy)
        results.fail("Button events", f"Missing {missing} buttons")

    # Also test named buttons
    named_buttons = ['a', 'b', 'x', 'y', 'lb', 'rb', 'start', 'select', 'guide']
    named_received = 0

    dev = find_test_device("Test Gamepad")
    dev.grab()
    received_buttons.clear()
    stop_event.clear()

    reader_thread = threading.Thread(target=reader, daemon=True)
    reader_thread.start()

    time.sleep(0.1)
    for btn in named_buttons:
        gamepad.press(btn)
        gamepad.sync()
        time.sleep(0.02)
        gamepad.release(btn)
        gamepad.sync()
        time.sleep(0.02)

    time.sleep(0.2)
    stop_event.set()
    reader_thread.join(timeout=1)

    dev.ungrab()
    dev.close()

    if len(received_buttons) >= len(named_buttons):
        results.ok(f"Named buttons received ({len(received_buttons)})", verbose)
    else:
        results.fail("Named button events", f"Only {len(received_buttons)}/{len(named_buttons)}")


def test_axis_events(gamepad: LinuxGamepad, results: TestResults, verbose: bool):
    """Test that axis movements generate correct events"""
    print("\n[Test] Axis Events (8 axes)")

    dev = find_test_device("Test Gamepad")
    if not dev:
        results.fail("Find device", "Device not found")
        return

    dev.grab()

    received_axes: Set[int] = set()
    stop_event = threading.Event()

    def reader():
        try:
            while not stop_event.is_set():
                from select import select
                r, _, _ = select([dev.fd], [], [], 0.1)
                if r:
                    for event in dev.read():
                        if event.type == e.EV_ABS:
                            received_axes.add(event.code)
        except Exception:
            pass

    reader_thread = threading.Thread(target=reader, daemon=True)
    reader_thread.start()

    time.sleep(0.1)

    # Test sticks
    gamepad.set_stick('left', 1.0, 0.5)
    gamepad.sync()
    time.sleep(0.05)
    gamepad.set_stick('left', 0, 0)
    gamepad.sync()

    gamepad.set_stick('right', -0.5, 1.0)
    gamepad.sync()
    time.sleep(0.05)
    gamepad.set_stick('right', 0, 0)
    gamepad.sync()

    # Test triggers
    gamepad.set_trigger('left', 1.0)
    gamepad.sync()
    time.sleep(0.05)
    gamepad.set_trigger('left', 0)
    gamepad.sync()

    gamepad.set_trigger('right', 0.75)
    gamepad.sync()
    time.sleep(0.05)
    gamepad.set_trigger('right', 0)
    gamepad.sync()

    # Test dpad
    gamepad.set_dpad(1, -1)
    gamepad.sync()
    time.sleep(0.05)
    gamepad.set_dpad(0, 0)
    gamepad.sync()

    time.sleep(0.2)
    stop_event.set()
    reader_thread.join(timeout=1)

    dev.ungrab()
    dev.close()

    expected_axes = {e.ABS_X, e.ABS_Y, e.ABS_RX, e.ABS_RY, e.ABS_Z, e.ABS_RZ, e.ABS_HAT0X, e.ABS_HAT0Y}

    if received_axes >= expected_axes:
        results.ok(f"All 8 axes received", verbose)
    else:
        missing = expected_axes - received_axes
        results.fail("Axis events", f"Missing axes: {missing}")


def test_wine_detection(gamepad: LinuxGamepad, results: TestResults, verbose: bool):
    """Test that Wine can detect the joystick with all buttons/axes"""
    print("\n[Test] Wine Detection")

    import os
    import os.path

    # Check if wine is available
    try:
        result = subprocess.run(['wine', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            results.skip("Wine version", "Wine not working properly")
            return
        wine_version = result.stdout.strip()
        results.ok(f"Wine available: {wine_version}", verbose)
    except FileNotFoundError:
        results.skip("Wine detection", "Wine not installed")
        return
    except subprocess.TimeoutExpired:
        results.skip("Wine detection", "Wine timed out")
        return
    except Exception as ex:
        results.skip("Wine detection", str(ex))
        return

    # Query winebus configuration
    try:
        result = subprocess.run(
            ['wine', 'reg', 'query',
             r'HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\winebus'],
            capture_output=True, text=True, timeout=10,
            env={**os.environ, 'WINEDEBUG': '-all'}
        )

        if result.returncode == 0:
            output = result.stdout
            if 'Enable SDL' in output and '0x0' in output:
                results.ok("winebus SDL disabled (evdev mode)", verbose)
            elif 'Enable SDL' in output:
                results.ok("winebus SDL enabled (XInput mode)", verbose)
            else:
                results.ok("winebus config present", verbose)
        else:
            results.ok("winebus using defaults (SDL mode)", verbose)
    except Exception as ex:
        results.skip("winebus config check", str(ex))

    # Find wine_joy_test.exe
    script_dir = os.path.dirname(os.path.abspath(__file__))
    exe_path = os.path.join(script_dir, 'wine_joy_test.exe')

    if not os.path.exists(exe_path):
        # Try to compile it
        c_path = os.path.join(script_dir, 'wine_joy_test.c')
        if os.path.exists(c_path):
            try:
                compile_result = subprocess.run(
                    ['x86_64-w64-mingw32-gcc', '-o', exe_path, c_path, '-lwinmm'],
                    capture_output=True, text=True, timeout=30
                )
                if compile_result.returncode != 0:
                    results.skip("Wine joystick test", "Failed to compile wine_joy_test.exe (install mingw-w64-gcc)")
                    return
            except FileNotFoundError:
                results.skip("Wine joystick test", "mingw-w64-gcc not found (install mingw-w64-gcc)")
                return
        else:
            results.skip("Wine joystick test", "wine_joy_test.exe not found")
            return

    # Run the test executable under Wine
    try:
        result = subprocess.run(
            ['wine', exe_path],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, 'WINEDEBUG': '-all'}
        )

        output = result.stdout
        if verbose:
            print("  Wine joystick query output:")
            for line in output.strip().split('\n'):
                print(f"    {line}")

        # Parse results
        parsed = {}
        for line in output.strip().split('\n'):
            if '=' in line:
                key, _, value = line.partition('=')
                parsed[key.strip()] = value.strip()

        # Check results
        num_devs = int(parsed.get('NUM_DEVS', 0))
        found_count = int(parsed.get('FOUND_COUNT', 0))
        test_found = parsed.get('TEST_FOUND', '0') == '1'
        test_buttons = int(parsed.get('TEST_BUTTONS', 0))
        test_axes = int(parsed.get('TEST_AXES', 0))

        results.ok(f"Wine reports {num_devs} joystick ports", verbose)

        if found_count > 0:
            results.ok(f"Wine detected {found_count} joystick(s)", verbose)
        else:
            results.fail("Wine joystick detection", "No joysticks detected by Wine")
            return

        if test_found:
            results.ok("Wine sees Test Gamepad device", verbose)

            if test_buttons >= 32:
                results.ok(f"Wine reports {test_buttons} buttons (32+ required)", verbose)
            elif test_buttons >= 10:
                results.fail("Wine button count", f"Only {test_buttons} buttons (SDL/XInput mode). Run: python wine_setup.py evdev")
            else:
                results.fail("Wine button count", f"Only {test_buttons} buttons detected")

            if test_axes >= 6:
                results.ok(f"Wine reports {test_axes} axes", verbose)
            else:
                results.fail("Wine axis count", f"Only {test_axes} axes detected")
        else:
            # List what joysticks were found
            joy_names = [v for k, v in parsed.items() if k.endswith('_NAME')]
            results.fail("Wine Test Gamepad detection", f"Found joysticks: {joy_names}, but not Test Gamepad")

    except subprocess.TimeoutExpired:
        results.fail("Wine joystick test", "Wine timed out")
    except Exception as ex:
        results.fail("Wine joystick test", str(ex))


def test_rapid_input(gamepad: LinuxGamepad, results: TestResults, verbose: bool):
    """Test rapid input doesn't cause issues"""
    print("\n[Test] Rapid Input Stress Test")

    dev = find_test_device("Test Gamepad")
    if not dev:
        results.fail("Find device", "Device not found")
        return

    dev.grab()

    event_count = 0
    stop_event = threading.Event()

    def reader():
        nonlocal event_count
        try:
            while not stop_event.is_set():
                from select import select
                r, _, _ = select([dev.fd], [], [], 0.1)
                if r:
                    for event in dev.read():
                        if event.type in (e.EV_KEY, e.EV_ABS):
                            event_count += 1
        except Exception:
            pass

    reader_thread = threading.Thread(target=reader, daemon=True)
    reader_thread.start()

    time.sleep(0.1)

    # Rapid fire inputs
    iterations = 100
    for i in range(iterations):
        gamepad.set_stick('left', (i % 10) / 10.0, ((i + 5) % 10) / 10.0)
        gamepad.press(f'btn_{(i % 32) + 1}')
        gamepad.sync()
        gamepad.release(f'btn_{(i % 32) + 1}')
        gamepad.sync()

    time.sleep(0.3)
    stop_event.set()
    reader_thread.join(timeout=1)

    dev.ungrab()
    dev.close()

    # We expect at least 2 events per iteration (press + release)
    expected_min = iterations * 2
    if event_count >= expected_min:
        results.ok(f"Handled {event_count} rapid events", verbose)
    else:
        results.fail("Rapid input", f"Only {event_count}/{expected_min} events received")


def main():
    parser = argparse.ArgumentParser(description="Test evdev gamepad and Wine compatibility")
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--wine', action='store_true', help='Include Wine detection test')
    parser.add_argument('--stress', action='store_true', help='Include stress test')
    args = parser.parse_args()

    print("=" * 50)
    print("VR Gamepad - evdev & Wine Compatibility Test")
    print("=" * 50)

    results = TestResults()

    # Test device creation
    gamepad = test_device_creation(results, args.verbose)
    if not gamepad:
        print("\nCannot continue without gamepad device.")
        results.summary()
        return 1

    try:
        # Test capabilities
        test_device_capabilities(gamepad, results, args.verbose)

        # Test button events
        test_button_events(gamepad, results, args.verbose)

        # Test axis events
        test_axis_events(gamepad, results, args.verbose)

        # Optional stress test
        if args.stress:
            test_rapid_input(gamepad, results, args.verbose)

        # Optional Wine test
        if args.wine:
            test_wine_detection(gamepad, results, args.verbose)

    finally:
        gamepad.close()

    success = results.summary()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
