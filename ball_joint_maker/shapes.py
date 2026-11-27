# shapes.py - Mesh generation for all parts (built directly with bmesh, no bpy.ops)
#
# To change a shape or add a new one, only this file needs editing.
# Every function returns a new Mesh datablock and never touches objects or the scene.

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

TAPER_SHAPES = {'CYLINDER', 'CUBE', 'FLAT_CYLINDER'}  # shapes that support top/bottom scaling
_EPS = 1e-9


# ------------------------------------------------------------
# Internal
# ------------------------------------------------------------
def _add_unit_primitive(bm, kind, segments):
    """Add a primitive that spans -1..+1 on every axis."""
    if kind == 'SPHERE':
        bmesh.ops.create_uvsphere(bm, u_segments=segments,
                                  v_segments=max(3, segments // 2), radius=1.0)
    elif kind == 'CUBE':
        bmesh.ops.create_cube(bm, size=2.0)
    else:  # CYLINDER / FLAT_CYLINDER
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                              radius1=1.0, radius2=1.0, depth=2.0)


def _taper(bm, top, bottom):
    """Scale XY linearly along Z (bottom face x bottom, top face x top)."""
    if top == 1.0 and bottom == 1.0:
        return
    for v in bm.verts:
        t = (v.co.z + 1.0) * 0.5
        f = bottom + (top - bottom) * t
        v.co.x *= f
        v.co.y *= f


def _to_mesh(bm, name):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return mesh


def _taper_factors(use_top, top, use_bottom, bottom):
    return (top if use_top else 1.0), (bottom if use_bottom else 1.0)


# ------------------------------------------------------------
# Public functions
# ------------------------------------------------------------
def ball_mesh(p, name):
    """Ball centered on the origin. Radius r (cylinder height 2r, cube edge 2r)."""
    bm = bmesh.new()
    _add_unit_primitive(bm, p.ball_shape, p.segments)
    if p.ball_shape in TAPER_SHAPES:
        _taper(bm, *_taper_factors(p.use_ball_top_scale, p.ball_top_scale,
                                   p.use_ball_bottom_scale, p.ball_bottom_scale))
    r = p.ball_radius
    bmesh.ops.scale(bm, vec=(r, r, r), verts=bm.verts)
    return _to_mesh(bm, name)


def stem_mesh(p, name):
    """Stem whose top sits at the origin (the ball center) plus Z offset, extending down by its length.
    Because the origin is the ball center, rotating the stem pivots it around the ball."""
    bm = bmesh.new()
    _add_unit_primitive(bm, p.stem_shape, p.segments)
    if p.stem_shape in TAPER_SHAPES:
        _taper(bm, *_taper_factors(p.use_stem_top_scale, p.stem_top_scale,
                                   p.use_stem_bottom_scale, p.stem_bottom_scale))
    r = p.stem_radius
    ry = r * p.stem_flat_ratio if p.stem_shape == 'FLAT_CYLINDER' else r
    half = p.stem_length * 0.5
    bmesh.ops.scale(bm, vec=(r, ry, half), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(0.0, 0.0, p.stem_z_offset - half), verts=bm.verts)
    return _to_mesh(bm, name)


def cutter_mesh(base_mesh, world_scale, clearance, name):
    """Copy of base_mesh scaled about its bounding-box center so that each axis grows by
    `clearance` (added to the diameter). world_scale is the base object's world scale, so the
    size is measured in world units."""
    bm = bmesh.new()
    bm.from_mesh(base_mesh)
    if bm.verts:
        lo = Vector(tuple(min(v.co[a] for v in bm.verts) for a in range(3)))
        hi = Vector(tuple(max(v.co[a] for v in bm.verts) for a in range(3)))
        center = (lo + hi) * 0.5
        factors = []
        for a in range(3):
            size = (hi[a] - lo[a]) * abs(world_scale[a])
            factors.append((size + clearance) / size if size > _EPS else 1.0)
        for v in bm.verts:
            d = v.co - center
            v.co = center + Vector((d.x * factors[0], d.y * factors[1], d.z * factors[2]))
    return _to_mesh(bm, name)


def cutout_mesh(p, name):
    """Cutout centered on the origin. BOX is X*Y*Z; CYLINDER runs along Y (cross-section X*Z)."""
    bm = bmesh.new()
    if p.cutout_shape == 'CYLINDER':
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=32,
                              radius1=0.5, radius2=0.5, depth=1.0)
        bmesh.ops.rotate(bm, cent=(0.0, 0.0, 0.0),
                         matrix=Matrix.Rotation(math.pi / 2.0, 3, 'X'), verts=bm.verts)
    else:
        bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(p.cutout_sx, p.cutout_sy, p.cutout_sz), verts=bm.verts)
    return _to_mesh(bm, name)
