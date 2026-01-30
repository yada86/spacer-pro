# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
from bpy.types import Operator
from . import spacer_core


def _get_props(context):
    return getattr(context.scene, "spacerpro_props", None)


def _active_or_last_spacer(context):
    sc = context.scene
    obj = context.object
    if not spacer_core.is_spacer_object(obj):
        obj = getattr(sc, "spacerpro_last_object", None)
    return obj


class SPACERPRO_OT_Generate(Operator):
    bl_idname = "spacerpro.generate"
    bl_label = "Create Spacer"
    bl_description = "Create a new Spacer PRO object"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = _get_props(context)
        if not props:
            self.report({"ERROR"}, "Spacer PRO props missing")
            return {"CANCELLED"}

        obj = spacer_core.ensure_spacer_object(context, name="Spacer")
        spacer_core.rebuild_spacer_object(obj, props)

        context.scene.spacerpro_last_object = obj
        self.report({"INFO"}, "Spacer created")
        return {"FINISHED"}


class SPACERPRO_OT_Update(Operator):
    bl_idname = "spacerpro.update"
    bl_label = "Update Spacer"
    bl_description = "Update selected Spacer PRO object (or last created one)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = _get_props(context)
        if not props:
            self.report({"ERROR"}, "Spacer PRO props missing")
            return {"CANCELLED"}

        obj = _active_or_last_spacer(context)
        if not spacer_core.is_spacer_object(obj):
            self.report({"ERROR"}, "No Spacer PRO object selected (and no last object stored)")
            return {"CANCELLED"}

        spacer_core.rebuild_spacer_object(obj, props)
        context.scene.spacerpro_last_object = obj

        self.report({"INFO"}, "Spacer updated")
        return {"FINISHED"}


class SPACERPRO_OT_ReloadScripts(Operator):
    bl_idname = "spacerpro.reload_scripts"
    bl_label = "Reload Scripts"
    bl_description = "Developer: Reload Blender scripts"

    def execute(self, context):
        bpy.ops.script.reload()
        return {"FINISHED"}


_classes = (
    SPACERPRO_OT_Generate,
    SPACERPRO_OT_Update,
    SPACERPRO_OT_ReloadScripts,
)

def register():
    for c in _classes:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(_classes):
        try:
            bpy.utils.unregister_class(c)
        except Exception:
            pass
