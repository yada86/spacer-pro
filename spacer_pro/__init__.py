# SPDX-License-Identifier: GPL-3.0-or-later

bl_info = {
    "name": "Spacer PRO",
    "author": "Daniel Albrethsen",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > Spacer PRO",
    "description": "Parametric spacer generator with pro update workflow + presets",
    "category": "3D View",
}

def register():
    # Lazy imports to avoid reload weirdness
    from . import spacer_core, presets, ops, ui
    spacer_core.register()
    presets.register()
    ops.register()
    ui.register()

def unregister():
    from . import ui, ops, presets, spacer_core
    ui.unregister()
    ops.unregister()
    presets.unregister()
    spacer_core.unregister()
