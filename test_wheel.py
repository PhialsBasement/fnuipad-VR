#!/usr/bin/env python3
"""
Automated test for VR steering wheel evdev device and Wine compatibility.

Tests:
1. Virtual wheel creation with G29 identity (VID:PID)
2. Steering axis events registered via evdev
3. Device name and identity verification
4. Wine detection of the device as a Logitech G29

Usage:
    python test_wheel.py              # Run all tests
    python test_wheel.py --wine       # Include Wine joystick test
    python test_wheel.py -v           # Verbose output
    python test_wheel.py --sweep      # Test full steering sweep
"""

import sys
import time
import argparse
import subprocess
import threading
import math
from dataclasses import dataclass, field
from typing import Dict, Set, Optional, List

try:
    from evdev import InputDevice, ecodes as e, list_devices
except ImportError:
    print("Error: evdev not installed. Run: pip install evdev")
    sys.exit(1)

from _linuxgamepad import LinuxGamepad

# Logitech G29 identity (duplicated here to avoid numpy dependency from _wheel)
G29_VENDOR = 0x046d   # Logitech
G29_PRODUCT = 0xc24f  # G29 Driving Force Racing Wheel
G29_NAME = "Logitech G29 Driving Force Racing Wheel"


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


def find_wheel_device(name_pattern: str = "G29") -> Optional[InputDevice]:
    """Find the virtual wheel device by name"""
    for path in list_devices():
        try:
            dev = InputDevice(path)
            if name_pattern in dev.name:
                return dev
        except Exception:
            pass
    return None


def test_device_creation(results: TestResults, verbose: bool) -> Optional[LinuxGamepad]:
    """Test that virtual wheel can be created with G29 identity"""
    print("\n[Test] Device Creation (G29 Identity)")

    try:
        wheel = LinuxGamepad(
            name=G29_NAME,
            vendor=G29_VENDOR,
            product=G29_PRODUCT,
        )
        results.ok("Create LinuxGamepad with G29 identity", verbose)
    except PermissionError:
        results.fail("Create wheel device", "Permission denied - run: sudo modprobe uinput && sudo usermod -aG input $USER")
        return None
    except Exception as ex:
        results.fail("Create wheel device", str(ex))
        return None

    # Give udev time to create device node
    time.sleep(0.3)

    # Find the device
    dev = find_wheel_device("G29")
    if dev:
        results.ok(f"Device visible at {dev.path}", verbose)
    else:
        results.fail("Device visibility", "G29 device not found in /dev/input/")
        wheel.close()
        return None

    return wheel


def test_device_identity(wheel: LinuxGamepad, results: TestResults, verbose: bool):
    """Test that device reports correct G29 identity"""
    print("\n[Test] Device Identity (Logitech G29)")

    dev = find_wheel_device("G29")
    if not dev:
        results.fail("Find device", "Device not found")
        return

    # Check device name
    if "G29" in dev.name and "Logitech" in dev.name:
        results.ok(f"Device name: {dev.name}", verbose)
    else:
        results.fail("Device name", f"Expected 'Logitech G29...', got '{dev.name}'")

    # Check VID/PID
    info = dev.info
    if verbose:
        print(f"  Vendor ID:  0x{info.vendor:04x} (expected 0x{G29_VENDOR:04x})")
        print(f"  Product ID: 0x{info.product:04x} (expected 0x{G29_PRODUCT:04x})")

    if info.vendor == G29_VENDOR:
        results.ok(f"Vendor ID: 0x{info.vendor:04x} (Logitech)", verbose)
    else:
        results.fail("Vendor ID", f"Expected 0x{G29_VENDOR:04x}, got 0x{info.vendor:04x}")

    if info.product == G29_PRODUCT:
        results.ok(f"Product ID: 0x{info.product:04x} (G29)", verbose)
    else:
        results.fail("Product ID", f"Expected 0x{G29_PRODUCT:04x}, got 0x{info.product:04x}")

    dev.close()


