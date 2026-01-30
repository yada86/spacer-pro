# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
import bmesh
from math import radians, tan
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, EnumProperty, FloatProperty, PointerProperty

ADDON_TAG = "SPACERPRO"
CORNERS = ("TI", "TO", "BI", "BO")

CORNER_MAP = {
    "TI": ("TOP", "INNER"),
    "TO": ("TOP", "OUTER"),
    "BI": ("BOTTOM", "INNER"),
    "BO": ("BOTTOM", "OUTER"),
}

CH_CORNER_PROPS = {
    "TI": ("ch_ti_on", "ch_ti_size", "ch_ti_angle"),
    "TO": ("ch_to_on", "ch_to_size", "ch_to_angle"),
    "BI": ("ch_bi_on", "ch_bi_size", "ch_bi_angle"),
    "BO": ("ch_bo_on", "ch_bo_size", "ch_bo_angle"),
}

TP_CORNER_PROPS = {
    "TI": ("tp_ti_on", "tp_ti_amount", "tp_ti_depth", "tp_ti_angle"),
    "TO": ("tp_to_on", "tp_to_amount", "tp_to_depth", "tp_to_angle"),
    "BI": ("tp_bi_on", "tp_bi_amount", "tp_bi_depth", "tp_bi_angle"),
    "BO": ("tp_bo_on", "tp_bo_amount", "tp_bo_depth", "tp_bo_angle"),
}


def _first_enabled_corner(props, corner_props_map, default="TI"):
    for c in CORNERS:
        on_prop = corner_props_map[c][0]
        if getattr(props, on_prop, False):
            return c
    return default


# ----------------------------
# Chamfer sync
# ----------------------------

def _ch_active_valid(props):
    active = getattr(props, "chamfer_active_corner", "TI")
    on_prop = CH_CORNER_PROPS.get(active, CH_CORNER_PROPS["TI"])[0]
    if getattr(props, on_prop, False):
        return active
    new_active = _first_enabled_corner(props, CH_CORNER_PROPS, default="TI")
    props.chamfer_active_corner = new_active
    return new_active


def _ch_pull_master_from_active(props):
    active = _ch_active_valid(props)
    _, sz_prop, an_prop = CH_CORNER_PROPS[active]
    props.chamfer_master_size = float(getattr(props, sz_prop, 0.0))
    props.chamfer_master_angle = float(getattr(props, an_prop, 45.0))


def _ch_push_master_to_enabled(props):
    ms = float(props.chamfer_master_size)
    ma = float(props.chamfer_master_angle)
    for c in CORNERS:
        on_prop, sz_prop, an_prop = CH_CORNER_PROPS[c]
        if getattr(props, on_prop, False):
            setattr(props, sz_prop, ms)
            setattr(props, an_prop, ma)


def _on_ch_edit_mode_update(self, _context):
    if self.edit_mode == "LINKED":
        _ch_pull_master_from_active(self)
        _ch_push_master_to_enabled(self)
    else:
        _ch_active_valid(self)


def _on_ch_active_corner_update(self, _context):
    if self.edit_mode == "LINKED":
        _ch_pull_master_from_active(self)
        _ch_push_master_to_enabled(self)
    else:
        _ch_active_valid(self)


def _on_ch_corner_toggle_update(self, _context):
    _ch_active_valid(self)
    if self.edit_mode == "LINKED":
        _ch_push_master_to_enabled(self)


def _on_ch_master_update(self, _context):
    if self.edit_mode == "LINKED":
        _ch_push_master_to_enabled(self)


# ----------------------------
# Taper sync (Amount + Depth + Angle)
# ----------------------------

def _tp_active_valid(props):
    active = getattr(props, "taper_active_corner", "TI")
    on_prop = TP_CORNER_PROPS.get(active, TP_CORNER_PROPS["TI"])[0]
    if getattr(props, on_prop, False):
        return active
    new_active = _first_enabled_corner(props, TP_CORNER_PROPS, default="TI")
    props.taper_active_corner = new_active
    return new_active


