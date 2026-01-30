# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
import bmesh
from math import radians, tan
from bpy.types import PropertyGroup
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    PointerProperty,
)

ADDON_TAG = "SPACERPRO"

# Corner keys (fixed order)
CORNERS = ("TI", "TO", "BI", "BO")

CORNER_LABEL = {
    "TI": "Top Inner",
    "TO": "Top Outer",
    "BI": "Bottom Inner",
    "BO": "Bottom Outer",
}

# Mapping -> (side, region)
CORNER_MAP = {
    "TI": ("TOP", "INNER"),
    "TO": ("TOP", "OUTER"),
    "BI": ("BOTTOM", "INNER"),
    "BO": ("BOTTOM", "OUTER"),
}

# Properties per corner: (enable, size, angle)
CORNER_PROPS = {
    "TI": ("ch_ti_on", "ch_ti_size", "ch_ti_angle"),
    "TO": ("ch_to_on", "ch_to_size", "ch_to_angle"),
    "BI": ("ch_bi_on", "ch_bi_size", "ch_bi_angle"),
    "BO": ("ch_bo_on", "ch_bo_size", "ch_bo_angle"),
}


def _first_enabled_corner(props):
    for c in CORNERS:
        on_prop, _, _ = CORNER_PROPS[c]
        if getattr(props, on_prop, False):
            return c
    return "TI"


def _active_corner_valid(props):
    active = getattr(props, "chamfer_active_corner", "TI")
    on_prop, _, _ = CORNER_PROPS.get(active, CORNER_PROPS["TI"])
    if getattr(props, on_prop, False):
        return active
    # move to first enabled
    new_active = _first_enabled_corner(props)
    props.chamfer_active_corner = new_active
    return new_active


def _push_master_to_enabled(props):
    """Copy master values -> every enabled corner."""
    ms = float(props.chamfer_master_size)
    ma = float(props.chamfer_master_angle)
    for c in CORNERS:
        on_prop, sz_prop, an_prop = CORNER_PROPS[c]
        if getattr(props, on_prop, False):
            setattr(props, sz_prop, ms)
            setattr(props, an_prop, ma)


def _pull_master_from_active(props):
    """Copy active corner values -> master fields."""
    active = _active_corner_valid(props)
    _, sz_prop, an_prop = CORNER_PROPS[active]
    props.chamfer_master_size = float(getattr(props, sz_prop, 0.0))
    props.chamfer_master_angle = float(getattr(props, an_prop, 45.0))


def _on_edit_mode_update(self, context):
    # When switching to LINKED: master <- active, then master -> all enabled
    if self.edit_mode == "LINKED":
        _pull_master_from_active(self)
        _push_master_to_enabled(self)
    else:
        _active_corner_valid(self)


def _on_active_corner_update(self, context):
    # In LINKED mode: master should follow active corner (source)
    if self.edit_mode == "LINKED":
        _pull_master_from_active(self)
        _push_master_to_enabled(self)
    else:
        _active_corner_valid(self)


def _on_corner_toggle_update(self, context):
    # Keep active corner valid if user disables it
    _active_corner_valid(self)
    # In LINKED mode, new enabled corners should get master values immediately
    if self.edit_mode == "LINKED":
        _push_master_to_enabled(self)


def _on_master_update(self, context):
    # In LINKED mode: editing master pushes to enabled corners
    if self.edit_mode == "LINKED":
        _push_master_to_enabled(self)