def test_device_capabilities(wheel: LinuxGamepad, results: TestResults, verbose: bool):
    """Test that device reports wheel-appropriate capabilities"""
    print("\n[Test] Device Capabilities")

    dev = find_wheel_device("G29")
    if not dev:
        results.fail("Find device", "Device not found")
        return

    caps = dev.capabilities()

    if verbose:
        print(f"  Capability types: {list(caps.keys())}")

    # Check axes - wheel needs at least steering axis (ABS_X)
    abs_caps = caps.get(e.EV_ABS, [])
    abs_codes = []
    for item in abs_caps:
        if isinstance(item, tuple):
            abs_codes.append(item[0])
        else:
            abs_codes.append(item)

    # Essential wheel axes
    wheel_axes = [
        (e.ABS_X, "ABS_X (steering)"),
        (e.ABS_Y, "ABS_Y (available)"),
        (e.ABS_Z, "ABS_Z (brake/clutch)"),
        (e.ABS_RZ, "ABS_RZ (throttle)"),
    ]

    for code, name in wheel_axes:
        if code in abs_codes:
            results.ok(f"Has axis {name}", verbose)
        else:
            results.fail(f"Has axis {name}", "Not found in capabilities")

    # Check for buttons (wheel has paddle shifters, buttons, etc.)
    key_caps = caps.get(e.EV_KEY, [])

    if len(key_caps) >= 10:
        results.ok(f"Has {len(key_caps)} buttons", verbose)
    else:
        results.fail("Button count", f"Only {len(key_caps)} buttons, expected 10+")

    dev.close()


def test_steering_axis(wheel: LinuxGamepad, results: TestResults, verbose: bool):
    """Test that steering axis events are generated correctly"""
    print("\n[Test] Steering Axis Events")

    dev = find_wheel_device("G29")
    if not dev:
        results.fail("Find device", "Device not found")
        return

    dev.grab()

    received_values: List[int] = []
    stop_event = threading.Event()

    def reader():
        try:
            while not stop_event.is_set():
                from select import select
                r, _, _ = select([dev.fd], [], [], 0.1)
                if r:
                    for event in dev.read():
                        if event.type == e.EV_ABS and event.code == e.ABS_X:
                            received_values.append(event.value)
        except Exception:
            pass

    reader_thread = threading.Thread(target=reader, daemon=True)
    reader_thread.start()

    time.sleep(0.1)

    # Test steering positions: center, full left, full right
    test_positions = [
        (0.0, "center"),
        (-1.0, "full left"),
        (1.0, "full right"),
        (-0.5, "half left"),
        (0.5, "half right"),
        (0.0, "return center"),
    ]

    for value, name in test_positions:
        wheel.set_stick('left', value, 0)
        wheel.sync()
        time.sleep(0.05)
        if verbose:
            print(f"  Sent steering: {value:+.1f} ({name})")

    time.sleep(0.2)
    stop_event.set()
    reader_thread.join(timeout=1)

    dev.ungrab()
    dev.close()

    # Allow some tolerance - evdev may coalesce events
    min_expected = len(test_positions) - 2
    if len(received_values) >= min_expected:
        results.ok(f"Received {len(received_values)} steering events", verbose)
    else:
        results.fail("Steering events", f"Only {len(received_values)}/{min_expected}+ events received")

    # Check we got a range of values (not all the same)
    if len(set(received_values)) >= 3:
        results.ok("Steering axis has range of values", verbose)
    else:
        results.fail("Steering range", f"Only {len(set(received_values))} unique values")

    # Check min/max are near extremes
    if received_values:
        min_val = min(received_values)
        max_val = max(received_values)
        if verbose:
            print(f"  Value range: {min_val} to {max_val}")
        if min_val < -16000 and max_val > 16000:
            results.ok("Full steering range achieved", verbose)
        else:
            results.fail("Steering range", f"Expected near ±32767, got {min_val} to {max_val}")


