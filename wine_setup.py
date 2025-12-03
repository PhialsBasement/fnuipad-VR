#!/usr/bin/env python3
"""
Wine Configuration for vJoy Device

Configures Wine/Proton to properly detect all 32 buttons and 8 axes
from the virtual joystick device.

By default, Wine uses SDL which limits detection to XInput's 10 buttons.
This script configures winebus to use evdev directly, exposing all buttons.
"""

import subprocess
import argparse
import os


def run_wine_reg(prefix: str, *args):
    """Run wine reg command with optional prefix"""
    env = os.environ.copy()
    if prefix:
        env['WINEPREFIX'] = prefix
    cmd = ['wine', 'reg'] + list(args)
    subprocess.run(cmd, env=env, check=True)


def setup_winebus_evdev(prefix: str = None):
    """
    Configure winebus to use evdev instead of SDL.
    This allows Wine to see all buttons/axes instead of XInput's limited set.
    """
    print("Configuring winebus to use evdev (full button support)...")

    # Disable SDL (which limits to XInput mapping)
    run_wine_reg(prefix, 'add',
        r'HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\winebus',
        '/v', 'Enable SDL', '/t', 'REG_DWORD', '/d', '0', '/f')

    # Disable hidraw (use evdev)
    run_wine_reg(prefix, 'add',
        r'HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\winebus',
        '/v', 'DisableHidraw', '/t', 'REG_DWORD', '/d', '1', '/f')

    print("Done. Wine will now use evdev and see all 32 buttons.")


def setup_winebus_sdl(prefix: str = None):
    """
    Configure winebus to use SDL (default, XInput compatible).
    Limited to ~10 buttons but better game compatibility.
    """
    print("Configuring winebus to use SDL (XInput mode)...")

    run_wine_reg(prefix, 'add',
        r'HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\winebus',
        '/v', 'Enable SDL', '/t', 'REG_DWORD', '/d', '1', '/f')

    run_wine_reg(prefix, 'add',
        r'HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\winebus',
        '/v', 'DisableHidraw', '/t', 'REG_DWORD', '/d', '0', '/f')

    print("Done. Wine will use SDL (XInput mode, ~10 buttons).")


def set_deadzone(prefix: str = None, value: int = 1000):
    """Set global DirectInput deadzone (0-10000)"""
    print(f"Setting DirectInput deadzone to {value}...")

    run_wine_reg(prefix, 'add',
        r'HKEY_CURRENT_USER\Software\Wine\DirectInput',
        '/v', 'DefaultDeadZone', '/t', 'REG_SZ', '/d', str(value), '/f')

    print("Done.")


def show_status(prefix: str = None):
    """Show current winebus configuration"""
    env = os.environ.copy()
    if prefix:
        env['WINEPREFIX'] = prefix

    print("Current winebus configuration:")
    print("-" * 40)

    try:
        result = subprocess.run(
            ['wine', 'reg', 'query',
             r'HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\winebus'],
            env=env, capture_output=True, text=True
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if 'SDL' in line or 'Hidraw' in line:
                    print(line.strip())
        else:
            print("No winebus configuration found (using defaults)")
    except Exception as e:
        print(f"Error: {e}")

    print()
    print("To test joystick detection, run:")
    if prefix:
        print(f"  WINEPREFIX={prefix} wine control joy.cpl")
    else:
        print("  wine control joy.cpl")


def main():
    parser = argparse.ArgumentParser(
        description="Configure Wine for vJoy device",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  evdev   - Use evdev backend (sees all 32 buttons, 8 axes)
  sdl     - Use SDL backend (XInput mode, ~10 buttons, better compat)
  status  - Show current configuration

Examples:
  %(prog)s evdev                    # Enable full button support
  %(prog)s sdl                      # Use XInput mode
  %(prog)s --prefix ~/.steam/steam/steamapps/compatdata/123456/pfx evdev
  %(prog)s status                   # Check current settings
        """
    )

    parser.add_argument('mode', choices=['evdev', 'sdl', 'status'],
                       help='Configuration mode')
    parser.add_argument('--prefix', '-p',
                       help='Wine prefix path (for Proton games)')
    parser.add_argument('--deadzone', '-d', type=int,
                       help='Set DirectInput deadzone (0-10000)')

    args = parser.parse_args()

    if args.mode == 'evdev':
        setup_winebus_evdev(args.prefix)
    elif args.mode == 'sdl':
        setup_winebus_sdl(args.prefix)
    elif args.mode == 'status':
        show_status(args.prefix)

    if args.deadzone is not None:
        set_deadzone(args.prefix, args.deadzone)


if __name__ == '__main__':
    main()
