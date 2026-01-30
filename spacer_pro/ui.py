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

CH_CORNER_PROPS = {
    "TI": ("ch_ti_on", "ch_ti_size", "ch_ti_angle"),
    "TO": ("ch_to_on", "ch_to_size", "ch_to_angle"),
    "BI": ("ch_bi_on", "ch_bi_size", "ch_bi_angle"),
    "BO": ("ch_bo_on", "ch_bo_size", "ch_bo_angle"),
}

# NEW TAPER: enable + amount + depth + angle (mode chooses amount-vs-angle behavior)
TP_CORNER_PROPS = {
    "TI": ("tp_ti_on", "tp_ti_amount", "tp_ti_depth", "tp_ti_angle"),
    "TO": ("tp_to_on", "tp_to_amount", "tp_to_depth", "tp_to_angle"),
    "BI": ("tp_bi_on", "tp_bi_amount", "tp_bi_depth", "tp_bi_angle"),
    "BO": ("tp_bo_on", "tp_bo_amount", "tp_bo_depth", "tp_bo_angle"),
}


def _error_box(layout, text):
    box = layout.box()
    row = box.row()
    row.alert = True
    row.label(text=text, icon="ERROR")
    return box


def _has_props(props, names):
    return all(hasattr(props, n) for n in names)


def _corner_header_row(box, props, corner, on_prop, is_active, domain):
    """checkbox + lamp + big clickable label (feels like click-anywhere)"""
    r = box.row(align=True)
    r.prop(props, on_prop, text="")  # membership

    icon = "RADIOBUT_ON" if is_active else "RADIOBUT_OFF"

    op_lamp = r.operator("spacerpro.set_active_corner", text="", icon=icon, emboss=False)
    op_lamp.corner = corner
    op_lamp.domain = domain

    op_big = r.operator("spacerpro.set_active_corner", text=CORNER_LABEL[corner], emboss=False)
    op_big.corner = corner
    op_big.domain = domain

    return r


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

        row = layout.row(align=True)
        row.scale_y = 1.15
        row.operator("spacerpro.generate", text="Create Spacer", icon="ADD")
        row.operator("spacerpro.update", text="Update", icon="FILE_REFRESH")

        if hasattr(props, "show_advanced"):
            layout.prop(props, "show_advanced", text="Advanced", toggle=True)
            if props.show_advanced:
                adv = layout.box()
                if hasattr(props, "debug_mode"):
                    adv.prop(props, "debug_mode", text="Debug")
                last_obj = getattr(sc, "spacerpro_last_object", None)
                adv.label(text=f"Last: {last_obj.name if last_obj else 'None'}", icon="OBJECT_DATA")


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
        col.prop(props, "inner_diameter", text="Inner Diameter")
        col.prop(props, "outer_diameter", text="Outer Diameter")
        col.prop(props, "height", text="Height")


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

        layout.prop(props, "chamfer_enable", text="Chamfer")
        if not props.chamfer_enable:
            return

        required = (
            "edit_mode", "chamfer_active_corner",
            "chamfer_master_size", "chamfer_master_angle",
            "ch_ti_on", "ch_to_on", "ch_bi_on", "ch_bo_on",
            "ch_ti_size", "ch_to_size", "ch_bi_size", "ch_bo_size",
            "ch_ti_angle", "ch_to_angle", "ch_bi_angle", "ch_bo_angle",
        )
        if not _has_props(props, required):
            _error_box(layout, "Chamfer props missing in spacer_core.py")
            return

        row = layout.row(align=True)
        row.label(text="Edit Mode:")
        row.prop(props, "edit_mode", expand=True)

        if props.edit_mode == "LINKED":
            col = layout.column(align=True)
            col.prop(props, "chamfer_master_size", text="Size")
            col.prop(props, "chamfer_master_angle", text="Angle")

        for c in CORNERS:
            on_prop, sz_prop, an_prop = CH_CORNER_PROPS[c]
            is_active = (props.chamfer_active_corner == c)
            is_on = getattr(props, on_prop, False)

            cb = layout.box()
            _corner_header_row(cb, props, c, on_prop, is_active, "CHAMFER")

            col2 = cb.column(align=True)

            if props.edit_mode == "INDIVIDUAL":
                col2.enabled = bool(is_on and is_active)
                col2.prop(props, sz_prop, text="Size")
                col2.prop(props, an_prop, text="Angle")
            else:
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

        layout.prop(props, "taper_enable", text="Taper")
        if not props.taper_enable:
            return

        required = (
            "taper_mode",
            "taper_edit_mode", "taper_active_corner",
            "taper_master_amount", "taper_master_depth", "taper_master_angle",
            "tp_ti_on", "tp_to_on", "tp_bi_on", "tp_bo_on",
            "tp_ti_amount", "tp_to_amount", "tp_bi_amount", "tp_bo_amount",
            "tp_ti_depth", "tp_to_depth", "tp_bi_depth", "tp_bo_depth",
            "tp_ti_angle", "tp_to_angle", "tp_bi_angle", "tp_bo_angle",
        )
        if not _has_props(props, required):
            _error_box(layout, "Taper props missing in spacer_core.py")
            return

        col = layout.column(align=True)
        col.prop(props, "taper_mode", text="Mode")

        row = layout.row(align=True)
        row.label(text="Edit Mode:")
        row.prop(props, "taper_edit_mode", expand=True)

        if props.taper_edit_mode == "LINKED":
            m = layout.column(align=True)
            m.prop(props, "taper_master_depth", text="Depth")
            if props.taper_mode == "AMOUNT":
                m.prop(props, "taper_master_amount", text="Amount")
            else:
                m.prop(props, "taper_master_angle", text="Angle")

        for c in CORNERS:
            on_prop, amt_prop, dep_prop, ang_prop = TP_CORNER_PROPS[c]
            is_active = (props.taper_active_corner == c)
            is_on = getattr(props, on_prop, False)

            cb = layout.box()
            _corner_header_row(cb, props, c, on_prop, is_active, "TAPER")

            col2 = cb.column(align=True)

            if props.taper_edit_mode == "INDIVIDUAL":
                col2.enabled = bool(is_on and is_active)
                col2.prop(props, dep_prop, text="Depth")
                if props.taper_mode == "AMOUNT":
                    col2.prop(props, amt_prop, text="Amount")
                else:
                    col2.prop(props, ang_prop, text="Angle")
            else:
                col2.enabled = False
                col2.prop(props, dep_prop, text="Depth")
                if props.taper_mode == "AMOUNT":
                    col2.prop(props, amt_prop, text="Amount")
                else:
                    col2.prop(props, ang_prop, text="Angle")


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
