bl_info = {
    "name": "Spacer PRO (MVP)",
    "author": "Daniel Albrethsen",
    "version": (0, 1, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > Spacer PRO",
    "description": "Parametric spacer generator (MVP)",
    "category": "3D View",
}

import bpy
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import FloatProperty, EnumProperty, BoolProperty, PointerProperty


# -------------------------
# Preset math (MVP)
# -------------------------

FIT_BASELINE = {
    "LOOSE": 0.30,
    "NORMAL": 0.20,
    "TIGHT": 0.12,
    "PRESS": 0.05,
}

MAT_OFFSET = {
    "PLA": 0.00,
    "PETG": 0.03,
    "ABS": 0.05,
    "NYLON": 0.07,
}

def calc_clearance(fit_class: str, material: str, offset: float) -> float:
    base = FIT_BASELINE.get(fit_class, 0.20)
    moff = MAT_OFFSET.get(material, 0.00)
    # clamp a bit to avoid nonsense
    c = base + moff + offset
    return max(0.00, min(c, 0.60))


# -------------------------
# Properties
# -------------------------

class SPACERPRO_Props(PropertyGroup):
    od_mm: FloatProperty(name="OD (mm)", default=20.0, min=0.1, soft_max=300.0)
    id_mm: FloatProperty(name="ID (mm)", default=10.0, min=0.1, soft_max=300.0)
    height_mm: FloatProperty(name="Height (mm)", default=5.0, min=0.1, soft_max=200.0)

    fit_class: EnumProperty(
        name="Fit",
        items=[
            ("LOOSE", "Loose", "Loose fit"),
            ("NORMAL", "Normal", "Normal fit"),
            ("TIGHT", "Tight", "Tight fit"),
            ("PRESS", "Press", "Press fit"),
        ],
        default="NORMAL",
    )

    material: EnumProperty(
        name="Material",
        items=[
            ("PLA", "PLA", ""),
            ("PETG", "PETG", ""),
            ("ABS", "ABS", ""),
            ("NYLON", "Nylon", ""),
        ],
        default="PETG",
    )

    clearance_offset: FloatProperty(
        name="Clearance Offset (mm)",
        default=0.00,
        min=-0.10,
        max=0.30,
        description="Fine tune clearance (+ looser, - tighter)",
    )

    chamfer_top: FloatProperty(name="Chamfer Top (mm)", default=0.0, min=0.0, max=5.0)
    chamfer_bottom: FloatProperty(name="Chamfer Bottom (mm)", default=0.0, min=0.0, max=5.0)

    show_advanced: BoolProperty(name="Advanced", default=False)


# -------------------------
# Operator
# -------------------------

class SPACERPRO_OT_generate(Operator):
    bl_idname = "spacerpro.generate"
    bl_label = "Generate Spacer"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.spacerpro_props

        # Basic validation
        if props.id_mm >= props.od_mm:
            self.report({"ERROR"}, "ID must be smaller than OD.")
            return {"CANCELLED"}

        clearance = calc_clearance(props.fit_class, props.material, props.clearance_offset)
        final_id = props.id_mm + clearance

        if final_id >= props.od_mm:
            self.report({"ERROR"}, "Final ID (with clearance) must be smaller than OD.")
            return {"CANCELLED"}

        # Create outer cylinder
        bpy.ops.mesh.primitive_cylinder_add(
            radius=props.od_mm * 0.5,
            depth=props.height_mm,
            enter_editmode=False,
            align='WORLD',
        )
        outer = context.active_object
        outer.name = "SpacerPRO_Outer"

        # Create inner cylinder (cutter)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=final_id * 0.5,
            depth=props.height_mm + 0.2,  # slightly longer for clean boolean
            enter_editmode=False,
            align='WORLD',
        )
        inner = context.active_object
        inner.name = "SpacerPRO_Cutter"

        # Boolean difference
        mod = outer.modifiers.new(name="SPACERPRO_Boolean", type='BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object = inner
        mod.solver = 'MANIFOLD'

        # Apply modifier
        context.view_layer.objects.active = outer
        bpy.ops.object.modifier_apply(modifier=mod.name)

        # Delete cutter
        bpy.data.objects.remove(inner, do_unlink=True)

        # Tag object with metadata (future-proof)
        outer["SPACERPRO_fit"] = props.fit_class
        outer["SPACERPRO_material"] = props.material
        outer["SPACERPRO_clearance"] = float(clearance)

        self.report({"INFO"}, f"Generated spacer. Clearance: {clearance:.2f} mm (ID -> {final_id:.2f} mm)")
        return {"FINISHED"}


# -------------------------
# UI Panel
# -------------------------

class SPACERPRO_PT_panel(Panel):
    bl_label = "Spacer PRO"
    bl_idname = "SPACERPRO_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Spacer PRO"

    def draw(self, context):
        layout = self.layout
        props = context.scene.spacerpro_props

        # MAIN GEOMETRY
        box = layout.box()
        box.label(text="Main Geometry")
        box.prop(props, "od_mm")
        box.prop(props, "id_mm")
        box.prop(props, "height_mm")

        # FIT / MATERIAL
        box = layout.box()
        box.label(text="Fit / Material")
        box.prop(props, "fit_class", expand=True)
        box.prop(props, "material", expand=True)
        box.prop(props, "clearance_offset")

        # INFO
        clearance = calc_clearance(props.fit_class, props.material, props.clearance_offset)
        final_id = props.id_mm + clearance
        info = layout.box()
        info.label(text="Info")
        info.label(text=f"Final clearance: {clearance:.2f} mm")
        info.label(text=f"Final ID: {final_id:.2f} mm")

        # ADVANCED (placeholder)
        layout.prop(props, "show_advanced", toggle=True)
        if props.show_advanced:
            box = layout.box()
            box.label(text="Advanced (WIP)")
            box.prop(props, "chamfer_top")
            box.prop(props, "chamfer_bottom")

        # ACTION
        layout.separator()
        layout.operator("spacerpro.generate", icon="MESH_CYLINDER")


# -------------------------
# Register
# -------------------------

classes = (
    SPACERPRO_Props,
    SPACERPRO_OT_generate,
    SPACERPRO_PT_panel,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.spacerpro_props = PointerProperty(type=SPACERPRO_Props)

def unregister():
    del bpy.types.Scene.spacerpro_props
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()