def _tp_pull_master_from_active(props):
    active = _tp_active_valid(props)
    _, amt_prop, dep_prop, ang_prop = TP_CORNER_PROPS[active]
    props.taper_master_amount = float(getattr(props, amt_prop, 0.5))
    props.taper_master_depth = float(getattr(props, dep_prop, 2.0))
    props.taper_master_angle = float(getattr(props, ang_prop, 10.0))


def _tp_push_master_to_enabled(props):
    ma = float(props.taper_master_amount)
    md = float(props.taper_master_depth)
    ang = float(props.taper_master_angle)
    for c in CORNERS:
        on_prop, amt_prop, dep_prop, ang_prop = TP_CORNER_PROPS[c]
        if getattr(props, on_prop, False):
            setattr(props, amt_prop, ma)
            setattr(props, dep_prop, md)
            setattr(props, ang_prop, ang)


def _on_tp_edit_mode_update(self, _context):
    if self.taper_edit_mode == "LINKED":
        _tp_pull_master_from_active(self)
        _tp_push_master_to_enabled(self)
    else:
        _tp_active_valid(self)


def _on_tp_active_corner_update(self, _context):
    if self.taper_edit_mode == "LINKED":
        _tp_pull_master_from_active(self)
        _tp_push_master_to_enabled(self)
    else:
        _tp_active_valid(self)


def _on_tp_corner_toggle_update(self, _context):
    _tp_active_valid(self)
    if self.taper_edit_mode == "LINKED":
        _tp_push_master_to_enabled(self)


def _on_tp_master_update(self, _context):
    if self.taper_edit_mode == "LINKED":
        _tp_push_master_to_enabled(self)


def _on_tp_mode_update(self, _context):
    if self.taper_edit_mode == "LINKED":
        _tp_push_master_to_enabled(self)


