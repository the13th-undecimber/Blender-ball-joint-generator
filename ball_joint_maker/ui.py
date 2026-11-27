# ui.py - Sidebar (N panel) > Joint Maker
#
# Workflow: 1) pick or create a joint -> 2) set the shape, Update Preview
#           -> 3) preview the socket on a target -> 4) apply
# Buttons show the joint they act on and are greyed out when there is nothing to act on.
# Update Preview sits in the "2) Shape" header and turns red while changes are not applied.

import bpy

from . import booleans, core, joint


def _taper_rows(col, p, prefix):
    col.prop(p, f"use_{prefix}_top_scale")
    if getattr(p, f"use_{prefix}_top_scale"):
        col.prop(p, f"{prefix}_top_scale")
    col.prop(p, f"use_{prefix}_bottom_scale")
    if getattr(p, f"use_{prefix}_bottom_scale"):
        col.prop(p, f"{prefix}_bottom_scale")


def _arrow(idx):
    return f" → {core.joint_label(idx)}" if idx else ""


class BJG_PT_main(bpy.types.Panel):
    bl_label = "Joint Maker"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Joint Maker"

    def draw(self, context):
        existing = core.existing_indices()
        self.layout.label(text=f"Joints {len(existing)} / {core.MAX_JOINTS}", icon='INFO')


class _Section:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Joint Maker"
    bl_parent_id = "BJG_PT_main"


# ------------------------------------------------------------
# 1) Joints
# ------------------------------------------------------------
class BJG_PT_joints(_Section, bpy.types.Panel):
    bl_label = "1) Joints"

    def draw(self, context):
        layout = self.layout
        existing = set(core.existing_indices())
        edited = joint.edited_index(context.scene)

        col = layout.column(align=True)
        row = None
        for i in range(1, core.MAX_JOINTS + 1):
            if (i - 1) % 3 == 0:
                row = col.row(align=True)
            cell = row.row(align=True)
            cell.enabled = i in existing
            cell.operator("bjg.edit_joint", text=core.joint_label(i), depress=(i == edited)).index = i

        if edited:
            state, targets = joint.joint_state(edited)
            box = layout.box()
            box.label(text=f"Editing: {core.joint_label(edited)} ({state})", icon='OBJECT_DATA')
            box.label(text=f"Socket preview on: {targets}")
            row = box.row(align=True)
            row.label(text="Select:")
            row.operator("bjg.select_part", text="Ball").which = 'BALL'
            sub = row.row(align=True)
            sub.enabled = core.part(edited, 'STEM') is not None
            sub.operator("bjg.select_part", text="Stem").which = 'STEM'
            sub = row.row(align=True)
            sub.enabled = core.part(edited, 'CUTOUT') is not None
            sub.operator("bjg.select_part", text="Cutout").which = 'CUTOUT'
        else:
            layout.label(text="No joint is being edited", icon='INFO')

        big = layout.row()
        big.scale_y = 1.3
        big.operator("bjg.generate", icon='MESH_UVSPHERE')


# ------------------------------------------------------------
# 2) Shape (Update Preview in the header, values in sub-panels)
# ------------------------------------------------------------
class BJG_PT_shape(_Section, bpy.types.Panel):
    bl_label = "2) Shape"

    def draw_header_preset(self, context):
        edited = joint.edited_index(context.scene)
        row = self.layout.row(align=True)
        row.enabled = edited is not None and core.part(edited, 'STEM') is not None
        row.alert = edited is not None and joint.is_stale(edited)
        row.operator("bjg.rebuild_preview", text="Update Preview" + _arrow(edited), icon='FILE_REFRESH')

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        edited = joint.edited_index(scene)
        p = joint.displayed_params(scene)

        if edited is None:
            layout.label(text="Values for the next new joint", icon='ADD')
        elif core.part(edited, 'STEM') is None:
            layout.label(text=f"{core.joint_label(edited)}: stem applied (shape is locked)", icon='LOCKED')
        elif joint.is_stale(edited):
            warn = layout.row()
            warn.alert = True
            warn.label(text=f"{core.joint_label(edited)}: changes not applied - press Update Preview",
                       icon='ERROR')
        else:
            layout.label(text=f"{core.joint_label(edited)} values (up to date)", icon='CHECKMARK')

        row = layout.row(align=True)
        row.prop(p, "segments")
        row.operator("bjg.reset_params", text="", icon='LOOP_BACK')


