import bpy
from bpy.types import Panel
from .spacer_core import calc_clearance


class SPACERPRO_PT_panel(Panel):
    bl_label = "Spacer PRO"
    bl_idname = "SPACERPRO_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Spacer PRO"

    def draw(self, context):
        layout = self.layout
        props = context.scene.spacerpro_props

        box = layout.box()
        box.label(text="Main Geometry")
        box.prop(props, "od_mm")
        box.prop(props, "id_mm")
        box.prop(props, "height_mm")

        box = layout.box()
        box.label(text="Fit / Material")
        box.prop(props, "fit_class", expand=True)
        box.prop(props, "material", expand=True)
        box.prop(props, "clearance_offset")

        clearance = calc_clearance(props.fit_class, props.material, props.clearance_offset)
        final_id = props.id_mm + clearance
        info = layout.box()
        info.label(text="Info")
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