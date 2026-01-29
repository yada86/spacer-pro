import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    FloatProperty,
    EnumProperty,
    BoolProperty,
    PointerProperty,
)

# -------------------------
# Preset math
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
    c = base + moff + offset
    return max(0.00, min(c, 0.60))


def resolve_diameters(mode: str, od_mm: float, id_mm: float, wall_mm: float):
    """Return (resolved_od, resolved_id) based on diameter mode."""
    if mode == "OD_ID":
        return od_mm, id_mm
    elif mode == "OD_WALL":
        # ID = OD - 2*wall
        return od_mm, max(0.0, od_mm - 2.0 * wall_mm)
    elif mode == "ID_WALL":
        # OD = ID + 2*wall
        return id_mm + 2.0 * wall_mm, id_mm
    return od_mm, id_mm


# -------------------------
# Mesh builder
# -------------------------

def build_spacer(od_mm: float, id_mm: float, height_mm: float, clearance: float):
    """Build spacer mesh using boolean difference. Returns the created outer object."""
    final_id = id_mm + clearance

    # Outer cylinder
    bpy.ops.mesh.primitive_cylinder_add(
        radius=od_mm * 0.5,
        depth=height_mm,
        enter_editmode=False,
        align='WORLD',
    )
    outer = bpy.context.active_object
    outer.name = "SpacerPRO_Outer"

    # Inner cutter
    bpy.ops.mesh.primitive_cylinder_add(
        radius=final_id * 0.5,
        depth=height_mm + 0.2,
        enter_editmode=False,
        align='WORLD',
    )
    inner = bpy.context.active_object
    inner.name = "SpacerPRO_Cutter"

    # Boolean
    mod = outer.modifiers.new(name="SPACERPRO_Boolean", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = inner
    mod.solver = 'MANIFOLD'  # Blender 5.x: FLOAT/EXACT/MANIFOLD

    bpy.context.view_layer.objects.active = outer
    bpy.ops.object.modifier_apply(modifier=mod.name)

    # Cleanup
    bpy.data.objects.remove(inner, do_unlink=True)

    return outer


# -------------------------
# Properties
# -------------------------

class SPACERPRO_Props(PropertyGroup):
    # Main geometry
    od_mm: FloatProperty(name="OD (mm)", default=20.0, min=0.1, soft_max=300.0)
    id_mm: FloatProperty(name="ID (mm)", default=10.0, min=0.1, soft_max=300.0)
    height_mm: FloatProperty(name="Height (mm)", default=5.0, min=0.1, soft_max=200.0)

    diameter_mode: EnumProperty(
        name="Diameter Mode",
        items=[
            ("OD_ID", "OD + ID", "Specify outer and inner diameter"),
            ("OD_WALL", "OD + Wall", "Specify outer diameter and wall thickness"),
            ("ID_WALL", "ID + Wall", "Specify inner diameter and wall thickness"),
        ],
        default="OD_ID",
    )

    wall_mm: FloatProperty(
        name="Wall (mm)",
        default=2.0,
        min=0.1,
        soft_max=50.0,
    )

    # Fit/material
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

    # UI
    show_advanced: BoolProperty(name="Advanced", default=False)


# -------------------------
# Register
# -------------------------

classes = (SPACERPRO_Props,)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.spacerpro_props = PointerProperty(type=SPACERPRO_Props)

def unregister():
    del bpy.types.Scene.spacerpro_props
    for c in reversed(classes):
        bpy.utils.unregister_class(c)