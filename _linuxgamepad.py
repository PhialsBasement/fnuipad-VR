"""
Linux Virtual Gamepad using evdev/uinput
Generic joystick device with 32 buttons and 8 axes
"""

from evdev import UInput, AbsInfo, ecodes as e


# Default device identity (generic joystick)
DEFAULT_VENDOR = 0x1234   # Generic
DEFAULT_PRODUCT = 0xBEAD  # vJoy-like
DEFAULT_VERSION = 0x0001

# Xbox 360 identity (for compatibility mode)
XBOX360_VENDOR = 0x045e   # Microsoft
XBOX360_PRODUCT = 0x028e  # Xbox 360 Controller
XBOX360_VERSION = 0x0110


class LinuxGamepad:
    """
    Virtual joystick device.

    By default presents as a generic joystick with 32 buttons and 8 axes.
    Games will query the device for its actual capabilities rather than
    assuming a preset layout.

    Axes (8 total):
        - Axis 1-2: Left stick (ABS_X, ABS_Y)
        - Axis 3: Left trigger (ABS_Z)
        - Axis 4-5: Right stick (ABS_RX, ABS_RY)
        - Axis 6: Right trigger (ABS_RZ)
        - Axis 7-8: HAT/D-pad (ABS_HAT0X, ABS_HAT0Y)

    Buttons (32 total):
        - Standard gamepad buttons mapped to BTN_TRIGGER_HAPPY1-32
        - Named aliases available (a, b, x, y, etc.)
    """

    AXIS_MIN = -32768
    AXIS_MAX = 32767
    AXIS_CENTER = 0
    TRIGGER_MIN = 0
    TRIGGER_MAX = 255

    def __init__(self, name="vJoy Device", device_id=1,
                 vendor=None, product=None, version=None):
        # Stick axes (signed, centered at 0)
        stick_info = AbsInfo(
            value=0,
            min=self.AXIS_MIN,
            max=self.AXIS_MAX,
            fuzz=16,
            flat=128,
            resolution=0
        )
        
        # Trigger axes (unsigned, 0 to 255)
        trigger_info = AbsInfo(
            value=0,
            min=self.TRIGGER_MIN,
            max=self.TRIGGER_MAX,
            fuzz=0,
            flat=0,
            resolution=0
        )
        
        # D-pad as hat (discrete -1, 0, 1)
        hat_info = AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0)
        
        capabilities = {
            e.EV_ABS: [
                # Left stick
                (e.ABS_X, stick_info),
                (e.ABS_Y, stick_info),
                # Right stick
                (e.ABS_RX, stick_info),
                (e.ABS_RY, stick_info),
                # Triggers
                (e.ABS_Z, trigger_info),   # Left trigger
                (e.ABS_RZ, trigger_info),  # Right trigger
                # D-pad hat
                (e.ABS_HAT0X, hat_info),
                (e.ABS_HAT0Y, hat_info),
            ],
            e.EV_KEY: [
                # Face buttons
                e.BTN_A,      # A / Cross
                e.BTN_B,      # B / Circle  
                e.BTN_X,      # X / Square
                e.BTN_Y,      # Y / Triangle
                # Bumpers
                e.BTN_TL,     # Left bumper (LB)
                e.BTN_TR,     # Right bumper (RB)
                # Stick clicks
                e.BTN_THUMBL, # Left stick click (L3)
                e.BTN_THUMBR, # Right stick click (R3)
                # Menu buttons
                e.BTN_START,  # Start / Options
                e.BTN_SELECT, # Select / Share / Back
                e.BTN_MODE,   # Guide / Home / PS button
                # D-pad buttons
                e.BTN_DPAD_UP,
                e.BTN_DPAD_DOWN,
                e.BTN_DPAD_LEFT,
                e.BTN_DPAD_RIGHT,
                # Extra buttons (TRIGGER_HAPPY range for custom mappings)
                *[e.BTN_TRIGGER_HAPPY1 + i for i in range(40)],
            ],
            e.EV_FF: [e.FF_RUMBLE],  # Force feedback support
        }
        
        self._ui = UInput(
            capabilities,
            name=f"{name} {device_id}",
            vendor=vendor if vendor is not None else DEFAULT_VENDOR,
            product=product if product is not None else DEFAULT_PRODUCT,
            version=version if version is not None else DEFAULT_VERSION,
        )
        
        self._pending = False
        
        # Button code mappings for easy access
        self.BTN = {
            'a': e.BTN_A,
            'b': e.BTN_B,
            'x': e.BTN_X,
            'y': e.BTN_Y,
            'lb': e.BTN_TL,
            'rb': e.BTN_TR,
            'ls': e.BTN_THUMBL,
            'rs': e.BTN_THUMBR,
            'start': e.BTN_START,
            'select': e.BTN_SELECT,
            'guide': e.BTN_MODE,
            # D-pad as buttons (alternative to hat)
            'dpad_up': e.BTN_DPAD_UP,
            'dpad_down': e.BTN_DPAD_DOWN,
            'dpad_left': e.BTN_DPAD_LEFT,
            'dpad_right': e.BTN_DPAD_RIGHT,
            # Directional stick clicks
            'ls_up': e.BTN_TRIGGER_HAPPY1,
            'ls_down': e.BTN_TRIGGER_HAPPY2,
            'ls_left': e.BTN_TRIGGER_HAPPY3,
            'ls_right': e.BTN_TRIGGER_HAPPY4,
            'rs_up': e.BTN_TRIGGER_HAPPY5,
            'rs_down': e.BTN_TRIGGER_HAPPY6,
            'rs_left': e.BTN_TRIGGER_HAPPY7,
            'rs_right': e.BTN_TRIGGER_HAPPY8,
            # Back paddles
            'back_lu': e.BTN_TRIGGER_HAPPY9,
            'back_ll': e.BTN_TRIGGER_HAPPY10,
            'back_ru': e.BTN_TRIGGER_HAPPY11,
            'back_rl': e.BTN_TRIGGER_HAPPY12,
            # Generic numbered buttons (btn_1 through btn_32)
            **{f'btn_{i}': e.BTN_TRIGGER_HAPPY1 + i - 1 for i in range(1, 33)},
        }
        
        self.AXIS = {
            'lx': e.ABS_X,
            'ly': e.ABS_Y,
            'rx': e.ABS_RX,
            'ry': e.ABS_RY,
            'lt': e.ABS_Z,
            'rt': e.ABS_RZ,
            'hat_x': e.ABS_HAT0X,
            'hat_y': e.ABS_HAT0Y,
            # Named aliases for mapping system
            'left_stick_x': e.ABS_X,
            'left_stick_y': e.ABS_Y,
            'right_stick_x': e.ABS_RX,
            'right_stick_y': e.ABS_RY,
            'left_trigger': e.ABS_Z,
            'right_trigger': e.ABS_RZ,
            'dpad_x': e.ABS_HAT0X,
            'dpad_y': e.ABS_HAT0Y,
            # Generic numbered axes
            'axis_1': e.ABS_X,
            'axis_2': e.ABS_Y,
            'axis_3': e.ABS_Z,
            'axis_4': e.ABS_RX,
            'axis_5': e.ABS_RY,
            'axis_6': e.ABS_RZ,
            'axis_7': e.ABS_HAT0X,
            'axis_8': e.ABS_HAT0Y,
        }
    
    def set_stick(self, stick, x, y):
        """
        Set stick position.
        
        Args:
            stick: 'left' or 'right'
            x: -1.0 to 1.0 (left to right)
            y: -1.0 to 1.0 (up to down, inverted from typical)
        """
        ix = int(x * self.AXIS_MAX)
        iy = int(y * self.AXIS_MAX)
        
        ix = max(self.AXIS_MIN, min(self.AXIS_MAX, ix))
        iy = max(self.AXIS_MIN, min(self.AXIS_MAX, iy))
        
        if stick == 'left':
            self._ui.write(e.EV_ABS, e.ABS_X, ix)
            self._ui.write(e.EV_ABS, e.ABS_Y, iy)
        else:
            self._ui.write(e.EV_ABS, e.ABS_RX, ix)
            self._ui.write(e.EV_ABS, e.ABS_RY, iy)
        
        self._pending = True
    
    def set_trigger(self, trigger, value):
        """
        Set trigger value.
        
        Args:
            trigger: 'left' or 'right'
            value: 0.0 to 1.0
        """
        iv = int(value * self.TRIGGER_MAX)
        iv = max(self.TRIGGER_MIN, min(self.TRIGGER_MAX, iv))
        
        axis = e.ABS_Z if trigger == 'left' else e.ABS_RZ
        self._ui.write(e.EV_ABS, axis, iv)
        self._pending = True
    
    def set_dpad(self, x, y):
        """
        Set D-pad state.
        
        Args:
            x: -1 (left), 0 (center), 1 (right)
            y: -1 (up), 0 (center), 1 (down)
        """
        self._ui.write(e.EV_ABS, e.ABS_HAT0X, x)
        self._ui.write(e.EV_ABS, e.ABS_HAT0Y, y)
        self._pending = True
    
    def set_button(self, button, pressed):
        """
        Set button state.
        
        Args:
            button: button name (see self.BTN) or evdev code
            pressed: True/False
        """
        if isinstance(button, str):
            code = self.BTN.get(button)
            if code is None:
                return
        else:
            code = button
        
        self._ui.write(e.EV_KEY, code, 1 if pressed else 0)
        self._pending = True
    
    def press(self, button):
        """Press a button"""
        self.set_button(button, True)
    
    def release(self, button):
        """Release a button"""
        self.set_button(button, False)
    
    def sync(self):
        """Flush all pending events"""
        if self._pending:
            self._ui.syn()
            self._pending = False
    
    def reset(self):
        """Reset all inputs to neutral"""
        self.set_stick('left', 0, 0)
        self.set_stick('right', 0, 0)
        self.set_trigger('left', 0)
        self.set_trigger('right', 0)
        self.set_dpad(0, 0)
        for btn in self.BTN.values():
            self._ui.write(e.EV_KEY, btn, 0)
        self.sync()
    
    def close(self):
        """Clean up the virtual device"""
        self.reset()
        self._ui.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