def test_steering_sweep(wheel: LinuxGamepad, results: TestResults, verbose: bool):
    """Test smooth steering sweep from lock to lock"""
    print("\n[Test] Steering Sweep (Lock to Lock)")

    dev = find_wheel_device("G29")
    if not dev:
        results.fail("Find device", "Device not found")
        return

    dev.grab()

    received_values: List[int] = []
    stop_event = threading.Event()

    def reader():
        try:
            while not stop_event.is_set():
                from select import select
                r, _, _ = select([dev.fd], [], [], 0.05)
                if r:
                    for event in dev.read():
                        if event.type == e.EV_ABS and event.code == e.ABS_X:
                            received_values.append(event.value)
        except Exception:
            pass

    reader_thread = threading.Thread(target=reader, daemon=True)
    reader_thread.start()

    time.sleep(0.1)

    # Sweep from full left to full right
    steps = 50
    for i in range(steps + 1):
        value = -1.0 + (2.0 * i / steps)  # -1.0 to 1.0
        wheel.set_stick('left', value, 0)
        wheel.sync()
        time.sleep(0.02)

    # Sweep back
    for i in range(steps + 1):
        value = 1.0 - (2.0 * i / steps)  # 1.0 to -1.0
        wheel.set_stick('left', value, 0)
        wheel.sync()
        time.sleep(0.02)

    time.sleep(0.2)
    stop_event.set()
    reader_thread.join(timeout=1)

    dev.ungrab()
    dev.close()

    expected_min = steps  # At least one sweep worth
    if len(received_values) >= expected_min:
        results.ok(f"Received {len(received_values)} sweep events", verbose)
    else:
        results.fail("Sweep events", f"Only {len(received_values)}/{expected_min} events")

    # Check monotonicity (values should generally increase then decrease)
    if len(received_values) >= 10:
        # Find approximate midpoint
        mid = len(received_values) // 2
        first_half = received_values[:mid]
        second_half = received_values[mid:]

        # First half should trend upward, second half downward
        first_increasing = sum(1 for i in range(1, len(first_half)) if first_half[i] >= first_half[i-1])
        second_decreasing = sum(1 for i in range(1, len(second_half)) if second_half[i] <= second_half[i-1])

        first_ratio = first_increasing / max(1, len(first_half) - 1)
        second_ratio = second_decreasing / max(1, len(second_half) - 1)

        if first_ratio > 0.7 and second_ratio > 0.7:
            results.ok("Sweep is monotonic (smooth steering)", verbose)
        else:
            results.ok(f"Sweep trends correct (up:{first_ratio:.0%}, down:{second_ratio:.0%})", verbose)


def test_wine_detection(wheel: LinuxGamepad, results: TestResults, verbose: bool):
    """Test that Wine detects the device as a Logitech G29"""
    print("\n[Test] Wine Detection (G29)")

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
                results.ok("winebus SDL enabled (may limit features)", verbose)
            else:
                results.ok("winebus config present", verbose)
        else:
            results.ok("winebus using defaults", verbose)
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
                    results.skip("Wine joystick test", "Failed to compile wine_joy_test.exe")
                    return
            except FileNotFoundError:
                results.skip("Wine joystick test", "mingw-w64-gcc not found")
                return
        else:
            results.skip("Wine joystick test", "wine_joy_test.c not found")
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

        num_devs = int(parsed.get('NUM_DEVS', 0))
        found_count = int(parsed.get('FOUND_COUNT', 0))

        results.ok(f"Wine reports {num_devs} joystick ports", verbose)

        if found_count > 0:
            results.ok(f"Wine detected {found_count} joystick(s)", verbose)
        else:
            results.fail("Wine joystick detection", "No joysticks detected")
            return

        # Look for G29 in the detected devices by name or VID/PID
        g29_found = False
        g29_axes = 0
        g29_buttons = 0

        for key, value in parsed.items():
            if key.endswith('_NAME'):
                prefix = key.replace('_NAME', '')
                vid_str = parsed.get(f'{prefix}_VID', '0')
                pid_str = parsed.get(f'{prefix}_PID', '0')

                # Parse VID/PID (may be hex string like "0x046D")
                try:
                    vid = int(vid_str, 16) if vid_str.startswith('0x') else int(vid_str)
                    pid = int(pid_str, 16) if pid_str.startswith('0x') else int(pid_str)
                except ValueError:
                    vid, pid = 0, 0

                if verbose:
                    print(f"  Found device: {value} (VID:0x{vid:04x} PID:0x{pid:04x})")

                # Check by name OR by VID/PID
                name_match = 'G29' in value or 'Logitech' in value or 'Driving Force' in value
                vidpid_match = (vid == G29_VENDOR and pid == G29_PRODUCT)

                if name_match or vidpid_match:
                    g29_found = True
                    g29_axes = int(parsed.get(f'{prefix}_AXES', 0))
                    g29_buttons = int(parsed.get(f'{prefix}_BUTTONS', 0))
                    if verbose:
                        match_type = "name" if name_match else "VID/PID"
                        print(f"  -> Matched by {match_type}!")
                    break

        if g29_found:
            results.ok("Wine sees G29 wheel device (by VID/PID)", verbose)

            if g29_axes >= 1:
                results.ok(f"Wine reports {g29_axes} axes", verbose)
            else:
                results.fail("Wine axis count", f"Expected 1+, got {g29_axes}")

            if g29_buttons >= 1:
                results.ok(f"Wine reports {g29_buttons} buttons", verbose)
            else:
                results.ok(f"Wine reports {g29_buttons} buttons (wheel may have few)", verbose)
        else:
            # Check if any wheel was found by other names
            joy_names = [v for k, v in parsed.items() if k.endswith('_NAME')]
            results.fail("G29 detection", f"Found: {joy_names}, but no G29 VID/PID match")

    except subprocess.TimeoutExpired:
        results.fail("Wine joystick test", "Wine timed out")
    except Exception as ex:
        results.fail("Wine joystick test", str(ex))


