# Ball Joint Maker (Blender 4.2+ extension)
#
# Files:
#   core.py      shared helpers: names, tags, collections, deletion, parenting
#   shapes.py    mesh generation for ball / stem / cutters / cutout
#   props.py     properties (per-joint shape values, edited joint, preferences)
#   joint.py     creating joints, Update Preview, cutouts, following the active object
#   booleans.py  adding and applying Boolean modifiers (Apply Stem, Finalize)
#   operators.py button actions
#   ui.py        sidebar panels
#
# Add-on metadata lives in blender_manifest.toml.

import bpy
from bpy.app.handlers import persistent

from . import joint, operators, props, ui

_classes = (*props.classes, *operators.classes, *ui.classes)
_msgbus_owner = object()


def _subscribe():
    """Watch the active object so the edited joint follows the selection."""
    bpy.msgbus.clear_by_owner(_msgbus_owner)
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.LayerObjects, "active"),
        owner=_msgbus_owner,
        args=(),
        notify=joint.follow_active,
    )


@persistent
def _on_load(_dummy):
    _subscribe()  # subscriptions are cleared when a file is loaded


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    props.register()
    _subscribe()
    bpy.app.handlers.load_post.append(_on_load)


def unregister():
    if _on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load)
    bpy.msgbus.clear_by_owner(_msgbus_owner)
    props.unregister()
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