class SPACERPRO_Props(PropertyGroup):
    # Dimensions
    inner_diameter: FloatProperty(name="Inner Diameter", default=57.10, min=0.1, subtype="DISTANCE", unit="LENGTH")
    outer_diameter: FloatProperty(name="Outer Diameter", default=73.10, min=0.2, subtype="DISTANCE", unit="LENGTH")
    height: FloatProperty(name="Height", default=6.0, min=0.1, subtype="DISTANCE", unit="LENGTH")

    # Chamfer
    chamfer_enable: BoolProperty(name="Chamfer", default=True)

    edit_mode: EnumProperty(
        name="Edit Mode",
        items=[("INDIVIDUAL", "Individual", ""), ("LINKED", "Linked", "")],
        default="INDIVIDUAL",
        update=_on_ch_edit_mode_update,
    )

    chamfer_active_corner: EnumProperty(
        name="Active Corner",
        items=[("TI", "Top Inner", ""), ("TO", "Top Outer", ""), ("BI", "Bottom Inner", ""), ("BO", "Bottom Outer", "")],
        default="BI",
        update=_on_ch_active_corner_update,
    )

    chamfer_master_size: FloatProperty(
        name="Size", default=1.0, min=0.0, subtype="DISTANCE", unit="LENGTH", update=_on_ch_master_update
    )
    chamfer_master_angle: FloatProperty(name="Angle", default=45.0, min=1.0, max=89.0, update=_on_ch_master_update)

    ch_ti_on: BoolProperty(name="Top Inner", default=False, update=_on_ch_corner_toggle_update)
    ch_to_on: BoolProperty(name="Top Outer", default=False, update=_on_ch_corner_toggle_update)
    ch_bi_on: BoolProperty(name="Bottom Inner", default=True, update=_on_ch_corner_toggle_update)
    ch_bo_on: BoolProperty(name="Bottom Outer", default=True, update=_on_ch_corner_toggle_update)

    ch_ti_size: FloatProperty(name="Size", default=1.0, min=0.0, subtype="DISTANCE", unit="LENGTH")
    ch_to_size: FloatProperty(name="Size", default=1.0, min=0.0, subtype="DISTANCE", unit="LENGTH")
    ch_bi_size: FloatProperty(name="Size", default=1.0, min=0.0, subtype="DISTANCE", unit="LENGTH")
    ch_bo_size: FloatProperty(name="Size", default=1.0, min=0.0, subtype="DISTANCE", unit="LENGTH")

    ch_ti_angle: FloatProperty(name="Angle", default=45.0, min=1.0, max=89.0)
    ch_to_angle: FloatProperty(name="Angle", default=45.0, min=1.0, max=89.0)
    ch_bi_angle: FloatProperty(name="Angle", default=45.0, min=1.0, max=89.0)
    ch_bo_angle: FloatProperty(name="Angle", default=45.0, min=1.0, max=89.0)

    # Taper
    taper_enable: BoolProperty(name="Taper", default=False)

    taper_mode: EnumProperty(
        name="Mode",
        items=[("ANGLE", "Angle", ""), ("AMOUNT", "Amount", "")],
        default="ANGLE",
        update=_on_tp_mode_update,
    )

    taper_edit_mode: EnumProperty(
        name="Edit Mode",
        items=[("INDIVIDUAL", "Individual", ""), ("LINKED", "Linked", "")],
        default="INDIVIDUAL",
        update=_on_tp_edit_mode_update,
    )

    taper_active_corner: EnumProperty(
        name="Active Corner",
        items=[("TI", "Top Inner", ""), ("TO", "Top Outer", ""), ("BI", "Bottom Inner", ""), ("BO", "Bottom Outer", "")],
        default="BI",
        update=_on_tp_active_corner_update,
    )

    taper_master_amount: FloatProperty(name="Amount", default=0.5, min=0.0, subtype="DISTANCE", unit="LENGTH", update=_on_tp_master_update)
    taper_master_depth: FloatProperty(name="Depth", default=2.0, min=0.01, subtype="DISTANCE", unit="LENGTH", update=_on_tp_master_update)
    taper_master_angle: FloatProperty(name="Angle", default=10.0, min=0.0, max=85.0, update=_on_tp_master_update)

    tp_ti_on: BoolProperty(name="Top Inner", default=False, update=_on_tp_corner_toggle_update)
    tp_to_on: BoolProperty(name="Top Outer", default=False, update=_on_tp_corner_toggle_update)
    tp_bi_on: BoolProperty(name="Bottom Inner", default=False, update=_on_tp_corner_toggle_update)
    tp_bo_on: BoolProperty(name="Bottom Outer", default=False, update=_on_tp_corner_toggle_update)

    tp_ti_amount: FloatProperty(name="Amount", default=0.5, min=0.0, subtype="DISTANCE", unit="LENGTH")
    tp_to_amount: FloatProperty(name="Amount", default=0.5, min=0.0, subtype="DISTANCE", unit="LENGTH")
    tp_bi_amount: FloatProperty(name="Amount", default=0.5, min=0.0, subtype="DISTANCE", unit="LENGTH")
    tp_bo_amount: FloatProperty(name="Amount", default=0.5, min=0.0, subtype="DISTANCE", unit="LENGTH")

    tp_ti_depth: FloatProperty(name="Depth", default=2.0, min=0.01, subtype="DISTANCE", unit="LENGTH")
    tp_to_depth: FloatProperty(name="Depth", default=2.0, min=0.01, subtype="DISTANCE", unit="LENGTH")
    tp_bi_depth: FloatProperty(name="Depth", default=2.0, min=0.01, subtype="DISTANCE", unit="LENGTH")
    tp_bo_depth: FloatProperty(name="Depth", default=2.0, min=0.01, subtype="DISTANCE", unit="LENGTH")

    tp_ti_angle: FloatProperty(name="Angle", default=10.0, min=0.0, max=85.0)
    tp_to_angle: FloatProperty(name="Angle", default=10.0, min=0.0, max=85.0)
    tp_bi_angle: FloatProperty(name="Angle", default=10.0, min=0.0, max=85.0)
    tp_bo_angle: FloatProperty(name="Angle", default=10.0, min=0.0, max=85.0)

    # Advanced
    show_advanced: BoolProperty(name="Advanced", default=False)
    debug_mode: BoolProperty(name="Debug", default=False)