class SPACERPRO_Props(PropertyGroup):
    # Dimensions
    inner_diameter: FloatProperty(
        name="Inner Diameter",
        default=57.10,
        min=0.1,
        subtype="DISTANCE",
        unit="LENGTH",
    )
    outer_diameter: FloatProperty(
        name="Outer Diameter",
        default=73.10,
        min=0.2,
        subtype="DISTANCE",
        unit="LENGTH",
    )
    height: FloatProperty(
        name="Height",
        default=6.0,
        min=0.1,
        subtype="DISTANCE",
        unit="LENGTH",
    )

    # Chamfer global
    chamfer_enable: BoolProperty(name="Chamfer", default=True)

    edit_mode: EnumProperty(
        name="Edit Mode",
        items=[
            ("INDIVIDUAL", "Individual", "Edit only the active corner"),
            ("LINKED", "Linked", "Edit master values applied to all enabled corners"),
        ],
        default="INDIVIDUAL",
        update=_on_edit_mode_update,
    )

    chamfer_active_corner: EnumProperty(
        name="Active Corner",
        items=[
            ("TI", "Top Inner", ""),
            ("TO", "Top Outer", ""),
            ("BI", "Bottom Inner", ""),
            ("BO", "Bottom Outer", ""),
        ],
        default="BI",
        update=_on_active_corner_update,
    )

    # Master values (used in LINKED mode)
    chamfer_master_size: FloatProperty(
        name="Size",
        default=1.0,
        min=0.0,
        subtype="DISTANCE",
        unit="LENGTH",
        update=_on_master_update,
    )
    chamfer_master_angle: FloatProperty(
        name="Angle",
        default=45.0,
        min=1.0,
        max=89.0,
        update=_on_master_update,
    )

    # Per-corner existence + values
    ch_ti_on: BoolProperty(name="Top Inner", default=False, update=_on_corner_toggle_update)
    ch_to_on: BoolProperty(name="Top Outer", default=False, update=_on_corner_toggle_update)
    ch_bi_on: BoolProperty(name="Bottom Inner", default=True, update=_on_corner_toggle_update)
    ch_bo_on: BoolProperty(name="Bottom Outer", default=True, update=_on_corner_toggle_update)

    ch_ti_size: FloatProperty(name="Size", default=1.0, min=0.0, subtype="DISTANCE", unit="LENGTH")
    ch_to_size: FloatProperty(name="Size", default=1.0, min=0.0, subtype="DISTANCE", unit="LENGTH")
    ch_bi_size: FloatProperty(name="Size", default=1.0, min=0.0, subtype="DISTANCE", unit="LENGTH")
    ch_bo_size: FloatProperty(name="Size", default=1.0, min=0.0, subtype="DISTANCE", unit="LENGTH")

    ch_ti_angle: FloatProperty(name="Angle", default=45.0, min=1.0, max=89.0)
    ch_to_angle: FloatProperty(name="Angle", default=45.0, min=1.0, max=89.0)
    ch_bi_angle: FloatProperty(name="Angle", default=45.0, min=1.0, max=89.0)
    ch_bo_angle: FloatProperty(name="Angle", default=45.0, min=1.0, max=89.0)

    # Taper (UI placeholder for later)
    taper_enable: BoolProperty(name="Taper", default=False)
    taper_side: EnumProperty(
        name="Side",
        items=[("TOP", "Top", ""), ("BOTTOM", "Bottom", "")],
        default="TOP",
    )
    taper_region: EnumProperty(
        name="Region",
        items=[("INNER", "Inner", ""), ("OUTER", "Outer", "")],
        default="INNER",
    )
    taper_mode: EnumProperty(
        name="Mode",
        items=[("ANGLE", "Angle", ""), ("HEIGHT", "Height", "")],
        default="ANGLE",
    )
    taper_angle_deg: FloatProperty(name="Angle", default=30.0, min=0.0, max=85.0)
    taper_height: FloatProperty(name="Height", default=2.0, min=0.0, subtype="DISTANCE", unit="LENGTH")

    # Advanced/dev
    show_advanced: BoolProperty(name="Advanced", default=False)
    debug_mode: BoolProperty(name="Debug", default=False)


# ----------------------------
# Geometry (manifold ring + chamfer)
# ----------------------------

def _safe_dims(props):
    od = max(float(props.outer_diameter), 0.2)
    idd = max(float(props.inner_diameter), 0.1)
    if idd >= od:
        idd = max(0.1, od * 0.5)
    h = max(float(props.height), 0.1)
    return idd, od, h


def _copy_bmesh_into(dst: bmesh.types.BMesh, src: bmesh.types.BMesh):
    vmap = {}
    for v in src.verts:
        vmap[v] = dst.verts.new(v.co)
    dst.verts.ensure_lookup_table()

    new_faces = []
    for f in src.faces:
        nf = dst.faces.new([vmap[v] for v in f.verts])
        new_faces.append(nf)
    dst.faces.ensure_lookup_table()
    return new_faces


def _boundary_edges_at_z(bm: bmesh.types.BMesh, z_target: float, eps: float):
    edges = []
    for e in bm.edges:
        if len(e.link_faces) != 1:
            continue
        z1 = e.verts[0].co.z
        z2 = e.verts[1].co.z
        if abs(z1 - z_target) <= eps and abs(z2 - z_target) <= eps:
            edges.append(e)
    return edges


def build_ring_bmesh(inner_d, outer_d, height, segments=128) -> bmesh.types.BMesh:
    bm = bmesh.new()
    half_h = height * 0.5
    eps = max(1e-6, height * 1e-4)

    # Outer tube
    bmesh.ops.create_cone(
        bm,
        cap_ends=False,
        segments=segments,
        radius1=outer_d * 0.5,
        radius2=outer_d * 0.5,
        depth=height,
    )

    # Inner tube copied in + reversed
    bm_inner = bmesh.new()
    bmesh.ops.create_cone(
        bm_inner,
        cap_ends=False,
        segments=segments,
        radius1=inner_d * 0.5,
        radius2=inner_d * 0.5,
        depth=height,
    )
    inner_faces = _copy_bmesh_into(bm, bm_inner)
    bm_inner.free()

    try:
        bmesh.ops.reverse_faces(bm, faces=inner_faces)
    except Exception:
        pass

    bm.normal_update()

    # Bridge rims (top + bottom) => manifold ring
    top_edges = _boundary_edges_at_z(bm, +half_h, eps)
    bot_edges = _boundary_edges_at_z(bm, -half_h, eps)

    if top_edges:
        bmesh.ops.bridge_loops(bm, edges=top_edges)
    if bot_edges:
        bmesh.ops.bridge_loops(bm, edges=bot_edges)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    return bm


