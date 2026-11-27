# props.py - Property definitions
#
#   BJG_ShapeParams  : one full set of shape parameters
#   BJG_JointData    : stored on each joint's collection (index, its own shape values, cutout state)
#   BJG_SceneSettings: stored on the scene (edited joint, values for the next new joint, preview toggle)

import bpy
from bpy.props import (BoolProperty, EnumProperty, FloatProperty,
                       FloatVectorProperty, IntProperty, PointerProperty, StringProperty)

from .core import MAX_JOINTS

_SKIP = {"rna_type", "name"}


def _on_cutout_toggle(self, context):
    from . import joint
    joint.sync_cutout(context, self.index)


def _on_preview_toggle(self, context):
    from . import joint
    joint.apply_preview_visibility(context.scene)


class BJG_ShapeParams(bpy.types.PropertyGroup):
    segments: IntProperty(name="Segments", default=16, min=8, max=64)

    # ---- Ball ----
    ball_shape: EnumProperty(name="Ball Shape", default='SPHERE', items=(
        ('SPHERE', "Sphere", ""),
        ('CYLINDER', "Cylinder", ""),
        ('CUBE', "Cube", ""),
    ))
    ball_radius: FloatProperty(name="Radius", default=1.0, min=0.01, unit='LENGTH')
    use_ball_top_scale: BoolProperty(name="Scale Top XY", default=False)
    ball_top_scale: FloatProperty(name="Top Scale", default=1.0, min=0.1, max=3.0)
    use_ball_bottom_scale: BoolProperty(name="Scale Bottom XY", default=False)
    ball_bottom_scale: FloatProperty(name="Bottom Scale", default=1.0, min=0.1, max=3.0)

    # ---- Stem ----
    stem_shape: EnumProperty(name="Stem Shape", default='CYLINDER', items=(
        ('CYLINDER', "Cylinder", ""),
        ('SPHERE', "Sphere", "Ellipsoid stretched along the stem length"),
        ('FLAT_CYLINDER', "Flat Cylinder", "Cylinder with an elliptical cross-section"),
        ('CUBE', "Cube", "Square prism"),
    ))
    stem_radius: FloatProperty(name="Radius", default=0.5, min=0.01, unit='LENGTH')
    stem_length: FloatProperty(name="Length", default=4.0, min=0.1, unit='LENGTH')
    stem_z_offset: FloatProperty(name="Z Offset", default=0.0, unit='LENGTH',
                                 description="Height of the stem top, measured from the ball center")
    stem_flat_ratio: FloatProperty(name="Flatness", default=0.5, min=0.05, max=1.0,
                                   description="Flat Cylinder: Y thickness as a ratio of X")
    use_stem_top_scale: BoolProperty(name="Scale Top XY", default=False)
    stem_top_scale: FloatProperty(name="Top Scale", default=1.0, min=0.1, max=3.0)
    use_stem_bottom_scale: BoolProperty(name="Scale Bottom XY", default=False)
    stem_bottom_scale: FloatProperty(name="Bottom Scale", default=1.0, min=0.1, max=3.0)

    # ---- Clearance ----
    clearance: FloatProperty(
        name="Clearance", default=0.1, min=0.0, soft_max=2.0, precision=3, step=0.1,
        unit='LENGTH',
        description="Added to the cutter size on each axis (added to the diameter, "
                    "so the gap on each side is half of this)")

    # ---- Cutout ----
    cutout_shape: EnumProperty(name="Cutout Shape", default='BOX', items=(
        ('BOX', "Box", ""),
        ('CYLINDER', "Cylinder", "Cylinder along the Y axis"),
    ))
    cutout_sx: FloatProperty(name="X", default=2.0, min=0.01, unit='LENGTH')
    cutout_sy: FloatProperty(name="Y", default=0.6, min=0.01, unit='LENGTH')
    cutout_sz: FloatProperty(name="Z", default=0.6, min=0.01, unit='LENGTH')

    def copy_from(self, other):
        for key in self.bl_rna.properties.keys():
            if key not in _SKIP:
                setattr(self, key, getattr(other, key))

    def signature(self):
        """All values as one string. Compared with the values of the last build to detect
        changes that have not been applied yet."""
        parts = []
        for key in self.bl_rna.properties.keys():
            if key in _SKIP:
                continue
            v = getattr(self, key)
            parts.append(f"{key}={round(v, 6) if isinstance(v, float) else v}")
        return ";".join(parts)

    def reset(self):
        for key in self.bl_rna.properties.keys():
            if key not in _SKIP:
                self.property_unset(key)


class BJG_JointData(bpy.types.PropertyGroup):
    """Stored on a joint's collection. Shape values belong to this joint only."""
    index: IntProperty(default=0)
    params: PointerProperty(type=BJG_ShapeParams)
    use_cutout: BoolProperty(name="Use Cutout", default=False, update=_on_cutout_toggle)
    has_cutout_matrix: BoolProperty(default=False)
    cutout_matrix: FloatVectorProperty(size=16)
    built_signature: StringProperty(default="")  # values used for the last build


class BJG_SceneSettings(bpy.types.PropertyGroup):
    template: PointerProperty(type=BJG_ShapeParams)  # shown when no joint is being edited
    edited_joint: IntProperty(name="Edited Joint", default=0, min=0, max=MAX_JOINTS)
    show_preview: BoolProperty(name="Show Socket Preview", default=True, update=_on_preview_toggle,
                               description="Show or hide the cut previews on targets and the cutter objects")


class BJG_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    show_generate_hint: BoolProperty(
        name="Show hint after generating", default=True,
        description="Show a short hint about Update Preview right after generating a joint")

    def draw(self, context):
        self.layout.prop(self, "show_generate_hint")


def addon_prefs(context):
    """Add-on preferences, or None when the add-on is not enabled as an add-on (e.g. in tests)."""
    addon = context.preferences.addons.get(__package__)
    return addon.preferences if addon is not None else None


classes = (BJG_ShapeParams, BJG_JointData, BJG_SceneSettings, BJG_AddonPreferences)


def register():
    bpy.types.Scene.bjg = PointerProperty(type=BJG_SceneSettings)
    bpy.types.Collection.bjg = PointerProperty(type=BJG_JointData)


def unregister():
    del bpy.types.Collection.bjg
    del bpy.types.Scene.bjg
