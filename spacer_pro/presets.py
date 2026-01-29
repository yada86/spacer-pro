import json
import os
import bpy
from bpy.types import PropertyGroup
from bpy.props import StringProperty, EnumProperty


def _presets_dir() -> str:
    base = bpy.utils.user_resource("CONFIG", path="spacer_pro", create=True)
    if not base:
        base = os.path.join(os.path.expanduser("~"), "spacer_pro")
        os.makedirs(base, exist_ok=True)
    return base


def presets_path() -> str:
    return os.path.join(_presets_dir(), "presets.json")


def _default_presets():
    return {
        "PETG Normal (Allround)": {
            "diameter_mode": "OD_ID",
            "od_mm": 20.0,
            "id_mm": 10.0,
            "wall_mm": 2.0,
            "height_mm": 5.0,
            "fit_class": "NORMAL",
            "material": "PETG",
            "clearance_offset": 0.00,
        },
        "PLA Tight": {
            "diameter_mode": "OD_ID",
            "od_mm": 20.0,
            "id_mm": 10.0,
            "wall_mm": 2.0,
            "height_mm": 5.0,
            "fit_class": "TIGHT",
            "material": "PLA",
            "clearance_offset": -0.02,
        },
        "Press-fit Nylon": {
            "diameter_mode": "OD_ID",
            "od_mm": 20.0,
            "id_mm": 10.0,
            "wall_mm": 2.0,
            "height_mm": 5.0,
            "fit_class": "PRESS",
            "material": "NYLON",
            "clearance_offset": 0.00,
        },
    }


def load_presets() -> dict:
    path = presets_path()
    if not os.path.exists(path):
        data = _default_presets()
        save_presets(data)
        return data

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("presets.json must be an object/dict")
        return data
    except Exception as e:
        recovered = _default_presets()
        save_presets(recovered)
        print("Spacer PRO: presets.json invalid; recreated defaults. Error:", e)
        return recovered


def save_presets(data: dict) -> None:
    path = presets_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def list_preset_names() -> list[str]:
    data = load_presets()
    return sorted(list(data.keys()), key=lambda s: s.lower())


def preset_items(self, context):
    names = list_preset_names()
    if not names:
        return [("NONE", "No presets", "No presets available")]
    return [(n, n, "") for n in names]


class SPACERPRO_PresetState(PropertyGroup):
    preset_name: EnumProperty(name="Preset", items=preset_items)
    preset_name_new: StringProperty(name="Name", default="My Preset")


classes = (SPACERPRO_PresetState,)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.spacerpro_preset_state = bpy.props.PointerProperty(type=SPACERPRO_PresetState)
    load_presets()


def unregister():
    del bpy.types.Scene.spacerpro_preset_state
    for c in reversed(classes):
        bpy.utils.unregister_class(c)