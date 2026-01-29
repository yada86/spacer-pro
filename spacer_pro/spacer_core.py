import bpy
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, EnumProperty, BoolProperty, PointerProperty

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
    c = base + moff + offset
    return max(0.00, min(c, 0.60))


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

    show_advanced: BoolProperty(name="Advanced", default=False)


classes = (SPACERPRO_Props,)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.spacerpro_props = PointerProperty(type=SPACERPRO_Props)

def unregister():
    del bpy.types.Scene.spacerpro_props
    for c in reversed(classes):
        bpy.utils.unregister_class(c)