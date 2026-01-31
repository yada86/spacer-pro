# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
from bpy.types import Operator
from bpy.props import EnumProperty, StringProperty

from . import spacer_core


class SPACERPRO_OT_SetActiveCorner(Operator):
    """Set active edit target corner for Chamfer/Taper"""
    bl_idname = "spacerpro.set_active_corner"
    bl_label = "Set Active Corner"
    bl_description = "Select the active chamfer/taper corner for editing."
    bl_options = {"INTERNAL"}

    corner: StringProperty()
    domain: EnumProperty(
        items=[("CHAMFER", "Chamfer", ""), ("TAPER", "Taper", "")],
        default="CHAMFER",
    )

    def execute(self, context):
        props = context.scene.spacerpro_props
        if self.domain == "CHAMFER":
            props.chamfer_active_corner = self.corner
        else:
            props.taper_active_corner = self.corner
        return {"FINISHED"}


class SPACERPRO_OT_Generate(Operator):
    bl_idname = "spacerpro.generate"
    bl_label = "Create Spacer"
    bl_description = "Create a new Spacer PRO object from current settings."
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        sc = context.scene
        props = getattr(sc, "spacerpro_props", None)
        if not props:
            self.report({"ERROR"}, "Spacer PRO props missing")
            return {"CANCELLED"}

        obj = spacer_core.ensure_spacer_object(context, name="Spacer")
        spacer_core.rebuild_spacer_object(obj, props)
        sc.spacerpro_last_object = obj
        return {"FINISHED"}


class SPACERPRO_OT_Update(Operator):
    bl_idname = "spacerpro.update"
    bl_label = "Update"
    bl_description = "Rebuild the last Spacer PRO object with current settings."
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        sc = context.scene
        props = getattr(sc, "spacerpro_props", None)
        if not props:
            self.report({"ERROR"}, "Spacer PRO props missing")
            return {"CANCELLED"}

        obj = getattr(sc, "spacerpro_last_object", None)

        if not obj or not spacer_core.is_spacer_object(obj):
            # fallback: active object if it's ours
            ao = context.view_layer.objects.active
            if spacer_core.is_spacer_object(ao):
                obj = ao
                sc.spacerpro_last_object = obj
            else:
                self.report({"WARNING"}, "No last Spacer PRO object. Use Create Spacer first.")
                return {"CANCELLED"}

        spacer_core.rebuild_spacer_object(obj, props)
        return {"FINISHED"}


classes = (
    SPACERPRO_OT_SetActiveCorner,
    SPACERPRO_OT_Generate,
    SPACERPRO_OT_Update,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        try:
            bpy.utils.unregister_class(c)
        except Exception:
            pass
