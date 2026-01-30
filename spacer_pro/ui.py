# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
from bpy.types import Panel
from . import presets


def _error_box(layout, text):
    box = layout.box()
    row = box.row()
    row.alert = True
    row.label(text=text, icon="ERROR")
    return box


def _ops_ok():
    try:
        need = ("generate", "update", "preset_apply", "preset_save", "preset_delete")
        return all(hasattr(bpy.ops.spacerpro, n) for n in need)
    except Exception:
        return False


class SPACERPRO_PT_Main(Panel):
    bl_label = "Spacer PRO"
    bl_idname = "SPACERPRO_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Spacer PRO"

    def draw(self, context):
        layout = self.layout
        sc = context.scene
        props = getattr(sc, "spacerpro_props", None)

        if not props:
            _error_box(layout, "spacerpro_props missing (register issue)")
            return

        # Small dev reload icon (only in Advanced mode)
        top = layout.row()
        top.alignment = "RIGHT"
        if getattr(props, "show_advanced", False) and hasattr(bpy.ops.spacerpro, "reload_scripts"):
            top.operator("spacerpro.reload_scripts", text="", icon="FILE_REFRESH")

        # Dimensions
        box = layout.box()
        box.label(text="Dimensions")
        col = box.column(align=True)
        col.prop(props, "inner_diameter", text="Inner Diameter")
        col.prop(props, "outer_diameter", text="Outer Diameter")
        col.prop(props, "height", text="Height")

        # Chamfers (UI-ready)
        box = layout.box()
        box.label(text="Chamfers")
        box.prop(props, "chamfer_enable", text="Chamfer")
        if props.chamfer_enable:
            row = box.row(align=True)
            row.prop(props, "chamfer_side", expand=True)
            row = box.row(align=True)
            row.prop(props, "chamfer_region", expand=True)
            row = box.row(align=True)
            row.prop(props, "chamfer_size", text="Size")
            row.prop(props, "chamfer_angle_deg", text="Angle")

        # Taper (UI-ready)
        box = layout.box()
        box.label(text="Taper")
        box.prop(props, "taper_enable", text="Taper")
        if props.taper_enable:
            row = box.row(align=True)
            row.prop(props, "taper_side", expand=True)
            row = box.row(align=True)
            row.prop(props, "taper_region", expand=True)
            row = box.row(align=True)
            row.prop(props, "taper_mode", expand=True)
            if props.taper_mode == "ANGLE":
                box.prop(props, "taper_angle_deg", text="Angle")
            else:
                box.prop(props, "taper_height", text="Height")

        # Presets (truth-based)
        if not _ops_ok() or not getattr(sc, "spacerpro_preset_state", None):
            _error_box(layout, "Presets unavailable (register issue)")
        else:
            presets.draw_presets_ui(layout, context)

        # PRO WORKFLOW BUTTONS
        row = layout.row(align=True)
        row.scale_y = 1.35
        row.operator("spacerpro.generate", text="Create Spacer", icon="ADD")
        row.operator("spacerpro.update", text="Update", icon="FILE_REFRESH")

        # Advanced toggle
        layout.prop(props, "show_advanced", text="Advanced", toggle=True)

        if props.show_advanced:
            box = layout.box()
            box.label(text="Advanced")
            box.prop(props, "debug_mode", text="Debug")
            last_obj = getattr(sc, "spacerpro_last_object", None)
            box.label(text=f"Last: {last_obj.name if last_obj else 'None'}", icon="OBJECT_DATA")


_classes = (SPACERPRO_PT_Main,)

def register():
    for c in _classes:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(_classes):
        try:
            bpy.utils.unregister_class(c)
        except Exception:
            pass