# ----------------------------
# Geometry
# ----------------------------

def _safe_dims(props):
    od = max(float(props.outer_diameter), 0.2)
    idd = max(float(props.inner_diameter), 0.1)
    if idd >= od:
        idd = max(0.1, od * 0.5)
    h = max(float(props.height), 0.1)
    return idd, od, h


def _boundary_edges_at_z(bm, z_target, eps):
    edges = []
    for e in bm.edges:
        if len(e.link_faces) != 1:
            continue
        z1 = e.verts[0].co.z
        z2 = e.verts[1].co.z
        if abs(z1 - z_target) <= eps and abs(z2 - z_target) <= eps:
            edges.append(e)
    return edges


def build_ring_bmesh(inner_d, outer_d, height, segments=128):
    bm = bmesh.new()
    half_h = height * 0.5
    eps = max(1e-6, height * 1e-4)

    # Outer cylinder (open)
    bmesh.ops.create_cone(
        bm, cap_ends=False, segments=segments,
        radius1=outer_d * 0.5, radius2=outer_d * 0.5, depth=height
    )

    # Inner cylinder (open)
    bm_inner = bmesh.new()
    bmesh.ops.create_cone(
        bm_inner, cap_ends=False, segments=segments,
        radius1=inner_d * 0.5, radius2=inner_d * 0.5, depth=height
    )

    # Copy inner verts/faces into bm
    vmap = {}
    for v in bm_inner.verts:
        vmap[v] = bm.verts.new(v.co)
    bm.verts.ensure_lookup_table()

    inner_faces = []
    for f in bm_inner.faces:
        inner_faces.append(bm.faces.new([vmap[v] for v in f.verts]))
    bm.faces.ensure_lookup_table()
    bm_inner.free()

    # Reverse inner faces normals
    try:
        bmesh.ops.reverse_faces(bm, faces=inner_faces)
    except Exception:
        pass

    bm.normal_update()

    # Bridge top and bottom boundaries to make manifold ring
    top_edges = _boundary_edges_at_z(bm, +half_h, eps)
    bot_edges = _boundary_edges_at_z(bm, -half_h, eps)

    if top_edges:
        bmesh.ops.bridge_loops(bm, edges=top_edges)
    if bot_edges:
        bmesh.ops.bridge_loops(bm, edges=bot_edges)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def _edges_at_corner(bm, side, region, height, inner_r, outer_r):
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


def _apply_chamfer_corner(bm, side, region, size, angle_deg, height, inner_d, outer_d):
    if size <= 0.0:
        return

    inner_r = inner_d * 0.5
    outer_r = outer_d * 0.5

    edges = _edges_at_corner(bm, side, region, height, inner_r, outer_r)
    if not edges:
        return

    res = bmesh.ops.bevel(
        bm, geom=edges,
        offset=size, offset_type='OFFSET',
        segments=1, profile=0.5,
        affect='EDGES', clamp_overlap=True,
    )

    new_verts = res.get("verts", [])
    if not new_verts:
        return

    a = max(1.0, min(89.0, float(angle_deg)))
    factor = tan(radians(a))  # 45° => 1.0

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
    for c in CORNERS:
        on_prop, sz_prop, an_prop = CH_CORNER_PROPS[c]
        if not getattr(props, on_prop, False):
            continue
        side, region = CORNER_MAP[c]
        size = float(getattr(props, sz_prop, 0.0))
        ang = float(getattr(props, an_prop, 45.0))
        _apply_chamfer_corner(bm, side, region, size, ang, height, inner_d, outer_d)


