"""
Flexible input mapping system with chord support
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum, auto
import json


class InputType(Enum):
    BUTTON = "button"
    AXIS = "axis"
    TRIGGER = "trigger"


class ConditionType(Enum):
    BUTTON_HELD = "button_held"
    BUTTON_NOT_HELD = "button_not_held"
    AXIS_ABOVE = "axis_above"
    AXIS_BELOW = "axis_below"


# All available Quest/VR controller inputs
VR_INPUTS = {
    "left": {
        "buttons": [
            "trigger_click", "trigger_touch",
            "grip_click", "grip_touch",
            "trackpad_click", "trackpad_touch",
            "menu", "system",
            "thumbstick_click", "thumbstick_touch",
            "x_button", "y_button",  # Quest specific
            "x_touch", "y_touch",
        ],
        "axes": [
            "trigger", "grip",
            "trackpad_x", "trackpad_y",
            "thumbstick_x", "thumbstick_y",
        ],
    },
    "right": {
        "buttons": [
            "trigger_click", "trigger_touch",
            "grip_click", "grip_touch",
            "trackpad_click", "trackpad_touch",
            "menu", "system",
            "thumbstick_click", "thumbstick_touch",
            "a_button", "b_button",  # Quest specific
            "a_touch", "b_touch",
        ],
        "axes": [
            "trigger", "grip",
            "trackpad_x", "trackpad_y",
            "thumbstick_x", "thumbstick_y",
        ],
    },
}

# All available gamepad outputs
GAMEPAD_OUTPUTS = {
    "buttons": [
        "a", "b", "x", "y",
        "lb", "rb",
        "ls", "rs",
        "start", "select", "guide",
        "dpad_up", "dpad_down", "dpad_left", "dpad_right",
        "ls_up", "ls_down", "ls_left", "ls_right",
        "rs_up", "rs_down", "rs_left", "rs_right",
        "back_lu", "back_ll", "back_ru", "back_rl",
        # Generic numbered buttons for flexibility
        *[f"btn_{i}" for i in range(1, 33)],
    ],
    "axes": [
        "left_stick_x", "left_stick_y",
        "right_stick_x", "right_stick_y",
        "left_trigger", "right_trigger",
        "dpad_x", "dpad_y",
        # Generic numbered axes
        *[f"axis_{i}" for i in range(1, 9)],
    ],
}


@dataclass
class Condition:
    """A condition that must be met for a mapping to activate"""
    type: ConditionType
    controller: str  # "left" or "right"
    input_name: str
    value: float = 0.5  # threshold for axis conditions
    
    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "controller": self.controller,
            "input": self.input_name,
            "value": self.value,
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "Condition":
        return cls(
            type=ConditionType(d["type"]),
            controller=d["controller"],
            input_name=d["input"],
            value=d.get("value", 0.5),
        )


@dataclass
class Mapping:
    """A single input-to-output mapping"""
    # Input
    input_type: InputType
    input_controller: str  # "left" or "right"
    input_name: str
    
    # Output
    output_type: InputType
    output_name: str
    
    # Conditions (for chords)
    conditions: List[Condition] = field(default_factory=list)
    
    # Modifiers
    invert: bool = False
    sensitivity: float = 1.0
    deadzone: float = 0.0
    
    # Priority (higher = checked first, for chord precedence)
    priority: int = 0
    
    # Whether this mapping is enabled
    enabled: bool = True
    
    # Optional name for display
    name: str = ""
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "input": {
                "type": self.input_type.value,
                "controller": self.input_controller,
                "name": self.input_name,
            },
            "output": {
                "type": self.output_type.value,
                "name": self.output_name,
            },
            "conditions": [c.to_dict() for c in self.conditions],
            "modifiers": {
                "invert": self.invert,
                "sensitivity": self.sensitivity,
                "deadzone": self.deadzone,
            },
            "priority": self.priority,
            "enabled": self.enabled,
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "Mapping":
        return cls(
            name=d.get("name", ""),
            input_type=InputType(d["input"]["type"]),
            input_controller=d["input"]["controller"],
            input_name=d["input"]["name"],
            output_type=InputType(d["output"]["type"]),
            output_name=d["output"]["name"],
            conditions=[Condition.from_dict(c) for c in d.get("conditions", [])],
            invert=d.get("modifiers", {}).get("invert", False),
            sensitivity=d.get("modifiers", {}).get("sensitivity", 1.0),
            deadzone=d.get("modifiers", {}).get("deadzone", 0.0),
            priority=d.get("priority", 0),
            enabled=d.get("enabled", True),
        )


@dataclass
class MappingProfile:
    """A complete mapping configuration"""
    name: str = "Default"
    mappings: List[Mapping] = field(default_factory=list)

    # Global settings
    global_deadzone: float = 0.1
    haptic_intensity: float = 0.5

    # Device identity settings
    device_name: str = "vJoy Device"
    device_vendor: Optional[int] = None   # None = use default (0x1234)
    device_product: Optional[int] = None  # None = use default (0xBEAD)

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "mappings": [m.to_dict() for m in self.mappings],
            "settings": {
                "global_deadzone": self.global_deadzone,
                "haptic_intensity": self.haptic_intensity,
            },
        }
        # Only include device settings if non-default
        if self.device_name != "vJoy Device" or self.device_vendor or self.device_product:
            d["device"] = {
                "name": self.device_name,
            }
            if self.device_vendor is not None:
                d["device"]["vendor"] = self.device_vendor
            if self.device_product is not None:
                d["device"]["product"] = self.device_product
        return d
    
    @classmethod
    def from_dict(cls, d: dict) -> "MappingProfile":
        profile = cls(
            name=d.get("name", "Default"),
            mappings=[Mapping.from_dict(m) for m in d.get("mappings", [])],
        )
        settings = d.get("settings", {})
        profile.global_deadzone = settings.get("global_deadzone", 0.1)
        profile.haptic_intensity = settings.get("haptic_intensity", 0.5)

        device = d.get("device", {})
        profile.device_name = device.get("name", "vJoy Device")
        profile.device_vendor = device.get("vendor")
        profile.device_product = device.get("product")
        return profile
    
    def save(self, path: str):
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: str) -> "MappingProfile":
        with open(path) as f:
            return cls.from_dict(json.load(f))
    
    def add_mapping(self, mapping: Mapping):
        self.mappings.append(mapping)
        self._sort_mappings()
    
    def remove_mapping(self, index: int):
        if 0 <= index < len(self.mappings):
            self.mappings.pop(index)
    
    def _sort_mappings(self):
        """Sort by priority (highest first) and chord count (more conditions first)"""
        self.mappings.sort(key=lambda m: (-m.priority, -len(m.conditions)))


def create_default_profile() -> MappingProfile:
    """Create a sensible default mapping profile"""
    profile = MappingProfile(name="Default")
    
    # Left stick from left thumbstick
    profile.add_mapping(Mapping(
        name="Left Stick X",
        input_type=InputType.AXIS,
        input_controller="left",
        input_name="thumbstick_x",
        output_type=InputType.AXIS,
        output_name="left_stick_x",
    ))
    profile.add_mapping(Mapping(
        name="Left Stick Y",
        input_type=InputType.AXIS,
        input_controller="left",
        input_name="thumbstick_y",
        output_type=InputType.AXIS,
        output_name="left_stick_y",
        invert=True,
    ))
    
    # Right stick from right thumbstick
    profile.add_mapping(Mapping(
        name="Right Stick X",
        input_type=InputType.AXIS,
        input_controller="right",
        input_name="thumbstick_x",
        output_type=InputType.AXIS,
        output_name="right_stick_x",
    ))
    profile.add_mapping(Mapping(
        name="Right Stick Y",
        input_type=InputType.AXIS,
        input_controller="right",
        input_name="thumbstick_y",
        output_type=InputType.AXIS,
        output_name="right_stick_y",
        invert=True,
    ))
    
    # Triggers
    profile.add_mapping(Mapping(
        name="Left Trigger",
        input_type=InputType.AXIS,
        input_controller="left",
        input_name="trigger",
        output_type=InputType.AXIS,
        output_name="left_trigger",
    ))
    profile.add_mapping(Mapping(
        name="Right Trigger",
        input_type=InputType.AXIS,
        input_controller="right",
        input_name="trigger",
        output_type=InputType.AXIS,
        output_name="right_trigger",
    ))
    
    # Grips as bumpers
    profile.add_mapping(Mapping(
        name="Left Bumper",
        input_type=InputType.BUTTON,
        input_controller="left",
        input_name="grip_click",
        output_type=InputType.BUTTON,
        output_name="lb",
    ))
    profile.add_mapping(Mapping(
        name="Right Bumper",
        input_type=InputType.BUTTON,
        input_controller="right",
        input_name="grip_click",
        output_type=InputType.BUTTON,
        output_name="rb",
    ))
    
    # Face buttons (Quest A/B/X/Y)
    profile.add_mapping(Mapping(
        name="A Button",
        input_type=InputType.BUTTON,
        input_controller="right",
        input_name="a_button",
        output_type=InputType.BUTTON,
        output_name="a",
    ))
    profile.add_mapping(Mapping(
        name="B Button",
        input_type=InputType.BUTTON,
        input_controller="right",
        input_name="b_button",
        output_type=InputType.BUTTON,
        output_name="b",
    ))
    profile.add_mapping(Mapping(
        name="X Button",
        input_type=InputType.BUTTON,
        input_controller="left",
        input_name="x_button",
        output_type=InputType.BUTTON,
        output_name="x",
    ))
    profile.add_mapping(Mapping(
        name="Y Button",
        input_type=InputType.BUTTON,
        input_controller="left",
        input_name="y_button",
        output_type=InputType.BUTTON,
        output_name="y",
    ))
    
    # Stick clicks
    profile.add_mapping(Mapping(
        name="Left Stick Click",
        input_type=InputType.BUTTON,
        input_controller="left",
        input_name="thumbstick_click",
        output_type=InputType.BUTTON,
        output_name="ls",
    ))
    profile.add_mapping(Mapping(
        name="Right Stick Click",
        input_type=InputType.BUTTON,
        input_controller="right",
        input_name="thumbstick_click",
        output_type=InputType.BUTTON,
        output_name="rs",
    ))
    
    # Menu buttons
    profile.add_mapping(Mapping(
        name="Start",
        input_type=InputType.BUTTON,
        input_controller="right",
        input_name="menu",
        output_type=InputType.BUTTON,
        output_name="start",
    ))
    profile.add_mapping(Mapping(
        name="Select",
        input_type=InputType.BUTTON,
        input_controller="left",
        input_name="menu",
        output_type=InputType.BUTTON,
        output_name="select",
    ))
    
    # Example chord: Grip + Trigger = Guide button
    profile.add_mapping(Mapping(
        name="Guide (Chord)",
        input_type=InputType.BUTTON,
        input_controller="right",
        input_name="trigger_click",
        output_type=InputType.BUTTON,
        output_name="guide",
        conditions=[
            Condition(
                type=ConditionType.BUTTON_HELD,
                controller="right",
                input_name="grip_click",
            ),
        ],
        priority=10,  # Higher priority than normal trigger
    ))
    
    return profile
