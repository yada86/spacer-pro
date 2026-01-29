import bpy
from bpy.types import Operator
from .spacer_core import calc_clearance


class SPACERPRO_OT_generate(Operator):
    bl_idname = "spacerpro.generate"
    bl_label = "Generate Spacer"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.spacerpro_props

        if props.id_mm >= props.od_mm:
            self.report({"ERROR"}, "ID must be smaller than OD.")
            return {"CANCELLED"}

        clearance = calc_clearance(props.fit_class, props.material, props.clearance_offset)
        final_id = props.id_mm + clearance

        if final_id >= props.od_mm:
            self.report({"ERROR"}, "Final ID (with clearance) must be smaller than OD.")
            return {"CANCELLED"}

        bpy.ops.mesh.primitive_cylinder_add(
            radius=props.od_mm * 0.5,
            depth=props.height_mm,
            enter_editmode=False,
            align='WORLD',
        )
        outer = context.active_object
        outer.name = "SpacerPRO_Outer"

        bpy.ops.mesh.primitive_cylinder_add(
            radius=final_id * 0.5,
            depth=props.height_mm + 0.2,
            enter_editmode=False,
            align='WORLD',
        )
        inner = context.active_object
        inner.name = "SpacerPRO_Cutter"

        mod = outer.modifiers.new(name="SPACERPRO_Boolean", type='BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object = inner
        mod.solver = 'MANIFOLD'  # FLOAT/EXACT/MANIFOLD in Blender 5.x

        context.view_layer.objects.active = outer
        bpy.ops.object.modifier_apply(modifier=mod.name)

        bpy.data.objects.remove(inner, do_unlink=True)

        outer["SPACERPRO_fit"] = props.fit_class
        outer["SPACERPRO_material"] = props.material
        outer["SPACERPRO_clearance"] = float(clearance)

        self.report({"INFO"}, f"Generated spacer. Clearance: {clearance:.2f} mm (ID -> {final_id:.2f} mm)")
        return {"FINISHED"}


classes = (SPACERPRO_OT_generate,)

def register():
    for c in classes:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)