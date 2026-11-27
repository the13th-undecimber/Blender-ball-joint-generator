# joint.py - Creating joints, updating previews, cutouts and the edited joint
#
# Parts (parent / child):
#   Ball ─┬─ Stem ── StemCutter
#         ├─ BallCutter
#         └─ Cutout
#
# How values are kept:
#   Each joint has its own shape values, stored on its collection. Joints never share values.
#   The UI shows and edits the values of the edited joint; with no edited joint it shows the
#   values for the next new joint. A new joint copies the values on screen when it is created
#   and is independent from then on.
#   Position and rotation live on the objects, not in the values. Update Preview only replaces
#   mesh data, so transforms, parenting and target modifiers stay as they are.

import bpy
from mathutils import Matrix

from . import booleans, core, shapes


# ------------------------------------------------------------
# Edited joint and displayed values
# ------------------------------------------------------------
def edited_index(scene):
    """Index of the edited joint, or None if its ball no longer exists."""
    idx = scene.bjg.edited_joint
    if idx and core.part(idx, 'BALL') is not None:
        return idx
    return None


def params_for(index):
    coll = core.joint_collection(index)
    return coll.bjg.params if coll is not None else None


def joint_data(index):
    coll = core.joint_collection(index)
    return coll.bjg if coll is not None else None


def displayed_params(scene):
    idx = edited_index(scene)
    if idx is not None:
        p = params_for(idx)
        if p is not None:
            return p
    return scene.bjg.template


def mark_built(index):
    data = joint_data(index)
    if data is not None:
        data.built_signature = data.params.signature()


def is_stale(index):
    """True when values changed since the last build (never for joints whose stem was applied)."""
    data = joint_data(index)
    if data is None or core.part(index, 'STEM') is None:
        return False
    return data.built_signature != data.params.signature()


def select_joint(context, index):
    """Make the joint the edited one and select its ball (unless the ball is hidden)."""
    context.scene.bjg.edited_joint = index
    ball = core.part(index, 'BALL')
    if ball is not None and not core.is_hidden(ball):
        for obj in context.selected_objects:
            obj.select_set(False)
        ball.select_set(True)
        context.view_layer.objects.active = ball


def follow_active():
    """When the active object changes, make its joint the edited joint.
    Objects that do not belong to a joint (such as targets) leave it unchanged."""
    context = bpy.context
    scene = getattr(context, "scene", None)
    view_layer = getattr(context, "view_layer", None)
    if scene is None or view_layer is None or not hasattr(scene, "bjg"):
        return
    idx = core.index_of(view_layer.objects.active)
    if idx is not None and scene.bjg.edited_joint != idx:
        scene.bjg.edited_joint = idx


def joint_state(index):
    """Status text for the UI."""
    if core.part(index, 'STEM') is None:
        state = "stem applied"
    else:
        state = "editing"
    if core.part(index, 'BALL_CUTTER') is None:
        state += ", finalized"
    targets = booleans.targets_using(index)
    names = ", ".join(t.name for t in targets) if targets else "none"
    return state, names


# ------------------------------------------------------------
# Create
# ------------------------------------------------------------
def _spawn_location(context):
    active = context.view_layer.objects.active
    if active is not None and active.select_get():
        return active.matrix_world.translation.copy()
    if context.selected_objects:
        return context.selected_objects[0].matrix_world.translation.copy()
    return context.scene.cursor.location.copy()


def _make_cutters(coll, index, p, ball, stem):
    ball_cutter = core.part(index, 'BALL_CUTTER')
    stem_cutter = core.part(index, 'STEM_CUTTER')
    bc_mesh = shapes.cutter_mesh(ball.data, core.world_matrix(ball).to_scale(), p.clearance,
                                 core.part_name(index, 'BALL_CUTTER'))
    sc_mesh = shapes.cutter_mesh(stem.data, core.world_matrix(stem).to_scale(), p.clearance,
                                 core.part_name(index, 'STEM_CUTTER'))
    if ball_cutter is None:
        ball_cutter = core.new_part(coll, index, 'BALL_CUTTER', bc_mesh)
    else:
        core.replace_mesh(ball_cutter, bc_mesh)
    if stem_cutter is None:
        stem_cutter = core.new_part(coll, index, 'STEM_CUTTER', sc_mesh)
    else:
        core.replace_mesh(stem_cutter, sc_mesh)
    # Cutters always follow their base part exactly
    core.set_parent(ball_cutter, ball)
    core.set_parent(stem_cutter, stem)
    booleans.set_boolean(ball_cutter, booleans.CUTTER_UNION, stem_cutter, 'UNION')


