import bpy
from bpy.types import Operator

from .spacer_core import (
    calc_clearance,
    resolve_diameters,
    build_spacer,
)

from . import presets


# -------------------------
# Generate
# -------------------------

class SPACERPRO_OT_generate(Operator):
    bl_idname = "spacerpro.generate"
    bl_label = "Generate Spacer"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.spacerpro_props

        resolved_od, resolved_id = resolve_diameters(
            props.diameter_mode,
            props.od_mm,
            props.id_mm,
            props.wall_mm,
        )

        if resolved_id <= 0.0 or resolved_od <= 0.0:
            self.report({"ERROR"}, "Resolved diameters must be > 0.")
            return {"CANCELLED"}

        if resolved_id >= resolved_od:
            self.report({"ERROR"}, "Resolved ID must be smaller than OD.")
            return {"CANCELLED"}

        clearance = calc_clearance(props.fit_class, props.material, props.clearance_offset)
        final_id = resolved_id + clearance

        if final_id >= resolved_od:
            self.report({"ERROR"}, "Final ID (with clearance) must be smaller than OD.")
            return {"CANCELLED"}

        outer = build_spacer(resolved_od, resolved_id, props.height_mm, clearance)

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


# -------------------------
# Presets
# -------------------------

def _props_to_dict(scene_props) -> dict:
    return {
        "diameter_mode": scene_props.diameter_mode,
        "od_mm": float(scene_props.od_mm),
        "id_mm": float(scene_props.id_mm),
        "wall_mm": float(scene_props.wall_mm),
        "height_mm": float(scene_props.height_mm),
        "fit_class": scene_props.fit_class,
        "material": scene_props.material,
        "clearance_offset": float(scene_props.clearance_offset),
    }

def _apply_dict_to_props(scene_props, d: dict):
    # Use .get with fallback to avoid crashes if preset is older
    scene_props.diameter_mode = d.get("diameter_mode", scene_props.diameter_mode)
    scene_props.od_mm = float(d.get("od_mm", scene_props.od_mm))
    scene_props.id_mm = float(d.get("id_mm", scene_props.id_mm))
    scene_props.wall_mm = float(d.get("wall_mm", scene_props.wall_mm))
    scene_props.height_mm = float(d.get("height_mm", scene_props.height_mm))
    scene_props.fit_class = d.get("fit_class", scene_props.fit_class)
    scene_props.material = d.get("material", scene_props.material)
    scene_props.clearance_offset = float(d.get("clearance_offset", scene_props.clearance_offset))


class SPACERPRO_OT_preset_apply(Operator):
    bl_idname = "spacerpro.preset_apply"
    bl_label = "Apply Preset"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        pstate = context.scene.spacerpro_preset_state
        props = context.scene.spacerpro_props

        name = pstate.preset_name
        data = presets.load_presets()
        if name not in data:
            self.report({"ERROR"}, f"Preset not found: {name}")
            return {"CANCELLED"}

        _apply_dict_to_props(props, data[name])
        self.report({"INFO"}, f"Applied preset: {name}")
        return {"FINISHED"}


class SPACERPRO_OT_preset_save(Operator):
    bl_idname = "spacerpro.preset_save"
    bl_label = "Save Preset"
    bl_options = {"REGISTER", "UNDO"}

    overwrite: bpy.props.BoolProperty(name="Overwrite", default=False)

    def execute(self, context):
        pstate = context.scene.spacerpro_preset_state
        props = context.scene.spacerpro_props

        name = (pstate.preset_name_new or "").strip()
        if not name:
            self.report({"ERROR"}, "Preset name is empty.")
            return {"CANCELLED"}

        data = presets.load_presets()

        if (name in data) and (not self.overwrite):
            self.report({"ERROR"}, "Preset exists. Use Overwrite.")
            return {"CANCELLED"}

        data[name] = _props_to_dict(props)
        presets.save_presets(data)

        # set dropdown to new preset
        try:
            pstate.preset_name = name
        except Exception:
            pass

        self.report({"INFO"}, f"Saved preset: {name}")
        return {"FINISHED"}


class SPACERPRO_OT_preset_delete(Operator):
    bl_idname = "spacerpro.preset_delete"
    bl_label = "Delete Preset"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        pstate = context.scene.spacerpro_preset_state
        name = pstate.preset_name

        data = presets.load_presets()
        if name not in data:
            self.report({"ERROR"}, f"Preset not found: {name}")
            return {"CANCELLED"}

        del data[name]
        presets.save_presets(data)

        # Move selection to something valid
        names = presets.list_preset_names()
        if names:
            try:
                pstate.preset_name = names[0]
            except Exception:
                pass

        self.report({"INFO"}, f"Deleted preset: {name}")
        return {"FINISHED"}


classes = (
    SPACERPRO_OT_generate,
    SPACERPRO_OT_preset_apply,
    SPACERPRO_OT_preset_save,
    SPACERPRO_OT_preset_delete,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)