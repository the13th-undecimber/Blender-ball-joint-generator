# booleans.py - Adding Boolean previews (non-destructive) and applying them (Apply Stem, Finalize)
#
# Modifier names:
#   Ball        : BJG_Union_Stem        (ball + stem)
#   Ball cutter : BJG_CutterUnion_Stem  (ball cutter + stem cutter)
#   Target      : BJG_Socket_J###       (target - ball cutter)
#                 BJG_Cutout_J###       (target - cutout)
#
# Applying does not use bpy.ops: only the wanted modifiers are enabled, the evaluated result is
# turned into a mesh, and that mesh replaces the object's data.

import bpy

from . import core

MALE_UNION = "BJG_Union_Stem"
CUTTER_UNION = "BJG_CutterUnion_Stem"
TARGET_PREFIXES = ("BJG_Socket_J", "BJG_Cutout_J")


def socket_mod_name(index):
    return f"BJG_Socket_{core.joint_label(index)}"


def cutout_mod_name(index):
    return f"BJG_Cutout_{core.joint_label(index)}"


# ------------------------------------------------------------
# Add
# ------------------------------------------------------------
def set_boolean(obj, name, operand, operation, show=True):
    mod = obj.modifiers.get(name)
    if mod is not None and mod.type != 'BOOLEAN':
        obj.modifiers.remove(mod)
        mod = None
    if mod is None:
        mod = obj.modifiers.new(name, 'BOOLEAN')
    mod.operation = operation
    mod.solver = 'EXACT'
    mod.use_self = False
    mod.use_hole_tolerant = True
    mod.object = operand
    mod.show_viewport = show
    mod.show_render = show
    return mod


def remove_modifier(obj, name):
    mod = obj.modifiers.get(name)
    if mod is not None:
        obj.modifiers.remove(mod)


def is_target(obj):
    return obj.type == 'MESH' and not core.is_generated(obj) and not core.is_backup(obj)


def targets_using(index, include_cutout=True):
    names = {socket_mod_name(index)}
    if include_cutout:
        names.add(cutout_mod_name(index))
    return [o for o in bpy.data.objects
            if is_target(o) and any(m.name in names for m in o.modifiers)]


def attach_to_target(target, index, show):
    """Add this joint's Difference previews to the target. Returns how many were added."""
    count = 0
    ball_cutter = core.part(index, 'BALL_CUTTER')
    if ball_cutter is not None:
        set_boolean(target, socket_mod_name(index), ball_cutter, 'DIFFERENCE', show)
        count += 1
    cutout = core.part(index, 'CUTOUT')
    if cutout is not None:
        set_boolean(target, cutout_mod_name(index), cutout, 'DIFFERENCE', show)
        count += 1
    return count


# ------------------------------------------------------------
# Apply
# ------------------------------------------------------------
def bake_modifiers(context, obj, names):
    """Bake only the modifiers in `names` into the mesh and remove them.
    Other modifiers stay untouched, in stack order. Returns True if anything was baked."""
    names = [n for n in names if n in obj.modifiers]
    if not names:
        return False
    if obj.data.shape_keys is not None:
        raise core.JointError(f"{obj.name} has shape keys and cannot be applied")

    states = {m.name: m.show_viewport for m in obj.modifiers}
    was_hidden = core.is_hidden(obj)
    try:
        for m in obj.modifiers:
            m.show_viewport = m.name in names
        if was_hidden:
            core.set_hidden(obj, False)
        depsgraph = context.evaluated_depsgraph_get()
        depsgraph.update()
        mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
    finally:
        for m in obj.modifiers:
            if m.name in states:
                m.show_viewport = states[m.name]
        if was_hidden:
            core.set_hidden(obj, True)

    for n in names:
        remove_modifier(obj, n)
    core.replace_mesh(obj, mesh)
    return True


def backup_target(scene, target):
    """Before the first Finalize, keep a hidden copy of the target without modifiers."""
    if target.get(core.BACKUP_DONE_KEY, False):
        return
    dup = target.copy()
    dup.data = target.data.copy()
    while dup.modifiers:
        dup.modifiers.remove(dup.modifiers[0])
    dup.name = f"{target.name}_preFinalize"
    dup[core.BACKUP_KEY] = True
    scene.collection.objects.link(dup)
    core.set_hidden(dup, True)
    dup.hide_render = True
    target[core.BACKUP_DONE_KEY] = True


def confirm_male(context, index):
    """Merge the stem into the ball and delete the stem."""
    ball = core.part(index, 'BALL')
    stem = core.part(index, 'STEM')
    if ball is None or stem is None:
        return False
    stem_cutter = core.part(index, 'STEM_CUTTER')
    if stem_cutter is not None and stem_cutter.parent == stem:
        core.reparent_keep_world(stem_cutter, ball)
    bake_modifiers(context, ball, [MALE_UNION])
    core.delete_object(stem)
    return True


def finalize(context, index):
    """Apply this joint's socket to every target that previews it, then delete the cutters.
    Returns the number of targets. Nothing is deleted when there is no target."""
    targets = targets_using(index)
    if not targets:
        return 0
    names = [socket_mod_name(index), cutout_mod_name(index)]
    for tgt in targets:
        backup_target(context.scene, tgt)
        bake_modifiers(context, tgt, names)
    for role in ('STEM_CUTTER', 'BALL_CUTTER', 'CUTOUT'):
        core.delete_object(core.part(index, role))
    return len(targets)
