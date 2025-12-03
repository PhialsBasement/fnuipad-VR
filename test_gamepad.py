#!/usr/bin/env python3
"""
Test utility for the Linux virtual gamepad.
Tests the gamepad without needing VR - useful for debugging.

Usage:
    python test_gamepad.py [--interactive]
"""

import sys
import time
import argparse
import math

from _linuxgamepad import LinuxGamepad


def test_basic():
    """Basic automated test of all inputs"""
    print("Creating virtual gamepad...")
    
    with LinuxGamepad(name="Test Gamepad") as pad:
        print(f"Gamepad created!")
        print()
        print("Check with: evtest /dev/input/event<N>")
        print("Or: cat /proc/bus/input/devices | grep -A5 'Test Gamepad'")
        print()
        
        # Test sticks
        print("Testing left stick...")
        for angle in range(0, 360, 30):
            rad = math.radians(angle)
            x = math.cos(rad)
            y = math.sin(rad)
            pad.set_stick('left', x, y)
            pad.sync()
            time.sleep(0.05)
        pad.set_stick('left', 0, 0)
        pad.sync()
        print("  Done")
        
        print("Testing right stick...")
        for angle in range(0, 360, 30):
            rad = math.radians(angle)
            x = math.cos(rad)
            y = math.sin(rad)
            pad.set_stick('right', x, y)
            pad.sync()
            time.sleep(0.05)
        pad.set_stick('right', 0, 0)
        pad.sync()
        print("  Done")
        
        # Test triggers
        print("Testing triggers...")
        for v in [0.25, 0.5, 0.75, 1.0, 0.5, 0.0]:
            pad.set_trigger('left', v)
            pad.set_trigger('right', v)
            pad.sync()
            time.sleep(0.1)
        print("  Done")
        
        # Test d-pad
        print("Testing D-pad...")
        for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0), (0, 0)]:
            pad.set_dpad(dx, dy)
            pad.sync()
            time.sleep(0.2)
        print("  Done")
        
        # Test buttons
        print("Testing buttons...")
        buttons = ['a', 'b', 'x', 'y', 'lb', 'rb', 'ls', 'rs', 'start', 'select', 'guide']
        for btn in buttons:
            pad.press(btn)
            pad.sync()
            time.sleep(0.1)
            pad.release(btn)
            pad.sync()
            time.sleep(0.05)
        print("  Done")
        
        # Test directional stick clicks
        print("Testing directional stick clicks...")
        for side in ['ls', 'rs']:
            for dir in ['up', 'down', 'left', 'right']:
                btn = f'{side}_{dir}'
                pad.press(btn)
                pad.sync()
                time.sleep(0.1)
                pad.release(btn)
                pad.sync()
                time.sleep(0.05)
        print("  Done")
        
        # Test back buttons
        print("Testing back buttons...")
        for btn in ['back_lu', 'back_ll', 'back_ru', 'back_rl']:
            pad.press(btn)
            pad.sync()
            time.sleep(0.1)
            pad.release(btn)
            pad.sync()
            time.sleep(0.05)
        print("  Done")
        
        print()
        print("All tests complete!")


def test_interactive():
    """Interactive test mode with keyboard input"""
    print("Creating virtual gamepad...")
    
    with LinuxGamepad(name="Test Gamepad") as pad:
        print("Gamepad created!")
        print()
        print("Interactive mode - press keys to test:")
        print("  WASD - Left stick")
        print("  Arrow keys - Right stick") 
        print("  1234 - Face buttons (A/B/X/Y)")
        print("  QE - Bumpers (LB/RB)")
        print("  ZC - Triggers (LT/RT)")
        print("  Space - A button tap")
        print("  Enter - Start")
        print("  Tab - Select")
        print("  Esc or Ctrl+C - Exit")
        print()
        
        try:
            import termios
            import tty
            import select
            
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin.fileno())
            
            # Track held keys for sticks
            held = set()
            
            while True:
                # Check for input with timeout
                if select.select([sys.stdin], [], [], 0.016)[0]:
                    ch = sys.stdin.read(1)
                    
                    if ch == '\x1b':  # Escape sequences
                        if select.select([sys.stdin], [], [], 0.01)[0]:
                            seq = sys.stdin.read(2)
                            if seq == '[A':  # Up arrow
                                held.add('r_up')
                            elif seq == '[B':  # Down arrow
                                held.add('r_down')
                            elif seq == '[C':  # Right arrow
                                held.add('r_right')
                            elif seq == '[D':  # Left arrow
                                held.add('r_left')
                        else:
                            # Just Escape
                            break
                    elif ch == '\x03':  # Ctrl+C
                        break
                    elif ch.lower() == 'w':
                        held.add('l_up')
                    elif ch.lower() == 's':
                        held.add('l_down')
                    elif ch.lower() == 'a':
                        held.add('l_left')
                    elif ch.lower() == 'd':
                        held.add('l_right')
                    elif ch == '1':
                        pad.press('a')
                    elif ch == '2':
                        pad.press('b')
                    elif ch == '3':
                        pad.press('x')
                    elif ch == '4':
                        pad.press('y')
                    elif ch.lower() == 'q':
                        pad.press('lb')
                    elif ch.lower() == 'e':
                        pad.press('rb')
                    elif ch.lower() == 'z':
                        pad.set_trigger('left', 1.0)
                    elif ch.lower() == 'c':
                        pad.set_trigger('right', 1.0)
                    elif ch == ' ':
                        pad.press('a')
                    elif ch == '\r':  # Enter
                        pad.press('start')
                    elif ch == '\t':  # Tab
                        pad.press('select')
                else:
                    # Release single-press buttons
                    pad.release('a')
                    pad.release('b')
                    pad.release('x')
                    pad.release('y')
                    pad.release('lb')
                    pad.release('rb')
                    pad.release('start')
                    pad.release('select')
                    pad.set_trigger('left', 0)
                    pad.set_trigger('right', 0)
                    held.clear()
                
                # Update sticks based on held keys
                lx = (1 if 'l_right' in held else 0) - (1 if 'l_left' in held else 0)
                ly = (1 if 'l_down' in held else 0) - (1 if 'l_up' in held else 0)
                rx = (1 if 'r_right' in held else 0) - (1 if 'r_left' in held else 0)
                ry = (1 if 'r_down' in held else 0) - (1 if 'r_up' in held else 0)
                
                pad.set_stick('left', lx, ly)
                pad.set_stick('right', rx, ry)
                pad.sync()
        
        except ImportError:
            print("Interactive mode requires a Unix terminal")
            return
        
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            print("\nExiting...")


def main():
    parser = argparse.ArgumentParser(description="Test the virtual gamepad")
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Interactive test mode with keyboard'
    )
    
    args = parser.parse_args()
    
    try:
        if args.interactive:
            test_interactive()
        else:
            test_basic()
    except PermissionError:
        print("Error: Permission denied accessing /dev/uinput")
        print()
        print("Run these commands to fix:")
        print("  sudo modprobe uinput")
        print("  sudo usermod -aG input $USER")
        print("  # Then log out and back in")
        print()
        print("Or create a udev rule:")
        print('  echo \'KERNEL=="uinput", GROUP="input", MODE="0660"\' | \\')
        print('    sudo tee /etc/udev/rules.d/99-uinput.rules')
        print("  sudo udevadm control --reload-rules")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