def _edges_at_corner(bm, side: str, region: str, height: float, inner_r: float, outer_r: float):
    half_h = height * 0.5
    z_target = half_h if side == "TOP" else -half_h
    r_target = inner_r if region == "INNER" else outer_r

    eps_z = max(1e-6, height * 0.001)
    eps_r = max(1e-6, (outer_r - inner_r) * 0.01)

    edges = []
    for e in bm.edges:
        z_avg = (e.verts[0].co.z + e.verts[1].co.z) * 0.5
        if abs(z_avg - z_target) > eps_z:
            continue

        r1 = (e.verts[0].co.x**2 + e.verts[0].co.y**2) ** 0.5
        r2 = (e.verts[1].co.x**2 + e.verts[1].co.y**2) ** 0.5
        r_avg = (r1 + r2) * 0.5

        if abs(r_avg - r_target) <= eps_r:
            edges.append(e)

    return edges


def _apply_chamfer_corner(bm, side: str, region: str, size: float, angle_deg: float,
                          height: float, inner_d: float, outer_d: float):
    if size <= 0.0:
        return

    inner_r = inner_d * 0.5
    outer_r = outer_d * 0.5

    edges = _edges_at_corner(bm, side, region, height, inner_r, outer_r)
    if not edges:
        return

    res = bmesh.ops.bevel(
        bm,
        geom=edges,
        offset=size,
        offset_type='OFFSET',
        segments=1,
        profile=0.5,
        affect='EDGES',
        clamp_overlap=True,
    )

    new_verts = res.get("verts", [])
    if not new_verts:
        return

    # Visible/usable angle control (approx but stable)
    a = max(1.0, min(89.0, float(angle_deg)))
    factor = tan(radians(a))  # tan(45)=1 => factor 1.0 at 45°

    half_h = height * 0.5
    z_ref = half_h if side == "TOP" else -half_h
    band = max(0.001, size * 2.5)

    for v in new_verts:
        z = v.co.z
        if side == "TOP":
            if not (z_ref - band <= z <= z_ref + 1e-6):
                continue
            d = (z_ref - z)
            v.co.z = z_ref - d * factor
        else:
            if not (z_ref - 1e-6 <= z <= z_ref + band):
                continue
            d = (z - z_ref)
            v.co.z = z_ref + d * factor


def _apply_chamfers(bm, props, inner_d, outer_d, height):
    if not props.chamfer_enable:
        return

    # Always apply to ALL enabled corners.
    for c in CORNERS:
        on_prop, sz_prop, an_prop = CORNER_PROPS[c]
        if not getattr(props, on_prop, False):
            continue

        side, region = CORNER_MAP[c]
        size = float(getattr(props, sz_prop, 0.0))
        ang = float(getattr(props, an_prop, 45.0))
        _apply_chamfer_corner(bm, side, region, size, ang, height, inner_d, outer_d)


def replace_object_mesh(obj: bpy.types.Object, bm: bmesh.types.BMesh, mesh_name="SpacerPRO_Mesh"):
    if obj.type != "MESH":
        obj.data = bpy.data.meshes.new(mesh_name)

    me = obj.data
    if not isinstance(me, bpy.types.Mesh):
        me = bpy.data.meshes.new(mesh_name)
        obj.data = me

    bm.to_mesh(me)
    bm.free()
    me.update(calc_edges=True, calc_edges_loose=True)


def ensure_spacer_object(context, name="Spacer") -> bpy.types.Object:
    me = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, me)
    context.collection.objects.link(obj)
    context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj


def tag_spacer_object(obj: bpy.types.Object):
    obj[ADDON_TAG] = True
    obj["SPACERPRO_VERSION"] = "1.0"


def is_spacer_object(obj: bpy.types.Object) -> bool:
    return bool(obj and obj.type == "MESH" and obj.get(ADDON_TAG) is True)


def rebuild_spacer_object(obj: bpy.types.Object, props):
    inner_d, outer_d, height = _safe_dims(props)

    # Safety: keep active valid; in LINKED keep master pushed
    _active_corner_valid(props)
    if props.edit_mode == "LINKED":
        _push_master_to_enabled(props)

    bm = build_ring_bmesh(inner_d, outer_d, height)

    # Apply features
    _apply_chamfers(bm, props, inner_d, outer_d, height)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    replace_object_mesh(obj, bm)
    tag_spacer_object(obj)


# ----------------------------
# Register
# ----------------------------

_classes = (SPACERPRO_Props,)

def register():
    for c in _classes:
        bpy.utils.register_class(c)

    bpy.types.Scene.spacerpro_props = PointerProperty(type=SPACERPRO_Props)

    bpy.types.Scene.spacerpro_last_object = PointerProperty(
        name="Last Spacer PRO Object",
        type=bpy.types.Object
    )

def unregister():
    if hasattr(bpy.types.Scene, "spacerpro_last_object"):
        del bpy.types.Scene.spacerpro_last_object

    if hasattr(bpy.types.Scene, "spacerpro_props"):
        del bpy.types.Scene.spacerpro_props

    for c in reversed(_classes):
        try:
            bpy.utils.unregister_class(c)
        except Exception:
            pass
