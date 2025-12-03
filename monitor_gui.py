#!/usr/bin/env python3
"""
Gamepad Monitor - Raw visualization of virtual gamepad state
Shows all 32 buttons and 8 axes
"""

import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass, field
from typing import Dict, Optional
import threading


@dataclass
class GamepadState:
    """Raw gamepad state"""
    axes: Dict[int, float] = field(default_factory=dict)  # axis_num -> value
    buttons: Dict[int, bool] = field(default_factory=dict)  # button_num -> pressed

    def copy(self):
        return GamepadState(
            axes=dict(self.axes),
            buttons=dict(self.buttons),
        )


class AxisBar(tk.Canvas):
    """Single axis visualization"""

    def __init__(self, parent, axis_num: int, **kwargs):
        super().__init__(parent, width=200, height=24,
                        bg='#2b2b2b', highlightthickness=0, **kwargs)
        self.axis_num = axis_num
        self.value = 0.0
        self.is_trigger = axis_num in (3, 6)  # LT, RT are 0-1 range
        self._draw()

    def _draw(self):
        self.delete("all")

        # Label
        self.create_text(25, 12, text=f"Axis {self.axis_num}",
                        fill='#aaaaaa', font=('Mono', 9), anchor='e')

        bar_x = 35
        bar_width = 130
        bar_height = 16

        # Background
        self.create_rectangle(
            bar_x, 4, bar_x + bar_width, 4 + bar_height,
            fill='#333333', outline='#555555'
        )

        if self.is_trigger:
            # 0 to 1 range (left-aligned fill)
            fill_width = int(self.value * bar_width)
            if fill_width > 0:
                self.create_rectangle(
                    bar_x + 1, 5,
                    bar_x + fill_width, 3 + bar_height,
                    fill='#00aa00', outline=''
                )
        else:
            # -1 to 1 range (center-aligned fill)
            center = bar_x + bar_width // 2
            self.create_line(center, 4, center, 4 + bar_height, fill='#555555')

            fill_width = int(self.value * (bar_width // 2))
            if fill_width != 0:
                x1 = center
                x2 = center + fill_width
                if x2 < x1:
                    x1, x2 = x2, x1
                self.create_rectangle(
                    x1, 5, x2, 3 + bar_height,
                    fill='#00aa00', outline=''
                )

        # Value text
        self.create_text(bar_x + bar_width + 5, 12,
                        text=f"{self.value:+.3f}",
                        fill='#888888', font=('Mono', 8), anchor='w')

    def set_value(self, value: float):
        if value != self.value:
            self.value = value
            self._draw()


class ButtonGrid(tk.Frame):
    """Grid of button indicators"""

    def __init__(self, parent, num_buttons: int = 32, **kwargs):
        super().__init__(parent, bg='#1e1e1e', **kwargs)
        self.num_buttons = num_buttons
        self.buttons = {}
        self._build()

    def _build(self):
        cols = 8
        rows = (self.num_buttons + cols - 1) // cols

        for i in range(self.num_buttons):
            row = i // cols
            col = i % cols
            btn_num = i + 1

            btn = tk.Canvas(self, width=36, height=36,
                           bg='#2b2b2b', highlightthickness=0)
            btn.grid(row=row, column=col, padx=2, pady=2)

            self.buttons[btn_num] = {
                'canvas': btn,
                'pressed': False
            }
            self._draw_button(btn_num)

    def _draw_button(self, btn_num: int):
        btn = self.buttons[btn_num]
        canvas = btn['canvas']
        pressed = btn['pressed']

        canvas.delete("all")

        fill = '#00aa00' if pressed else '#444444'
        outline = '#88ff88' if pressed else '#666666'
        text_color = '#ffffff' if pressed else '#888888'

        canvas.create_rectangle(
            4, 4, 32, 32,
            fill=fill, outline=outline, width=2
        )
        canvas.create_text(18, 18, text=str(btn_num),
                          fill=text_color, font=('Mono', 9, 'bold'))

    def set_button(self, btn_num: int, pressed: bool):
        if btn_num in self.buttons:
            if self.buttons[btn_num]['pressed'] != pressed:
                self.buttons[btn_num]['pressed'] = pressed
                self._draw_button(btn_num)


class GamepadMonitor(tk.Tk):
    """Main monitor window"""

    def __init__(self):
        super().__init__()

        self.title("Gamepad Monitor")
        self.configure(bg='#1e1e1e')
        self.resizable(False, False)

        self.state = GamepadState()
        self._running = True
        self.evdev_device = None

        self._build_ui()
        self._find_device()
        self._start_reader()
        self._update_loop()

    def _build_ui(self):
        # Title
        title = tk.Label(self, text="Virtual Gamepad Monitor",
                        font=('Arial', 12, 'bold'),
                        fg='#ffffff', bg='#1e1e1e')
        title.pack(pady=(10, 5))

        # Main container
        main = tk.Frame(self, bg='#1e1e1e')
        main.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # Axes section
        axes_frame = tk.LabelFrame(main, text="Axes", bg='#1e1e1e', fg='#aaaaaa',
                                   font=('Arial', 10))
        axes_frame.pack(fill=tk.X, pady=(0, 10))

        self.axis_bars = {}
        for i in range(1, 9):
            bar = AxisBar(axes_frame, i)
            bar.pack(pady=1, padx=5)
            self.axis_bars[i] = bar

        # Buttons section
        buttons_frame = tk.LabelFrame(main, text="Buttons", bg='#1e1e1e', fg='#aaaaaa',
                                      font=('Arial', 10))
        buttons_frame.pack(fill=tk.X)

        self.button_grid = ButtonGrid(buttons_frame, num_buttons=32)
        self.button_grid.pack(pady=5, padx=5)

        # Status bar
        self.status_var = tk.StringVar(value="Looking for device...")
        status = tk.Label(self, textvariable=self.status_var,
                         fg='#666666', bg='#1e1e1e',
                         font=('Mono', 9))
        status.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

    def _find_device(self):
        """Find the virtual gamepad device"""
        try:
            from evdev import list_devices, InputDevice

            for path in list_devices():
                dev = InputDevice(path)
                # Match vJoy Device or legacy VR Gamepad names
                if "vJoy" in dev.name or "VR Gamepad" in dev.name:
                    self.evdev_device = dev
                    self.status_var.set(f"Connected: {dev.name} ({dev.path})")
                    return

            self.status_var.set("Device not found - create gamepad first")
        except ImportError:
            self.status_var.set("evdev not installed")
        except Exception as e:
            self.status_var.set(f"Error: {e}")

    def _start_reader(self):
        """Start background thread to read events"""
        if self.evdev_device:
            thread = threading.Thread(target=self._read_events, daemon=True)
            thread.start()

    def _read_events(self):
        """Read events from the device"""
        from evdev import ecodes as e

        # Map evdev axis codes to our axis numbers
        axis_map = {
            e.ABS_X: 1,      # Left stick X
            e.ABS_Y: 2,      # Left stick Y
            e.ABS_Z: 3,      # Left trigger
            e.ABS_RX: 4,     # Right stick X
            e.ABS_RY: 5,     # Right stick Y
            e.ABS_RZ: 6,     # Right trigger
            e.ABS_HAT0X: 7,  # D-pad X
            e.ABS_HAT0Y: 8,  # D-pad Y
        }

        # Map evdev button codes to our button numbers
        button_map = {
            e.BTN_A: 1,
            e.BTN_B: 2,
            e.BTN_X: 3,
            e.BTN_Y: 4,
            e.BTN_TL: 5,     # LB
            e.BTN_TR: 6,     # RB
            e.BTN_THUMBL: 7, # LS
            e.BTN_THUMBR: 8, # RS
            e.BTN_START: 9,
            e.BTN_SELECT: 10,
            e.BTN_MODE: 11,  # Guide
            e.BTN_DPAD_UP: 12,
            e.BTN_DPAD_DOWN: 13,
            e.BTN_DPAD_LEFT: 14,
            e.BTN_DPAD_RIGHT: 15,
        }
        # Add TRIGGER_HAPPY buttons (16-47 map to our 16-32+)
        for i in range(32):
            button_map[e.BTN_TRIGGER_HAPPY1 + i] = 16 + i

        try:
            for event in self.evdev_device.read_loop():
                if not self._running:
                    break

                if event.type == e.EV_ABS:
                    axis_num = axis_map.get(event.code)
                    if axis_num:
                        # Normalize value
                        if axis_num in (3, 6):  # Triggers 0-255
                            value = event.value / 255.0
                        elif axis_num in (7, 8):  # D-pad -1 to 1
                            value = float(event.value)
                        else:  # Sticks -32768 to 32767
                            value = event.value / 32767.0
                        self.state.axes[axis_num] = value

                elif event.type == e.EV_KEY:
                    btn_num = button_map.get(event.code)
                    if btn_num and btn_num <= 32:
                        self.state.buttons[btn_num] = event.value == 1

        except Exception as ex:
            self.status_var.set(f"Read error: {ex}")

    def _update_loop(self):
        """Update display from state"""
        if not self._running:
            return

        # Update axes
        for axis_num, bar in self.axis_bars.items():
            bar.set_value(self.state.axes.get(axis_num, 0.0))

        # Update buttons
        for btn_num in range(1, 33):
            self.button_grid.set_button(btn_num, self.state.buttons.get(btn_num, False))

        self.after(16, self._update_loop)

    def on_closing(self):
        self._running = False
        self.destroy()

    def run(self):
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.mainloop()


def main():
    monitor = GamepadMonitor()
    monitor.run()


if __name__ == "__main__":
    main()
