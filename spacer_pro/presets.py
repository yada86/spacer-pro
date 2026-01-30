# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
from bpy.types import Operator, PropertyGroup
from bpy.props import BoolProperty, EnumProperty, PointerProperty, StringProperty
from pathlib import Path
import json

ADDON_ID = "spacer_pro"
PRESET_DIRNAME = "presets"


def _preset_root_dir() -> Path:
    base = bpy.utils.user_resource("CONFIG", path="", create=True)
    if not base:
        base = bpy.utils.user_resource("SCRIPTS", path="", create=True)
    root = Path(base) / ADDON_ID / PRESET_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def _sanitize_name(name: str) -> str:
    name = (name or "").strip()
    bad = '<>:"/\\|?*\n\r\t'
    for c in bad:
        name = name.replace(c, "_")
    name = name.strip(" .")
    return name[:64] if name else ""


def _preset_path(preset_name: str) -> Path:
    safe = _sanitize_name(preset_name)
    return _preset_root_dir() / f"{safe}.json"


def _list_presets() -> list[str]:
    root = _preset_root_dir()
    names = [p.stem for p in root.glob("*.json")]
    names.sort(key=lambda s: s.lower())
    return names


def _get_props(scene):
    return getattr(scene, "spacerpro_props", None)


def _pg_to_dict(pg) -> dict:
    data = {}
    if not pg or not hasattr(pg, "bl_rna"):
        return data
    for prop in pg.bl_rna.properties:
        pid = prop.identifier
        if pid in {"rna_type"}:
            continue
        if getattr(prop, "is_readonly", False):
            continue
        try:
            val = getattr(pg, pid)
        except Exception:
            continue
        if isinstance(val, (bool, int, float, str)):
            data[pid] = val
    return data


def _dict_to_pg(data: dict, pg):
    if not pg or not hasattr(pg, "bl_rna"):
        return
    for k, v in (data or {}).items():
        if not hasattr(pg, k):
            continue
        try:
            setattr(pg, k, v)
        except Exception:
            continue


def _enum_presets_items(self, context):
    try:
        names = _list_presets() or []
    except Exception:
        names = []
    items = [("NONE", "None", "No preset selected")]
    items.extend([(n, n, f"Preset: {n}") for n in names])
    return items



class SPACERPRO_PresetState(PropertyGroup):
    preset: EnumProperty(name="Preset", items=_enum_presets_items)
    new_name: StringProperty(name="Name", default="")
    last_error: StringProperty(name="Last Error", default="", options={"HIDDEN"})


class SPACERPRO_OT_PresetApply(Operator):
    bl_idname = "spacerpro.preset_apply"
    bl_label = "Apply Preset"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        sc = context.scene
        st = getattr(sc, "spacerpro_preset_state", None)
        props = _get_props(sc)
        if not st or not props:
            self.report({"ERROR"}, "Preset state or props missing")
            return {"CANCELLED"}

        name = st.preset
        if not name or name == "NONE":
            self.report({"WARNING"}, "No preset selected")
            return {"CANCELLED"}

        path = _preset_path(name)
        if not path.exists():
            self.report({"ERROR"}, f"Preset not found: {name}")
            return {"CANCELLED"}

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            st.last_error = f"Load error: {e}"
            self.report({"ERROR"}, "Failed to load preset JSON")
            return {"CANCELLED"}

        _dict_to_pg(payload.get("settings", {}), props)
        self.report({"INFO"}, f"Applied: {name}")
        return {"FINISHED"}


class SPACERPRO_OT_PresetSave(Operator):
    bl_idname = "spacerpro.preset_save"
    bl_label = "Save Preset"
    bl_options = {"REGISTER", "UNDO"}

    overwrite: BoolProperty(name="Overwrite", default=False)

    def execute(self, context):
        sc = context.scene
        st = getattr(sc, "spacerpro_preset_state", None)
        props = _get_props(sc)
        if not st or not props:
            self.report({"ERROR"}, "Preset state or props missing")
            return {"CANCELLED"}

        name = _sanitize_name(st.new_name)
        if not name:
            self.report({"ERROR"}, "Preset name is empty")
            return {"CANCELLED"}

        path = _preset_path(name)
        if path.exists() and not self.overwrite:
            self.report({"ERROR"}, "Preset exists. Use Overwrite.")
            return {"CANCELLED"}

        payload = {
            "name": name,
            "addon": ADDON_ID,
            "blender": bpy.app.version_string,
            "settings": _pg_to_dict(props),
        }

        try:
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            st.last_error = f"Save error: {e}"
            self.report({"ERROR"}, "Failed to save preset")
            return {"CANCELLED"}

        st.new_name = ""
        try:
            names = _list_presets()
            st.preset = names[0] if names else "NONE"
        except Exception:
            pass

        self.report({"INFO"}, f"Saved: {name}")
        return {"FINISHED"}


class SPACERPRO_OT_PresetDelete(Operator):
    bl_idname = "spacerpro.preset_delete"
    bl_label = "Delete Preset"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        sc = context.scene
        st = getattr(sc, "spacerpro_preset_state", None)
        if not st:
            self.report({"ERROR"}, "Preset state missing")
            return {"CANCELLED"}

        name = st.preset
        if not name or name == "NONE":
            self.report({"WARNING"}, "No preset selected")
            return {"CANCELLED"}

        path = _preset_path(name)
        if not path.exists():
            self.report({"WARNING"}, "Preset file missing")
            return {"CANCELLED"}

        try:
            path.unlink()
        except Exception as e:
            st.last_error = f"Delete error: {e}"
            self.report({"ERROR"}, "Failed to delete preset")
            return {"CANCELLED"}

        try:
            names = _list_presets()
            st.preset = names[0] if names else "NONE"
        except Exception:
            st.preset = "NONE"

        self.report({"INFO"}, f"Deleted: {name}")
        return {"FINISHED"}


def draw_presets_ui(layout, context):
    sc = context.scene
    st = getattr(sc, "spacerpro_preset_state", None)

    box = layout.box()
    box.label(text="Presets")

    if not st:
        row = box.row()
        row.alert = True
        row.label(text="Presets unavailable (register issue)")
        return

    row = box.row(align=True)
    row.prop(st, "preset", text="")
    row.operator("spacerpro.preset_apply", text="Apply", icon="CHECKMARK")

    row = box.row(align=True)
    row.prop(st, "new_name", text="")
    op = row.operator("spacerpro.preset_save", text="Save", icon="FILE_TICK")
    op.overwrite = False

    row = box.row(align=True)
    op2 = row.operator("spacerpro.preset_save", text="Overwrite", icon="FILE_REFRESH")
    op2.overwrite = True
    row.operator("spacerpro.preset_delete", text="Delete", icon="TRASH")


_classes = (
    SPACERPRO_PresetState,
    SPACERPRO_OT_PresetApply,
    SPACERPRO_OT_PresetSave,
    SPACERPRO_OT_PresetDelete,
)

def register():
    for c in _classes:
        bpy.utils.register_class(c)

    bpy.types.Scene.spacerpro_preset_state = PointerProperty(type=SPACERPRO_PresetState)

    # Lazy init happens in UI / operators instead.
    # (Avoid touching bpy.context.scene during register; unstable on reload/startup.)
    return



def unregister():
    if hasattr(bpy.types.Scene, "spacerpro_preset_state"):
        del bpy.types.Scene.spacerpro_preset_state

    for c in reversed(_classes):
        try:
            bpy.utils.unregister_class(c)
        except Exception:
            pass
