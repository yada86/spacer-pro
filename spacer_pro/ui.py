import bpy
from bpy.types import Panel

from .spacer_core import calc_clearance, resolve_diameters


class SPACERPRO_PT_panel(Panel):
    bl_label = "Spacer PRO"
    bl_idname = "SPACERPRO_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Spacer PRO"

    def draw(self, context):
        layout = self.layout
        props = context.scene.spacerpro_props
        pstate = context.scene.spacerpro_preset_state

        # -------------------------
        # Presets (compact)
        # -------------------------
        box = layout.box()
        box.label(text="Presets")

        row = box.row(align=True)
        row.prop(pstate, "preset_name", text="")
        row.operator("spacerpro.preset_apply", text="Apply")

        row = box.row(align=True)
        row.prop(pstate, "preset_name_new", text="")
        boxrow = box.row(align=True)
        boxrow.operator("spacerpro.preset_save", text="Save").overwrite = False
        boxrow.operator("spacerpro.preset_save", text="Overwrite").overwrite = True
        boxrow.operator("spacerpro.preset_delete", text="Delete")

        # -------------------------
        # Main Geometry
        # -------------------------
        box = layout.box()
        box.label(text="Main Geometry")
        box.prop(props, "diameter_mode", expand=True)

        if props.diameter_mode == "OD_ID":
            box.prop(props, "od_mm")
            box.prop(props, "id_mm")
        elif props.diameter_mode == "OD_WALL":
            box.prop(props, "od_mm")
            box.prop(props, "wall_mm")
        elif props.diameter_mode == "ID_WALL":
            box.prop(props, "id_mm")
            box.prop(props, "wall_mm")

        box.prop(props, "height_mm")

        # -------------------------
        # Fit / Material (dropdowns)
        # -------------------------
        box = layout.box()
        box.label(text="Fit / Material")

        # dropdowns: DO NOT use expand=True here
        box.prop(props, "fit_class", text="Fit")
        box.prop(props, "material", text="Material")
        box.prop(props, "clearance_offset")

        # -------------------------
        # Info
        # -------------------------
        clearance = calc_clearance(props.fit_class, props.material, props.clearance_offset)
        resolved_od, resolved_id = resolve_diameters(
            props.diameter_mode,
            props.od_mm,
            props.id_mm,
            props.wall_mm,
        )
        final_id = resolved_id + clearance

        info = layout.box()
        info.label(text="Info")
        info.label(text=f"Resolved OD: {resolved_od:.2f} mm")
        info.label(text=f"Resolved ID: {resolved_id:.2f} mm")
        info.label(text=f"Final clearance: {clearance:.2f} mm")
        info.label(text=f"Final ID: {final_id:.2f} mm")

        layout.separator()
        layout.operator("spacerpro.generate", icon="MESH_CYLINDER")


classes = (SPACERPRO_PT_panel,)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)