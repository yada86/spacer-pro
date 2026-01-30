# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
import bmesh
from bpy.types import PropertyGroup
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    PointerProperty,
)

ADDON_TAG = "SPACERPRO"


# ----------------------------
# Properties (Scene.spacerpro_props)
# ----------------------------

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

    # Chamfer controls (UI-ready)
    chamfer_enable: BoolProperty(name="Chamfer", default=True)
    chamfer_side: bpy.props.EnumProperty(
        name="Side",
        items=[("TOP", "Top", ""), ("BOTTOM", "Bottom", "")],
        default="BOTTOM",
    )
    chamfer_region: bpy.props.EnumProperty(
        name="Region",
        items=[("INNER", "Inner", ""), ("OUTER", "Outer", "")],
        default="INNER",
    )
    chamfer_size: FloatProperty(
        name="Size",
        default=1.0,
        min=0.0,
        subtype="DISTANCE",
        unit="LENGTH",
    )
    chamfer_angle_deg: FloatProperty(
        name="Angle",
        default=45.0,
        min=1.0,
        max=89.0,
        subtype="ANGLE",
        unit="ROTATION",
        description="UI angle in degrees (geometry hook later)",
    )

    # Taper controls (UI-ready)
    taper_enable: BoolProperty(name="Taper", default=False)
    taper_side: bpy.props.EnumProperty(
        name="Side",
        items=[("TOP", "Top", ""), ("BOTTOM", "Bottom", "")],
        default="TOP",
    )
    taper_region: bpy.props.EnumProperty(
        name="Region",
        items=[("INNER", "Inner", ""), ("OUTER", "Outer", "")],
        default="INNER",
    )
    taper_mode: bpy.props.EnumProperty(
        name="Mode",
        items=[("ANGLE", "Angle", ""), ("HEIGHT", "Height", "")],
        default="ANGLE",
    )
    taper_angle_deg: FloatProperty(
        name="Angle",
        default=30.0,
        min=0.0,
        max=85.0,
        subtype="ANGLE",
        unit="ROTATION",
        description="UI angle in degrees (geometry hook later)",
    )
    taper_height: FloatProperty(
        name="Height",
        default=2.0,
        min=0.0,
        subtype="DISTANCE",
        unit="LENGTH",
    )

    # Advanced/dev
    show_advanced: BoolProperty(name="Advanced", default=False)
    debug_mode: BoolProperty(name="Debug", default=False)


# ----------------------------
# Core geometry (MANIFOLD ring)
# ----------------------------

def _safe_dims(props):
    od = max(float(props.outer_diameter), 0.2)
    idd = max(float(props.inner_diameter), 0.1)
    if idd >= od:
        idd = max(0.1, od * 0.5)
    h = max(float(props.height), 0.1)
    return idd, od, h


def _copy_bmesh_into(dst: bmesh.types.BMesh, src: bmesh.types.BMesh):
    """Copy verts/faces from src into dst. Returns list of newly created faces."""
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
    """
    Return boundary edges (edges with 1 linked face) whose BOTH verts are near z_target.
    Works well for open cylinder rims.
    """
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
    """
    Build a single, closed, manifold ring:
      - outer tube (no caps)
      - inner tube (no caps)
      - bridge top rim outer<->inner
      - bridge bottom rim outer<->inner
    """
    bm = bmesh.new()
    half_h = height * 0.5
    eps = max(1e-6, height * 1e-4)

    # Outer tube (no caps)
    bmesh.ops.create_cone(
        bm,
        cap_ends=False,
        segments=segments,
        radius1=outer_d * 0.5,
        radius2=outer_d * 0.5,
        depth=height,
    )
    bm.normal_update()

    # Inner tube (no caps) in a temp bmesh, then copy in
    bm_inner = bmesh.new()
    bmesh.ops.create_cone(
        bm_inner,
        cap_ends=False,
        segments=segments,
        radius1=inner_d * 0.5,
        radius2=inner_d * 0.5,
        depth=height,
    )
    new_inner_faces = _copy_bmesh_into(bm, bm_inner)
    bm_inner.free()

    # Flip inner faces so normals point inward (important for consistent manifold)
    try:
        bmesh.ops.reverse_faces(bm, faces=new_inner_faces)
    except Exception:
        pass

    bm.normal_update()

    # Find boundary rims
    top_z = +half_h
    bot_z = -half_h

    top_edges = _boundary_edges_at_z(bm, top_z, eps)
    bot_edges = _boundary_edges_at_z(bm, bot_z, eps)

    if not top_edges or not bot_edges:
        # Fallback: if eps is too tight (shouldn't happen), widen it a bit
        top_edges = _boundary_edges_at_z(bm, top_z, eps * 10.0)
        bot_edges = _boundary_edges_at_z(bm, bot_z, eps * 10.0)

    # Bridge top and bottom between the two loops (outer+inner are both in the list)
    # bridge_loops will connect two edge loops when given edges from both loops.
    if top_edges:
        bmesh.ops.bridge_loops(bm, edges=top_edges)
    if bot_edges:
        bmesh.ops.bridge_loops(bm, edges=bot_edges)

    # Clean up
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    return bm


def replace_object_mesh(obj: bpy.types.Object, bm: bmesh.types.BMesh, mesh_name="SpacerPRO_Mesh"):
    # Ensure the OBJECT is a mesh object
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
    bm = build_ring_bmesh(inner_d, outer_d, height)
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