class _ShapeSub:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Joint Maker"
    bl_parent_id = "BJG_PT_shape"


class BJG_PT_shape_ball(_ShapeSub, bpy.types.Panel):
    bl_label = "Ball"

    def draw(self, context):
        p = joint.displayed_params(context.scene)
        col = self.layout.column(align=True)
        col.prop(p, "ball_shape", text="")
        col.prop(p, "ball_radius")
        if p.ball_shape in {'CYLINDER', 'CUBE'}:
            _taper_rows(col, p, "ball")


class BJG_PT_shape_stem(_ShapeSub, bpy.types.Panel):
    bl_label = "Stem"

    def draw(self, context):
        p = joint.displayed_params(context.scene)
        col = self.layout.column(align=True)
        col.prop(p, "stem_shape", text="")
        col.prop(p, "stem_radius")
        col.prop(p, "stem_length")
        if p.stem_shape == 'FLAT_CYLINDER':
            col.prop(p, "stem_flat_ratio")
        if p.stem_shape in {'CYLINDER', 'CUBE', 'FLAT_CYLINDER'}:
            _taper_rows(col, p, "stem")


class BJG_PT_shape_clearance(_ShapeSub, bpy.types.Panel):
    bl_label = "Clearance"

    def draw(self, context):
        p = joint.displayed_params(context.scene)
        self.layout.prop(p, "clearance", text="Added to Diameter")


class BJG_PT_shape_cutout(_ShapeSub, bpy.types.Panel):
    bl_label = "Cutout"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        edited = joint.edited_index(context.scene)
        if edited is not None:
            self.layout.prop(joint.joint_data(edited), "use_cutout", text="")

    def draw(self, context):
        layout = self.layout
        edited = joint.edited_index(context.scene)
        p = joint.displayed_params(context.scene)
        if edited is None:
            layout.label(text="Pick a joint to use cutouts")
            return
        data = joint.joint_data(edited)
        col = layout.column(align=True)
        col.active = data.use_cutout
        col.prop(p, "cutout_shape", text="")
        col.prop(p, "cutout_sx")
        col.prop(p, "cutout_sy")
        col.prop(p, "cutout_sz")


# ------------------------------------------------------------
# 3) Target / 4) Apply
# ------------------------------------------------------------
class BJG_PT_target(_Section, bpy.types.Panel):
    bl_label = "3) Target"

    def draw(self, context):
        layout = self.layout
        edited = joint.edited_index(context.scene)
        has_target = any(booleans.is_target(o) for o in context.selected_objects)
        if not has_target:
            layout.label(text="Select the mesh(es) to cut", icon='INFO')

        row = layout.row()
        row.enabled = edited is not None and has_target
        row.operator("bjg.apply_to_target", text="Preview Socket on Target" + _arrow(edited),
                     icon='MOD_BOOLEAN')
        row = layout.row()
        row.enabled = has_target and bool(core.existing_indices())
        row.operator("bjg.apply_to_target", text="Preview Sockets of All Joints").all_joints = True
        layout.prop(context.scene.bjg, "show_preview")


class BJG_PT_finalize(_Section, bpy.types.Panel):
    bl_label = "4) Apply"

    def draw(self, context):
        layout = self.layout
        edited = joint.edited_index(context.scene)

        row = layout.row()
        row.enabled = edited is not None and core.part(edited, 'STEM') is not None
        row.operator("bjg.confirm_male", text="Apply Stem" + _arrow(edited), icon='CHECKMARK')

        row = layout.row()
        row.enabled = edited is not None and bool(booleans.targets_using(edited))
        row.operator("bjg.finalize", text="Finalize" + _arrow(edited), icon='CHECKMARK')
        row = layout.row()
        row.enabled = any(booleans.targets_using(i) for i in core.existing_indices())
        row.operator("bjg.finalize", text="Finalize All Joints").all_joints = True


classes = (BJG_PT_main, BJG_PT_joints, BJG_PT_shape,
           BJG_PT_shape_ball, BJG_PT_shape_stem, BJG_PT_shape_clearance, BJG_PT_shape_cutout,
           BJG_PT_target, BJG_PT_finalize)