def create_joint(context):
    scene = context.scene
    index = core.free_index()
    if index is None:
        raise core.JointError(f"Maximum of {core.MAX_JOINTS} joints reached")

    source = displayed_params(scene)   # build from the values shown on screen
    scene.bjg.template.copy_from(source)
    coll = core.ensure_joint_collection(scene, index)
    data = coll.bjg
    data.params.copy_from(scene.bjg.template)
    data.has_cutout_matrix = False
    data.use_cutout = False  # reset when reusing a free slot (no parts yet, so nothing is created)
    p = data.params

    ball = core.new_part(coll, index, 'BALL', shapes.ball_mesh(p, core.part_name(index, 'BALL')))
    ball.matrix_world = Matrix.Translation(_spawn_location(context))
    stem = core.new_part(coll, index, 'STEM', shapes.stem_mesh(p, core.part_name(index, 'STEM')))
    core.set_parent(stem, ball)
    booleans.set_boolean(ball, booleans.MALE_UNION, stem, 'UNION')
    _make_cutters(coll, index, p, ball, stem)
    apply_preview_visibility(scene)
    mark_built(index)

    select_joint(context, index)
    return index


# ------------------------------------------------------------
# Update Preview
# ------------------------------------------------------------
def rebuild_joint(context, index):
    """Rebuild the meshes from this joint's values. Returns a message (raises JointError on failure)."""
    scene = context.scene
    ball = core.part(index, 'BALL')
    stem = core.part(index, 'STEM')
    label = core.joint_label(index)
    if ball is None:
        raise core.JointError(f"{label}: ball not found")
    if stem is None:
        raise core.JointError(f"{label}: the stem has been applied, the shape can no longer be updated")

    coll = core.ensure_joint_collection(scene, index)
    p = coll.bjg.params
    core.replace_mesh(ball, shapes.ball_mesh(p, core.part_name(index, 'BALL')))
    core.replace_mesh(stem, shapes.stem_mesh(p, core.part_name(index, 'STEM')))
    _make_cutters(coll, index, p, ball, stem)  # recreated if removed by Finalize

    cutout = core.part(index, 'CUTOUT')
    if cutout is not None:
        core.replace_mesh(cutout, shapes.cutout_mesh(p, core.part_name(index, 'CUTOUT')))

    apply_preview_visibility(scene)
    mark_built(index)
    return f"{label} updated"


# ------------------------------------------------------------
# Cutout
# ------------------------------------------------------------
def _remember_cutout_matrix(index):
    cutout = core.part(index, 'CUTOUT')
    data = joint_data(index)
    if cutout is None or data is None:
        return
    data.cutout_matrix = core.matrix_to_list(cutout.matrix_basis)
    data.has_cutout_matrix = True


def _create_cutout(scene, index, ball):
    coll = core.ensure_joint_collection(scene, index)
    data = coll.bjg
    cutout = core.new_part(coll, index, 'CUTOUT',
                           shapes.cutout_mesh(data.params, core.part_name(index, 'CUTOUT')))
    local = core.list_to_matrix(data.cutout_matrix) if data.has_cutout_matrix else Matrix.Identity(4)
    core.set_parent(cutout, ball, local)
    # Targets that already have this joint's socket get the cutout as well
    show = scene.bjg.show_preview
    for tgt in booleans.targets_using(index, include_cutout=False):
        booleans.set_boolean(tgt, booleans.cutout_mod_name(index), cutout, 'DIFFERENCE', show)
    return cutout


def sync_cutout(context, index):
    """Create or remove the cutout to match the joint's Use Cutout setting."""
    scene = context.scene
    data = joint_data(index)
    if data is None:
        return
    ball = core.part(index, 'BALL')
    cutout = core.part(index, 'CUTOUT')
    if data.use_cutout and ball is not None and cutout is None:
        cutout = _create_cutout(scene, index, ball)
        apply_preview_visibility(scene)
        if not core.is_hidden(cutout):
            for obj in context.selected_objects:
                obj.select_set(False)
            cutout.select_set(True)
            context.view_layer.objects.active = cutout
    elif not data.use_cutout and cutout is not None:
        _remember_cutout_matrix(index)
        for tgt in booleans.targets_using(index):
            booleans.remove_modifier(tgt, booleans.cutout_mod_name(index))
        core.delete_object(cutout)


# ------------------------------------------------------------
# Visibility
# ------------------------------------------------------------
def apply_preview_visibility(scene):
    show = scene.bjg.show_preview
    for obj in bpy.data.objects:
        role = core.role_of(obj)
        if role in core.CUTTER_ROLES:
            core.set_hidden(obj, not show)
        elif role is None and obj.type == 'MESH':
            for m in obj.modifiers:
                if m.type == 'BOOLEAN' and m.name.startswith(booleans.TARGET_PREFIXES):
                    m.show_viewport = show
                    m.show_render = show


# ------------------------------------------------------------
# Finalize (also turns Use Cutout off)
# ------------------------------------------------------------
def finalize_joint(context, index):
    n = booleans.finalize(context, index)
    if n:
        data = joint_data(index)
        if data is not None:
            data.has_cutout_matrix = False
            data.use_cutout = False
    return n