def _apply_tapers(bm, props, inner_d, outer_d, height):
    if not getattr(props, "taper_enable", False):
        return

    inner_r = inner_d * 0.5
    outer_r = outer_d * 0.5
    half_h = height * 0.5

    thickness = max(outer_r - inner_r, 1e-6)
    rad_band = max(thickness * 0.25, 0.2)  # influence around target radius

    def z_weight(z, side, depth):
        depth = max(0.0001, float(depth))
        if side == "TOP":
            t = (half_h - z) / depth
        else:
            t = (z - (-half_h)) / depth
        t = max(0.0, min(1.0, t))
        return 1.0 - t  # rim=1, inside=0

    def r_weight(r, region):
        target = inner_r if region == "INNER" else outer_r
        d = abs(r - target)
        w = 1.0 - max(0.0, min(1.0, d / rad_band))
        return w

    mode = getattr(props, "taper_mode", "ANGLE")

    for c in CORNERS:
        on_prop, amt_prop, dep_prop, ang_prop = TP_CORNER_PROPS[c]
        if not getattr(props, on_prop, False):
            continue

        side, region = CORNER_MAP[c]

        depth = float(getattr(props, dep_prop, 2.0))
        depth = max(0.01, min(depth, height))

        if mode == "ANGLE":
            ang = float(getattr(props, ang_prop, 10.0))
            ang = max(0.0, min(85.0, ang))
            delta_r = tan(radians(ang)) * depth
        else:
            delta_r = float(getattr(props, amt_prop, 0.0))

        if abs(delta_r) <= 1e-9:
            continue

        sign = -1.0 if region == "INNER" else 1.0

        for v in bm.verts:
            z = v.co.z
            wZ = z_weight(z, side, depth)
            if wZ <= 0.0:
                continue

            x, y = v.co.x, v.co.y
            r = (x * x + y * y) ** 0.5
            if r <= 1e-9:
                continue

            wR = r_weight(r, region)
            if wR <= 0.0:
                continue

            w = wZ * wR
            new_r = r + sign * (delta_r * w)
            scale = new_r / r

            v.co.x *= scale
            v.co.y *= scale


def replace_object_mesh(obj, bm, mesh_name="SpacerPRO_Mesh"):
    if obj.type != "MESH":
        obj.data = bpy.data.meshes.new(mesh_name)

    me = obj.data
    if not isinstance(me, bpy.types.Mesh):
        me = bpy.data.meshes.new(mesh_name)
        obj.data = me

    bm.to_mesh(me)
    bm.free()
    me.update(calc_edges=True, calc_edges_loose=True)


def ensure_spacer_object(context, name="Spacer"):
    me = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, me)
    context.collection.objects.link(obj)
    context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj


def tag_spacer_object(obj):
    obj[ADDON_TAG] = True
    obj["SPACERPRO_VERSION"] = "1.0"


def is_spacer_object(obj):
    return bool(obj and obj.type == "MESH" and obj.get(ADDON_TAG) is True)


def rebuild_spacer_object(obj, props):
    inner_d, outer_d, height = _safe_dims(props)

    _ch_active_valid(props)
    if props.edit_mode == "LINKED":
        _ch_push_master_to_enabled(props)

    _tp_active_valid(props)
    if props.taper_edit_mode == "LINKED":
        _tp_push_master_to_enabled(props)

    bm = build_ring_bmesh(inner_d, outer_d, height)

    _apply_chamfers(bm, props, inner_d, outer_d, height)
    _apply_tapers(bm, props, inner_d, outer_d, height)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    replace_object_mesh(obj, bm)
    tag_spacer_object(obj)


_classes = (SPACERPRO_Props,)


def register():
    for c in _classes:
        bpy.utils.register_class(c)

    bpy.types.Scene.spacerpro_props = PointerProperty(type=SPACERPRO_Props)
    bpy.types.Scene.spacerpro_last_object = PointerProperty(name="Last Spacer PRO Object", type=bpy.types.Object)


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
