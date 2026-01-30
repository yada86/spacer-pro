# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
from bpy.types import Panel

try:
    from . import presets
except Exception:
    presets = None


CORNERS = ("TI", "TO", "BI", "BO")
CORNER_LABEL = {
    "TI": "Top Inner",
    "TO": "Top Outer",
    "BI": "Bottom Inner",
    "BO": "Bottom Outer",
}
CORNER_PROPS = {
    "TI": ("ch_ti_on", "ch_ti_size", "ch_ti_angle"),
    "TO": ("ch_to_on", "ch_to_size", "ch_to_angle"),
    "BI": ("ch_bi_on", "ch_bi_size", "ch_bi_angle"),
    "BO": ("ch_bo_on", "ch_bo_size", "ch_bo_angle"),
}


def _error_box(layout, text):
    box = layout.box()
    row = box.row()
    row.alert = True
    row.label(text=text, icon="ERROR")
    return box


def _has_props(props, names):
    return all(hasattr(props, n) for n in names)


# ----------------------------
# Main container
# ----------------------------

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
            _error_box(layout, "spacerpro_props missing (register order issue)")
            return

        # Workflow buttons at bottom (Blender-ish)
        row = layout.row(align=True)
        row.scale_y = 1.25
        row.operator("spacerpro.generate", text="Create Spacer", icon="ADD")
        row.operator("spacerpro.update", text="Update", icon="FILE_REFRESH")

        # Advanced toggle (optional)
        if hasattr(props, "show_advanced"):
            layout.prop(props, "show_advanced", text="Advanced", toggle=True)
            if props.show_advanced:
                adv = layout.box()
                adv.label(text="Advanced")
                if hasattr(props, "debug_mode"):
                    adv.prop(props, "debug_mode", text="Debug")
                last_obj = getattr(sc, "spacerpro_last_object", None)
                adv.label(text=f"Last: {last_obj.name if last_obj else 'None'}", icon="OBJECT_DATA")


# ----------------------------
# Subpanels = Blender-style dropdown sections
# ----------------------------

class SPACERPRO_PT_Dimensions(Panel):
    bl_label = "Dimensions"
    bl_idname = "SPACERPRO_PT_dimensions"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Spacer PRO"
    bl_parent_id = "SPACERPRO_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        props = getattr(context.scene, "spacerpro_props", None)
        if not props:
            _error_box(layout, "spacerpro_props missing")
            return

        col = layout.column(align=True)
        for p, label in (("inner_diameter", "Inner Diameter"),
                         ("outer_diameter", "Outer Diameter"),
                         ("height", "Height")):
            if hasattr(props, p):
                col.prop(props, p, text=label)
            else:
                _error_box(col, f"Missing property: {p}")
                return


class SPACERPRO_PT_Chamfers(Panel):
    bl_label = "Chamfers"
    bl_idname = "SPACERPRO_PT_chamfers"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Spacer PRO"
    bl_parent_id = "SPACERPRO_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        props = getattr(context.scene, "spacerpro_props", None)
        if not props:
            _error_box(layout, "spacerpro_props missing")
            return

        if not hasattr(props, "chamfer_enable"):
            _error_box(layout, "Missing property: chamfer_enable")
            return

        layout.prop(props, "chamfer_enable", text="Chamfer")

        if not props.chamfer_enable:
            return

        required = (
            "edit_mode",
            "chamfer_active_corner",
            "chamfer_master_size",
            "chamfer_master_angle",
            "ch_ti_on", "ch_to_on", "ch_bi_on", "ch_bo_on",
            "ch_ti_size", "ch_to_size", "ch_bi_size", "ch_bo_size",
            "ch_ti_angle", "ch_to_angle", "ch_bi_angle", "ch_bo_angle",
        )
        if not _has_props(props, required):
            missing = [n for n in required if not hasattr(props, n)]
            _error_box(layout, "Chamfer UI can't load: missing props in spacer_core.py")
            for n in missing[:10]:
                layout.label(text=f"- {n}")
            if len(missing) > 10:
                layout.label(text=f"... (+{len(missing)-10} more)")
            return

        # Edit mode
        row = layout.row(align=True)
        row.label(text="Edit Mode:")
        row.prop(props, "edit_mode", expand=True)

        # Linked master controls (vertical safe)
        if props.edit_mode == "LINKED":
            col = layout.column(align=True)
            col.prop(props, "chamfer_master_size", text="Size")
            col.prop(props, "chamfer_master_angle", text="Angle")

        # Corner blocks (vertical safe)
        for c in CORNERS:
            on_prop, sz_prop, an_prop = CORNER_PROPS[c]
            is_active = (props.chamfer_active_corner == c)
            is_on = getattr(props, on_prop, False)

            cb = layout.box()
            r = cb.row(align=True)
            r.prop_enum(props, "chamfer_active_corner", c, text="")  # (•)
            r.prop(props, on_prop, text="")                         # ☑
            r.label(text=CORNER_LABEL[c])

            if props.edit_mode == "INDIVIDUAL":
                col2 = cb.column(align=True)
                col2.enabled = bool(is_on and is_active)
                col2.prop(props, sz_prop, text="Size")
                col2.prop(props, an_prop, text="Angle")
            else:
                col2 = cb.column(align=True)
                col2.enabled = False
                col2.prop(props, sz_prop, text="Size")
                col2.prop(props, an_prop, text="Angle")


class SPACERPRO_PT_Taper(Panel):
    bl_label = "Taper"
    bl_idname = "SPACERPRO_PT_taper"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Spacer PRO"
    bl_parent_id = "SPACERPRO_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        props = getattr(context.scene, "spacerpro_props", None)
        if not props:
            _error_box(layout, "spacerpro_props missing")
            return

        if not hasattr(props, "taper_enable"):
            layout.label(text="(taper props not registered yet)")
            return

        layout.prop(props, "taper_enable", text="Taper")
        if not props.taper_enable:
            return

        # If you already have these props, show them. Otherwise, keep safe.
        col = layout.column(align=True)
        if hasattr(props, "taper_side"):
            col.prop(props, "taper_side", text="Side")
        if hasattr(props, "taper_region"):
            col.prop(props, "taper_region", text="Region")
        if hasattr(props, "taper_mode"):
            col.prop(props, "taper_mode", text="Mode")

        # Mode-specific
        if getattr(props, "taper_mode", "ANGLE") == "ANGLE" and hasattr(props, "taper_angle_deg"):
            col.prop(props, "taper_angle_deg", text="Angle")
        if getattr(props, "taper_mode", "ANGLE") == "HEIGHT" and hasattr(props, "taper_height"):
            col.prop(props, "taper_height", text="Height")


class SPACERPRO_PT_Presets(Panel):
    bl_label = "Presets"
    bl_idname = "SPACERPRO_PT_presets"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Spacer PRO"
    bl_parent_id = "SPACERPRO_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        if presets is None:
            _error_box(layout, "Presets unavailable (import failed)")
            return

        try:
            presets.draw_presets_ui(layout, context)
        except Exception as e:
            _error_box(layout, f"Presets UI error: {e}")


# ----------------------------
# Register
# ----------------------------

_classes = (
    SPACERPRO_PT_Main,
    SPACERPRO_PT_Dimensions,
    SPACERPRO_PT_Chamfers,
    SPACERPRO_PT_Taper,
    SPACERPRO_PT_Presets,
)

def register():
    for c in _classes:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(_classes):
        try:
            bpy.utils.unregister_class(c)
        except Exception:
            pass
