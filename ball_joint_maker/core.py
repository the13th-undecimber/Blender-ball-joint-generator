# core.py - Shared helpers (names, tags, collections, deletion, parenting, mesh replacement)
#
# Every object created by the add-on carries a role tag and a joint-index tag.
# Parts are found by tag, not by name, so a renamed or ".001" object is still found.

import bpy
from mathutils import Matrix

MAX_JOINTS = 6

ROLE_KEY = "bjg_role"        # role of the object
JOINT_KEY = "bjg_joint"      # joint index of the object
BACKUP_KEY = "bjg_backup"    # marks a pre-Finalize backup copy
BACKUP_DONE_KEY = "bjg_backup_done"  # marks a target that already has a backup

ROOT_COLLECTION = "BJG_Joints"

# role -> name prefix
ROLE_BASE_NAMES = {
    'BALL': "BJG_Ball",
    'STEM': "BJG_Stem",
    'BALL_CUTTER': "BJG_BallCutter",
    'STEM_CUTTER': "BJG_StemCutter",
    'CUTOUT': "BJG_Cutout",
}
HELPER_ROLES = ('STEM', 'BALL_CUTTER', 'STEM_CUTTER', 'CUTOUT')  # wireframe display, hidden in renders
CUTTER_ROLES = ('BALL_CUTTER', 'STEM_CUTTER', 'CUTOUT')          # affected by the preview toggle


class JointError(Exception):
    """Error meant for the user. Operators show it with report()."""


# ------------------------------------------------------------
# Names
# ------------------------------------------------------------
def joint_label(index):
    return f"J{index:03d}"


def collection_name(index):
    return f"BJG_Joint{index:03d}"


def part_name(index, role):
    return f"{ROLE_BASE_NAMES[role]}{index:03d}"


# ------------------------------------------------------------
# Lookup
# ------------------------------------------------------------
def role_of(obj):
    return obj.get(ROLE_KEY) if obj is not None else None


def index_of(obj):
    """Joint index of the object (or of its parents), or None."""
    while obj is not None:
        idx = obj.get(JOINT_KEY)
        if isinstance(idx, int) and 1 <= idx <= MAX_JOINTS:
            return idx
        obj = obj.parent
    return None


def is_generated(obj):
    return role_of(obj) is not None


def is_backup(obj):
    return bool(obj.get(BACKUP_KEY, False))


def part(index, role):
    """Return the part of a joint. If duplicates carry the same tags, the canonical name wins."""
    wanted = part_name(index, role)
    found = None
    for obj in bpy.data.objects:
        if obj.get(ROLE_KEY) == role and obj.get(JOINT_KEY) == index:
            if obj.name == wanted:
                return obj
            if found is None:
                found = obj
    return found


def existing_indices():
    """Indices of joints whose ball exists."""
    found = set()
    for obj in bpy.data.objects:
        if obj.get(ROLE_KEY) == 'BALL':
            idx = obj.get(JOINT_KEY)
            if isinstance(idx, int):
                found.add(idx)
    return sorted(found)


def free_index():
    """Lowest joint index without any parts, or None when all slots are used."""
    used = set()
    for obj in bpy.data.objects:
        if obj.get(ROLE_KEY) is not None:
            idx = obj.get(JOINT_KEY)
            if isinstance(idx, int):
                used.add(idx)
    for i in range(1, MAX_JOINTS + 1):
        if i not in used:
            return i
    return None


def joint_collection(index):
    for coll in bpy.data.collections:
        if coll.bjg.index == index:
            return coll
    return None


# ------------------------------------------------------------
# Collections
# ------------------------------------------------------------
def _root_collection(scene):
    root = bpy.data.collections.get(ROOT_COLLECTION)
    if root is None:
        root = bpy.data.collections.new(ROOT_COLLECTION)
    if root.name not in scene.collection.children:
        scene.collection.children.link(root)
    return root


def ensure_joint_collection(scene, index):
    coll = joint_collection(index)
    if coll is None:
        coll = bpy.data.collections.new(collection_name(index))
        coll.bjg.index = index
    root = _root_collection(scene)
    if coll.name not in root.children:
        root.children.link(coll)
    return coll


# ------------------------------------------------------------
# Create / delete
# ------------------------------------------------------------
def new_part(coll, index, role, mesh):
    obj = bpy.data.objects.new(part_name(index, role), mesh)
    obj[ROLE_KEY] = role
    obj[JOINT_KEY] = index
    coll.objects.link(obj)
    if role in HELPER_ROLES:
        obj.display_type = 'WIRE'
        obj.hide_render = True
    return obj


def delete_object(obj):
    if obj is None:
        return
    mesh = obj.data if obj.type == 'MESH' else None
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh is not None and mesh.users == 0:
        bpy.data.meshes.remove(mesh)


def replace_mesh(obj, new_mesh):
    """Swap only the mesh data; the object keeps its transform, parenting and references."""
    old = obj.data
    keep_name = old.name
    obj.data = new_mesh
    if old.users == 0:
        bpy.data.meshes.remove(old)
        new_mesh.name = keep_name


def set_hidden(obj, hidden):
    """Does nothing if the object is not in the view layer (e.g. in an excluded collection)."""
    try:
        obj.hide_set(hidden)
    except RuntimeError:
        pass


def is_hidden(obj):
    try:
        return obj.hide_get()
    except RuntimeError:
        return False


# ------------------------------------------------------------
# Matrices / parenting
# ------------------------------------------------------------
def world_matrix(obj):
    """World matrix computed directly, without waiting for a depsgraph update."""
    m = obj.matrix_basis.copy()
    while obj.parent is not None:
        m = obj.parent.matrix_basis @ obj.matrix_parent_inverse @ m
        obj = obj.parent
    return m


def set_parent(child, parent, local=None):
    """Place the child at `local` in the parent's space (parent inverse set to identity)."""
    child.parent = parent
    child.matrix_parent_inverse = Matrix.Identity(4)
    child.matrix_basis = local if local is not None else Matrix.Identity(4)


def reparent_keep_world(child, new_parent):
    mw = world_matrix(child)
    child.parent = new_parent
    child.matrix_parent_inverse = Matrix.Identity(4)
    child.matrix_basis = world_matrix(new_parent).inverted() @ mw


def matrix_to_list(m):
    return [m[r][c] for r in range(4) for c in range(4)]


def list_to_matrix(values):
    v = list(values)
    return Matrix([v[0:4], v[4:8], v[8:12], v[12:16]])
