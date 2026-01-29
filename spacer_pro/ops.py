import bpy
from bpy.types import Operator

from .spacer_core import (
    calc_clearance,
    resolve_diameters,
    build_spacer,
)


class SPACERPRO_OT_generate(Operator):
    bl_idname = "spacerpro.generate"
    bl_label = "Generate Spacer"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.spacerpro_props

        # Resolve OD/ID based on mode (OD+ID / OD+Wall / ID+Wall)
        resolved_od, resolved_id = resolve_diameters(
            props.diameter_mode,
            props.od_mm,
            props.id_mm,
            props.wall_mm,
        )

        # Validation
        if resolved_id <= 0.0 or resolved_od <= 0.0:
            self.report({"ERROR"}, "Resolved diameters must be > 0.")
            return {"CANCELLED"}

        if resolved_id >= resolved_od:
            self.report({"ERROR"}, "Resolved ID must be smaller than OD.")
            return {"CANCELLED"}

        # Clearance
        clearance = calc_clearance(props.fit_class, props.material, props.clearance_offset)
        final_id = resolved_id + clearance

        if final_id >= resolved_od:
            self.report({"ERROR"}, "Final ID (with clearance) must be smaller than OD.")
            return {"CANCELLED"}

        # Build mesh
        outer = build_spacer(resolved_od, resolved_id, props.height_mm, clearance)

        # Metadata tags (future-proof)
        outer["SPACERPRO_mode"] = props.diameter_mode
        outer["SPACERPRO_fit"] = props.fit_class
        outer["SPACERPRO_material"] = props.material
        outer["SPACERPRO_clearance"] = float(clearance)
        outer["SPACERPRO_resolved_od"] = float(resolved_od)
        outer["SPACERPRO_resolved_id"] = float(resolved_id)

        self.report(
            {"INFO"},
            f"Generated spacer. OD {resolved_od:.2f} / ID {resolved_id:.2f} -> Final ID {final_id:.2f} (clr {clearance:.2f})"
        )
        return {"FINISHED"}


classes = (SPACERPRO_OT_generate,)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)