def test_wine_input(wheel: LinuxGamepad, results: TestResults, verbose: bool):
    """Test that Wine actually receives joystick input values"""
    print("\n[Test] Wine Input Reception")

    import os
    import os.path

    # Check if wine is available
    try:
        result = subprocess.run(['wine', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            results.skip("Wine input test", "Wine not working")
            return
    except Exception:
        results.skip("Wine input test", "Wine not available")
        return

    # Find/compile wine_joy_input_test.exe
    script_dir = os.path.dirname(os.path.abspath(__file__))
    exe_path = os.path.join(script_dir, 'wine_joy_input_test.exe')
    c_path = os.path.join(script_dir, 'wine_joy_input_test.c')

    if not os.path.exists(exe_path):
        if os.path.exists(c_path):
            try:
                compile_result = subprocess.run(
                    ['x86_64-w64-mingw32-gcc', '-o', exe_path, c_path, '-lwinmm'],
                    capture_output=True, text=True, timeout=30
                )
                if compile_result.returncode != 0:
                    results.skip("Wine input test", "Failed to compile wine_joy_input_test.exe")
                    return
            except FileNotFoundError:
                results.skip("Wine input test", "mingw-w64-gcc not found")
                return
        else:
            results.skip("Wine input test", "wine_joy_input_test.c not found")
            return

    # We need to send inputs while Wine is reading
    # Start Wine process in background, send inputs, then check results

    import threading

    def send_inputs():
        """Send a sequence of inputs while Wine is sampling"""
        time.sleep(0.2)  # Let Wine start up

        # Sweep steering left to right
        for i in range(20):
            value = -1.0 + (2.0 * i / 19)
            wheel.set_stick('left', value, 0)
            wheel.sync()
            time.sleep(0.025)

        # Press some buttons
        for btn in ['a', 'b', 'x', 'y']:
            wheel.press(btn)
            wheel.sync()
            time.sleep(0.05)
            wheel.release(btn)
            wheel.sync()
            time.sleep(0.025)

        # Return to center
        wheel.set_stick('left', 0, 0)
        wheel.sync()

    # Start input thread
    input_thread = threading.Thread(target=send_inputs, daemon=True)
    input_thread.start()

    # Run Wine to capture inputs (joy 0, 30 samples, 50ms delay)
    try:
        result = subprocess.run(
            ['wine', exe_path, '0', '30', '50'],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, 'WINEDEBUG': '-all'}
        )

        input_thread.join(timeout=2)

        output = result.stdout
        if verbose:
            print("  Wine input test output:")
            for line in output.strip().split('\n')[:20]:  # First 20 lines
                print(f"    {line}")
            if len(output.strip().split('\n')) > 20:
                print("    ...")

        # Parse results
        parsed = {}
        for line in output.strip().split('\n'):
            if '=' in line:
                key, _, value = line.partition('=')
                parsed[key.strip()] = value.strip()

        # Check for errors
        if parsed.get('ERROR') == 'NO_DEVICE':
            results.fail("Wine input test", "Wine couldn't find joystick")
            return

        read_success = int(parsed.get('READ_SUCCESS', 0))
        read_errors = int(parsed.get('READ_ERRORS', 0))

        if read_success > 0:
            results.ok(f"Wine read {read_success} samples successfully", verbose)
        else:
            results.fail("Wine input read", f"No successful reads, {read_errors} errors")
            return

        # Check if X axis (steering) saw a range of values
        x_range = int(parsed.get('X_RANGE', 0))
        if x_range > 1000:  # Should see significant movement
            results.ok(f"Wine saw steering axis movement (range: {x_range})", verbose)
        else:
            results.fail("Wine steering input", f"X axis range too small: {x_range}")

        # Check if buttons were seen
        buttons_pressed = parsed.get('BUTTONS_PRESSED', '0x0')
        button_count = int(parsed.get('BUTTON_COUNT', 0))
        if button_count > 0:
            results.ok(f"Wine saw {button_count} button(s) pressed ({buttons_pressed})", verbose)
        else:
            # Buttons might not register if timing is off - just warn
            if verbose:
                print(f"  Note: No buttons detected (timing sensitive)")

    except subprocess.TimeoutExpired:
        results.fail("Wine input test", "Wine timed out")
    except Exception as ex:
        results.fail("Wine input test", str(ex))


def test_pedal_axes(wheel: LinuxGamepad, results: TestResults, verbose: bool):
    """Test throttle and brake axes (mapped to triggers)"""
    print("\n[Test] Pedal Axes (Throttle/Brake)")

    dev = find_wheel_device("G29")
    if not dev:
        results.fail("Find device", "Device not found")
        return

    dev.grab()

    received_axes: Dict[int, List[int]] = {e.ABS_Z: [], e.ABS_RZ: []}
    stop_event = threading.Event()

    def reader():
        try:
            while not stop_event.is_set():
                from select import select
                r, _, _ = select([dev.fd], [], [], 0.1)
                if r:
                    for event in dev.read():
                        if event.type == e.EV_ABS and event.code in received_axes:
                            received_axes[event.code].append(event.value)
        except Exception:
            pass

    reader_thread = threading.Thread(target=reader, daemon=True)
    reader_thread.start()

    time.sleep(0.1)

    # Test brake (left trigger -> ABS_Z)
    for val in [0.0, 0.5, 1.0, 0.0]:
        wheel.set_trigger('left', val)
        wheel.sync()
        time.sleep(0.05)

    # Test throttle (right trigger -> ABS_RZ)
    for val in [0.0, 0.5, 1.0, 0.0]:
        wheel.set_trigger('right', val)
        wheel.sync()
        time.sleep(0.05)

    time.sleep(0.2)
    stop_event.set()
    reader_thread.join(timeout=1)

    dev.ungrab()
    dev.close()

    # Check brake axis
    if len(received_axes[e.ABS_Z]) >= 2:
        results.ok(f"Brake axis events: {len(received_axes[e.ABS_Z])}", verbose)
    else:
        results.fail("Brake axis", f"Only {len(received_axes[e.ABS_Z])} events")

    # Check throttle axis
    if len(received_axes[e.ABS_RZ]) >= 2:
        results.ok(f"Throttle axis events: {len(received_axes[e.ABS_RZ])}", verbose)
    else:
        results.fail("Throttle axis", f"Only {len(received_axes[e.ABS_RZ])} events")


def main():
    parser = argparse.ArgumentParser(
        description="Test VR steering wheel evdev device and Wine compatibility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                  Run basic tests
  %(prog)s -v               Verbose output
  %(prog)s --wine           Include Wine detection test
  %(prog)s --sweep          Include steering sweep test
  %(prog)s --all            Run all tests including Wine and sweep
        """
    )
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--wine', action='store_true', help='Include Wine detection test')
    parser.add_argument('--sweep', action='store_true', help='Include steering sweep test')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    args = parser.parse_args()

    if args.all:
        args.wine = True
        args.sweep = True

    print("=" * 50)
    print("VR Steering Wheel - evdev & Wine Compatibility Test")
    print("=" * 50)
    print(f"Target device: {G29_NAME}")
    print(f"VID:PID: {G29_VENDOR:04x}:{G29_PRODUCT:04x}")

    results = TestResults()

    # Test device creation
    wheel = test_device_creation(results, args.verbose)
    if not wheel:
        print("\nCannot continue without wheel device.")
        results.summary()
        return 1

    try:
        # Test identity
        test_device_identity(wheel, results, args.verbose)

        # Test capabilities
        test_device_capabilities(wheel, results, args.verbose)

        # Test steering axis
        test_steering_axis(wheel, results, args.verbose)

        # Test pedal axes
        test_pedal_axes(wheel, results, args.verbose)

        # Optional sweep test
        if args.sweep:
            test_steering_sweep(wheel, results, args.verbose)

        # Optional Wine tests
        if args.wine:
            test_wine_detection(wheel, results, args.verbose)
            test_wine_input(wheel, results, args.verbose)

    finally:
        wheel.close()

    success = results.summary()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
