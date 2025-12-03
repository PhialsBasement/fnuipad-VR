#!/usr/bin/env python3
"""
GUI Configuration Tool for VR Gamepad Mapper
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
from pathlib import Path
from typing import Optional

from _mapping import (
    MappingProfile, Mapping, Condition,
    InputType, ConditionType,
    VR_INPUTS, GAMEPAD_OUTPUTS,
    create_default_profile
)


class MappingDialog(tk.Toplevel):
    """Dialog for creating/editing a mapping"""
    
    def __init__(self, parent, mapping: Optional[Mapping] = None):
        super().__init__(parent)
        self.title("Edit Mapping" if mapping else "New Mapping")
        self.geometry("500x600")
        self.resizable(False, False)
        
        self.result: Optional[Mapping] = None
        self.mapping = mapping
        self.conditions: list[Condition] = list(mapping.conditions) if mapping else []
        
        self._build_ui()
        
        if mapping:
            self._load_mapping(mapping)
        
        self.transient(parent)
        self.grab_set()
    
    def _build_ui(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Name
        ttk.Label(main, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.name_var = tk.StringVar()
        ttk.Entry(main, textvariable=self.name_var, width=40).grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=2)
        
        # Input section
        input_frame = ttk.LabelFrame(main, text="Input (VR Controller)", padding=5)
        input_frame.grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=10)
        
        ttk.Label(input_frame, text="Controller:").grid(row=0, column=0, sticky=tk.W)
        self.input_controller = ttk.Combobox(input_frame, values=["left", "right"], state="readonly", width=15)
        self.input_controller.grid(row=0, column=1, sticky=tk.W, padx=5)
        self.input_controller.set("left")
        self.input_controller.bind("<<ComboboxSelected>>", self._update_input_list)
        
        ttk.Label(input_frame, text="Type:").grid(row=1, column=0, sticky=tk.W)
        self.input_type = ttk.Combobox(input_frame, values=["button", "axis"], state="readonly", width=15)
        self.input_type.grid(row=1, column=1, sticky=tk.W, padx=5)
        self.input_type.set("button")
        self.input_type.bind("<<ComboboxSelected>>", self._update_input_list)
        
        ttk.Label(input_frame, text="Input:").grid(row=2, column=0, sticky=tk.W)
        self.input_name = ttk.Combobox(input_frame, state="readonly", width=25)
        self.input_name.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=5)
        self._update_input_list()
        
        # Output section
        output_frame = ttk.LabelFrame(main, text="Output (Gamepad)", padding=5)
        output_frame.grid(row=2, column=0, columnspan=3, sticky=tk.EW, pady=10)
        
        ttk.Label(output_frame, text="Type:").grid(row=0, column=0, sticky=tk.W)
        self.output_type = ttk.Combobox(output_frame, values=["button", "axis"], state="readonly", width=15)
        self.output_type.grid(row=0, column=1, sticky=tk.W, padx=5)
        self.output_type.set("button")
        self.output_type.bind("<<ComboboxSelected>>", self._update_output_list)
        
        ttk.Label(output_frame, text="Output:").grid(row=1, column=0, sticky=tk.W)
        self.output_name = ttk.Combobox(output_frame, state="readonly", width=25)
        self.output_name.grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=5)
        self._update_output_list()
        
        # Modifiers section
        mod_frame = ttk.LabelFrame(main, text="Modifiers", padding=5)
        mod_frame.grid(row=3, column=0, columnspan=3, sticky=tk.EW, pady=10)
        
        self.invert_var = tk.BooleanVar()
        ttk.Checkbutton(mod_frame, text="Invert", variable=self.invert_var).grid(row=0, column=0, sticky=tk.W)
        
        ttk.Label(mod_frame, text="Sensitivity:").grid(row=0, column=1, sticky=tk.W, padx=(20, 5))
        self.sensitivity_var = tk.StringVar(value="1.0")
        ttk.Entry(mod_frame, textvariable=self.sensitivity_var, width=8).grid(row=0, column=2, sticky=tk.W)
        
        ttk.Label(mod_frame, text="Deadzone:").grid(row=1, column=1, sticky=tk.W, padx=(20, 5))
        self.deadzone_var = tk.StringVar(value="0.0")
        ttk.Entry(mod_frame, textvariable=self.deadzone_var, width=8).grid(row=1, column=2, sticky=tk.W)
        
        ttk.Label(mod_frame, text="Priority:").grid(row=1, column=0, sticky=tk.W)
        self.priority_var = tk.StringVar(value="0")
        ttk.Entry(mod_frame, textvariable=self.priority_var, width=5).grid(row=2, column=0, sticky=tk.W)
        
        # Conditions section (chords)
        cond_frame = ttk.LabelFrame(main, text="Conditions (Chords)", padding=5)
        cond_frame.grid(row=4, column=0, columnspan=3, sticky=tk.EW, pady=10)
        
        self.conditions_list = tk.Listbox(cond_frame, height=4, width=50)
        self.conditions_list.grid(row=0, column=0, columnspan=3, sticky=tk.EW)
        
        ttk.Button(cond_frame, text="Add Condition", command=self._add_condition).grid(row=1, column=0, pady=5)
        ttk.Button(cond_frame, text="Remove", command=self._remove_condition).grid(row=1, column=1, pady=5)
        
        self._refresh_conditions_list()
        
        # Buttons
        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=5, column=0, columnspan=3, pady=20)
        
        ttk.Button(btn_frame, text="OK", command=self._ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)
    
    def _update_input_list(self, event=None):
        controller = self.input_controller.get()
        itype = self.input_type.get()
        
        if itype == "button":
            values = VR_INPUTS[controller]["buttons"]
        else:
            values = VR_INPUTS[controller]["axes"]
        
        self.input_name["values"] = values
        if values:
            self.input_name.set(values[0])
    
    def _update_output_list(self, event=None):
        otype = self.output_type.get()
        
        if otype == "button":
            values = GAMEPAD_OUTPUTS["buttons"]
        else:
            values = GAMEPAD_OUTPUTS["axes"]
        
        self.output_name["values"] = values
        if values:
            self.output_name.set(values[0])
    
    def _refresh_conditions_list(self):
        self.conditions_list.delete(0, tk.END)
        for cond in self.conditions:
            text = f"{cond.type.value}: {cond.controller} {cond.input_name}"
            if cond.type in (ConditionType.AXIS_ABOVE, ConditionType.AXIS_BELOW):
                text += f" ({cond.value})"
            self.conditions_list.insert(tk.END, text)
    
    def _add_condition(self):
        dialog = ConditionDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            self.conditions.append(dialog.result)
            self._refresh_conditions_list()
    
    def _remove_condition(self):
        sel = self.conditions_list.curselection()
        if sel:
            self.conditions.pop(sel[0])
            self._refresh_conditions_list()
    
    def _load_mapping(self, m: Mapping):
        self.name_var.set(m.name)
        self.input_controller.set(m.input_controller)
        self.input_type.set(m.input_type.value)
        self._update_input_list()
        self.input_name.set(m.input_name)
        self.output_type.set(m.output_type.value)
        self._update_output_list()
        self.output_name.set(m.output_name)
        self.invert_var.set(m.invert)
        self.sensitivity_var.set(str(m.sensitivity))
        self.deadzone_var.set(str(m.deadzone))
        self.priority_var.set(str(m.priority))
    
    def _ok(self):
        try:
            self.result = Mapping(
                name=self.name_var.get(),
                input_type=InputType(self.input_type.get()),
                input_controller=self.input_controller.get(),
                input_name=self.input_name.get(),
                output_type=InputType(self.output_type.get()),
                output_name=self.output_name.get(),
                conditions=self.conditions,
                invert=self.invert_var.get(),
                sensitivity=float(self.sensitivity_var.get()),
                deadzone=float(self.deadzone_var.get()),
                priority=int(self.priority_var.get()),
                enabled=True,
            )
            self.destroy()
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid value: {e}")


class ConditionDialog(tk.Toplevel):
    """Dialog for adding a condition"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Add Condition")
        self.geometry("350x200")
        self.resizable(False, False)
        
        self.result: Optional[Condition] = None
        self._build_ui()
        
        self.transient(parent)
        self.grab_set()
    
    def _build_ui(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main, text="Type:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.cond_type = ttk.Combobox(main, values=[t.value for t in ConditionType], state="readonly", width=20)
        self.cond_type.grid(row=0, column=1, sticky=tk.W, pady=5)
        self.cond_type.set(ConditionType.BUTTON_HELD.value)
        
        ttk.Label(main, text="Controller:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.controller = ttk.Combobox(main, values=["left", "right"], state="readonly", width=20)
        self.controller.grid(row=1, column=1, sticky=tk.W, pady=5)
        self.controller.set("left")
        self.controller.bind("<<ComboboxSelected>>", self._update_inputs)
        
        ttk.Label(main, text="Input:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.input_name = ttk.Combobox(main, state="readonly", width=20)
        self.input_name.grid(row=2, column=1, sticky=tk.W, pady=5)
        self._update_inputs()
        
        ttk.Label(main, text="Threshold:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.threshold_var = tk.StringVar(value="0.5")
        ttk.Entry(main, textvariable=self.threshold_var, width=10).grid(row=3, column=1, sticky=tk.W, pady=5)
        
        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=20)
        ttk.Button(btn_frame, text="OK", command=self._ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)
    
    def _update_inputs(self, event=None):
        controller = self.controller.get()
        # Combine buttons and axes for conditions
        values = VR_INPUTS[controller]["buttons"] + VR_INPUTS[controller]["axes"]
        self.input_name["values"] = values
        if values:
            self.input_name.set(values[0])
    
    def _ok(self):
        try:
            self.result = Condition(
                type=ConditionType(self.cond_type.get()),
                controller=self.controller.get(),
                input_name=self.input_name.get(),
                value=float(self.threshold_var.get()),
            )
            self.destroy()
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid value: {e}")


class ConfigGUI(tk.Tk):
    """Main configuration GUI"""
    
    def __init__(self):
        super().__init__()
        self.title("VR Gamepad Configuration")
        self.geometry("800x600")
        
        self.profile: MappingProfile = create_default_profile()
        self.current_file: Optional[Path] = None
        
        self._build_menu()
        self._build_ui()
        self._refresh_mappings()
    
    def _build_menu(self):
        menubar = tk.Menu(self)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", command=self._new_profile, accelerator="Ctrl+N")
        file_menu.add_command(label="Open...", command=self._open_profile, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self._save_profile, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self._save_profile_as)
        file_menu.add_separator()
        file_menu.add_command(label="Load Default", command=self._load_default)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Add Mapping...", command=self._add_mapping)
        edit_menu.add_command(label="Edit Mapping...", command=self._edit_mapping)
        edit_menu.add_command(label="Delete Mapping", command=self._delete_mapping)
        edit_menu.add_separator()
        edit_menu.add_command(label="Duplicate Mapping", command=self._duplicate_mapping)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        self.config(menu=menubar)
        
        # Keybindings
        self.bind("<Control-n>", lambda e: self._new_profile())
        self.bind("<Control-o>", lambda e: self._open_profile())
        self.bind("<Control-s>", lambda e: self._save_profile())
    
    def _build_ui(self):
        # Main paned window
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - mappings list
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        ttk.Label(left_frame, text="Mappings:", font=("", 10, "bold")).pack(anchor=tk.W)
        
        # Treeview for mappings
        columns = ("input", "output", "conditions")
        self.tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=20)
        self.tree.heading("input", text="Input")
        self.tree.heading("output", text="Output")
        self.tree.heading("conditions", text="Conditions")
        self.tree.column("input", width=200)
        self.tree.column("output", width=150)
        self.tree.column("conditions", width=150)
        
        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind("<Double-1>", lambda e: self._edit_mapping())
        
        # Right panel - buttons and info
        right_frame = ttk.Frame(paned, width=200)
        paned.add(right_frame, weight=0)
        
        ttk.Label(right_frame, text="Actions:", font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Button(right_frame, text="Add Mapping", command=self._add_mapping).pack(fill=tk.X, pady=2)
        ttk.Button(right_frame, text="Edit Mapping", command=self._edit_mapping).pack(fill=tk.X, pady=2)
        ttk.Button(right_frame, text="Delete Mapping", command=self._delete_mapping).pack(fill=tk.X, pady=2)
        ttk.Button(right_frame, text="Duplicate", command=self._duplicate_mapping).pack(fill=tk.X, pady=2)
        
        ttk.Separator(right_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)
        
        ttk.Button(right_frame, text="Move Up", command=self._move_up).pack(fill=tk.X, pady=2)
        ttk.Button(right_frame, text="Move Down", command=self._move_down).pack(fill=tk.X, pady=2)
        
        ttk.Separator(right_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)
        
        # Profile settings
        ttk.Label(right_frame, text="Profile Settings:", font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        ttk.Label(right_frame, text="Name:").pack(anchor=tk.W)
        self.profile_name_var = tk.StringVar()
        ttk.Entry(right_frame, textvariable=self.profile_name_var).pack(fill=tk.X, pady=(0, 5))
        self.profile_name_var.trace_add("write", self._on_name_change)
        
        ttk.Label(right_frame, text="Global Deadzone:").pack(anchor=tk.W)
        self.deadzone_var = tk.StringVar(value="0.1")
        ttk.Entry(right_frame, textvariable=self.deadzone_var).pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(right_frame, text="Haptic Intensity:").pack(anchor=tk.W)
        self.haptic_var = tk.StringVar(value="0.5")
        ttk.Entry(right_frame, textvariable=self.haptic_var).pack(fill=tk.X, pady=(0, 5))

        ttk.Separator(right_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Device settings
        ttk.Label(right_frame, text="Device Settings:", font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))

        ttk.Label(right_frame, text="Device Name:").pack(anchor=tk.W)
        self.device_name_var = tk.StringVar(value="vJoy Device")
        ttk.Entry(right_frame, textvariable=self.device_name_var).pack(fill=tk.X, pady=(0, 5))

        ttk.Label(right_frame, text="Vendor ID (hex):").pack(anchor=tk.W)
        self.vendor_var = tk.StringVar(value="")
        ttk.Entry(right_frame, textvariable=self.vendor_var).pack(fill=tk.X, pady=(0, 5))

        ttk.Label(right_frame, text="Product ID (hex):").pack(anchor=tk.W)
        self.product_var = tk.StringVar(value="")
        ttk.Entry(right_frame, textvariable=self.product_var).pack(fill=tk.X, pady=(0, 5))

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _refresh_mappings(self):
        self.tree.delete(*self.tree.get_children())
        
        for i, m in enumerate(self.profile.mappings):
            input_str = f"{m.input_controller}.{m.input_name}"
            output_str = m.output_name
            cond_str = f"{len(m.conditions)} condition(s)" if m.conditions else ""
            
            tags = () if m.enabled else ("disabled",)
            self.tree.insert("", tk.END, iid=str(i), values=(input_str, output_str, cond_str), tags=tags)
        
        self.tree.tag_configure("disabled", foreground="gray")

        self.profile_name_var.set(self.profile.name)
        self.deadzone_var.set(str(self.profile.global_deadzone))
        self.haptic_var.set(str(self.profile.haptic_intensity))

        # Device settings
        self.device_name_var.set(self.profile.device_name)
        self.vendor_var.set(f"{self.profile.device_vendor:04x}" if self.profile.device_vendor else "")
        self.product_var.set(f"{self.profile.device_product:04x}" if self.profile.device_product else "")
    
    def _get_selected_index(self) -> Optional[int]:
        sel = self.tree.selection()
        if sel:
            return int(sel[0])
        return None
    
    def _add_mapping(self):
        dialog = MappingDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            self.profile.add_mapping(dialog.result)
            self._refresh_mappings()
            self.status_var.set("Mapping added")
    
    def _edit_mapping(self):
        idx = self._get_selected_index()
        if idx is None:
            return
        
        mapping = self.profile.mappings[idx]
        dialog = MappingDialog(self, mapping)
        self.wait_window(dialog)
        if dialog.result:
            self.profile.mappings[idx] = dialog.result
            self._refresh_mappings()
            self.status_var.set("Mapping updated")
    
    def _delete_mapping(self):
        idx = self._get_selected_index()
        if idx is None:
            return
        
        if messagebox.askyesno("Confirm", "Delete this mapping?"):
            self.profile.remove_mapping(idx)
            self._refresh_mappings()
            self.status_var.set("Mapping deleted")
    
    def _duplicate_mapping(self):
        idx = self._get_selected_index()
        if idx is None:
            return
        
        import copy
        m = copy.deepcopy(self.profile.mappings[idx])
        m.name = f"{m.name} (copy)"
        self.profile.add_mapping(m)
        self._refresh_mappings()
        self.status_var.set("Mapping duplicated")
    
    def _move_up(self):
        idx = self._get_selected_index()
        if idx is None or idx == 0:
            return
        
        self.profile.mappings[idx], self.profile.mappings[idx-1] = \
            self.profile.mappings[idx-1], self.profile.mappings[idx]
        self._refresh_mappings()
        self.tree.selection_set(str(idx-1))
    
    def _move_down(self):
        idx = self._get_selected_index()
        if idx is None or idx >= len(self.profile.mappings) - 1:
            return
        
        self.profile.mappings[idx], self.profile.mappings[idx+1] = \
            self.profile.mappings[idx+1], self.profile.mappings[idx]
        self._refresh_mappings()
        self.tree.selection_set(str(idx+1))
    
    def _on_name_change(self, *args):
        self.profile.name = self.profile_name_var.get()
    
    def _new_profile(self):
        if messagebox.askyesno("New Profile", "Create a new empty profile?"):
            self.profile = MappingProfile(name="New Profile")
            self.current_file = None
            self._refresh_mappings()
            self.status_var.set("New profile created")
    
    def _load_default(self):
        if messagebox.askyesno("Load Default", "Load the default profile?"):
            self.profile = create_default_profile()
            self.current_file = None
            self._refresh_mappings()
            self.status_var.set("Default profile loaded")
    
    def _open_profile(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if path:
            try:
                self.profile = MappingProfile.load(path)
                self.current_file = Path(path)
                self._refresh_mappings()
                self.status_var.set(f"Loaded: {path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load: {e}")
    
    def _update_profile_from_ui(self):
        """Update profile object from UI fields"""
        try:
            self.profile.global_deadzone = float(self.deadzone_var.get())
        except ValueError:
            pass
        try:
            self.profile.haptic_intensity = float(self.haptic_var.get())
        except ValueError:
            pass

        # Device settings
        self.profile.device_name = self.device_name_var.get() or "vJoy Device"

        vendor_str = self.vendor_var.get().strip()
        if vendor_str:
            try:
                self.profile.device_vendor = int(vendor_str, 16)
            except ValueError:
                pass
        else:
            self.profile.device_vendor = None

        product_str = self.product_var.get().strip()
        if product_str:
            try:
                self.profile.device_product = int(product_str, 16)
            except ValueError:
                pass
        else:
            self.profile.device_product = None

    def _save_profile(self):
        self._update_profile_from_ui()

        if self.current_file:
            self.profile.save(str(self.current_file))
            self.status_var.set(f"Saved: {self.current_file}")
        else:
            self._save_profile_as()
    
    def _save_profile_as(self):
        self._update_profile_from_ui()

        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if path:
            self.profile.save(path)
            self.current_file = Path(path)
            self.status_var.set(f"Saved: {path}")


def main():
    app = ConfigGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
