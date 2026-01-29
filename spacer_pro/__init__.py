bl_info = {
    "name": "Spacer PRO",
    "author": "Daniel Albrethsen",
    "version": (0, 1, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > Spacer PRO",
    "description": "Parametric spacer generator for functional 3D printing",
    "category": "3D View",
}

import importlib

from . import spacer_core, ops, ui


def _reload_modules():
    importlib.reload(spacer_core)
    importlib.reload(ops)
    importlib.reload(ui)


def register():
    print("SPACER PRO LOADED FROM:", __file__)
    _reload_modules()
    spacer_core.register()
    ops.register()
    ui.register()


def unregister():
    ui.unregister()
    ops.unregister()
    spacer_core.unregister()