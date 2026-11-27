# operators.py - Button actions
#
# Operators act on the edited joint only. Buttons labelled "All Joints" act on every joint.
# Failures are raised as JointError and shown in Blender's status bar (never silently ignored).

import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty

from . import booleans, core, joint, props


def _labels(indices):
    return ", ".join(core.joint_label(i) for i in indices)


class _Base:
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def edited(self, context):
        idx = joint.edited_index(context.scene)
        if idx is None:
            raise core.JointError("No joint is being edited (pick one with the J001-J006 buttons)")
        return idx

    def execute(self, context):
        try:
            return self.run(context)
        except core.JointError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}


# ------------------------------------------------------------
# 1) Joints
# ------------------------------------------------------------
class BJG_OT_generate(_Base, bpy.types.Operator):
    bl_idname = "bjg.generate"
    bl_label = "Generate Joint"
    bl_description = ("Create a ball joint from the values shown, at the selected object "
                      "(or the 3D cursor), and make it the edited joint")

    def run(self, context):
        idx = joint.create_joint(context)
        self.report({'INFO'}, f"{core.joint_label(idx)} created")
        return {'FINISHED'}

    def invoke(self, context, event):
        result = self.execute(context)
        prefs = props.addon_prefs(context)
        if result == {'FINISHED'} and prefs is not None and prefs.show_generate_hint:
            bpy.ops.bjg.generate_hint('INVOKE_DEFAULT')
        return result


class BJG_OT_generate_hint(bpy.types.Operator):
    bl_idname = "bjg.generate_hint"
    bl_label = "Joint Created"
    bl_description = "What to do after generating a joint"
    bl_options = {'INTERNAL'}

    dont_show: BoolProperty(name="Don't show this again", default=False, options={'SKIP_SAVE'})

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=380)

    def draw(self, context):
        col = self.layout.column(align=True)
        col.label(text="After adjusting the shape values, press", icon='INFO')
        col.label(text="[Update Preview] in the \"2) Shape\" header to apply them.")
        col.label(text="The button turns red while changes are not applied.")
        self.layout.separator()
        self.layout.prop(self, "dont_show")

    def execute(self, context):
        prefs = props.addon_prefs(context)
        if self.dont_show and prefs is not None:
            prefs.show_generate_hint = False
            self.report({'INFO'}, "Hint disabled (re-enable it in the add-on preferences)")
        return {'FINISHED'}


class BJG_OT_edit_joint(_Base, bpy.types.Operator):
    bl_idname = "bjg.edit_joint"
    bl_label = "Edit Joint"
    bl_description = "Make this the edited joint and select its ball"
    bl_options = {'REGISTER'}

    index: IntProperty(min=1, max=core.MAX_JOINTS, default=1)

    @classmethod
    def poll(cls, context):
        return True

    def run(self, context):
        if core.part(self.index, 'BALL') is None:
            raise core.JointError(f"{core.joint_label(self.index)} does not exist")
        joint.select_joint(context, self.index)
        return {'FINISHED'}


# ------------------------------------------------------------
# 2) Shape
# ------------------------------------------------------------
class BJG_OT_reset_params(_Base, bpy.types.Operator):
    bl_idname = "bjg.reset_params"
    bl_label = "Reset Values"
    bl_description = "Reset the values shown (the edited joint's values) to defaults. Press Update Preview to apply"

    @classmethod
    def poll(cls, context):
        return True

    def run(self, context):
        joint.displayed_params(context.scene).reset()
        self.report({'INFO'}, "Values reset (press Update Preview to apply)")
        return {'FINISHED'}


class BJG_OT_rebuild_preview(_Base, bpy.types.Operator):
    bl_idname = "bjg.rebuild_preview"
    bl_label = "Update Preview"
    bl_description = "Rebuild the edited joint from the values shown (position, rotation and target previews are kept)"

    def run(self, context):
        msg = joint.rebuild_joint(context, self.edited(context))
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class BJG_OT_select_part(_Base, bpy.types.Operator):
    bl_idname = "bjg.select_part"
    bl_label = "Select Part"
    bl_description = "Select a part of the edited joint"

    which: EnumProperty(items=(
        ('BALL', "Ball", ""),
        ('STEM', "Stem", ""),
        ('CUTOUT', "Cutout", ""),
    ), default='BALL')

    def run(self, context):
        obj = core.part(self.edited(context), self.which)
        if obj is None or core.is_hidden(obj):
            raise core.JointError("Nothing to select (the part is hidden or does not exist)")
        for o in context.selected_objects:
            o.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        return {'FINISHED'}


# ------------------------------------------------------------
# 3) Target
# ------------------------------------------------------------
class BJG_OT_apply_to_target(_Base, bpy.types.Operator):
    bl_idname = "bjg.apply_to_target"
    bl_label = "Preview Socket on Target"
    bl_description = ("Add the socket (and cutout) to the selected meshes as Boolean modifiers. "
                      "Nothing is applied until Finalize")

    all_joints: BoolProperty(default=False, options={'SKIP_SAVE'})

    def run(self, context):
        indices = core.existing_indices() if self.all_joints else [self.edited(context)]
        targets = [o for o in context.selected_objects if booleans.is_target(o)]
        if not targets:
            raise core.JointError("Select the mesh(es) to cut (joint parts are ignored)")
        show = context.scene.bjg.show_preview
        count = sum(booleans.attach_to_target(t, i, show) for i in indices for t in targets)
        joint.apply_preview_visibility(context.scene)
        self.report({'INFO'}, f"{count} socket preview(s) added ({_labels(indices)} -> {len(targets)} object(s))")
        return {'FINISHED'}


# ------------------------------------------------------------
# 4) Apply
# ------------------------------------------------------------
class BJG_OT_confirm_male(_Base, bpy.types.Operator):
    bl_idname = "bjg.confirm_male"
    bl_label = "Apply Stem"
    bl_description = "Merge the edited joint's stem into its ball and delete the stem (the shape can no longer be updated)"

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def run(self, context):
        idx = self.edited(context)
        if not booleans.confirm_male(context, idx):
            raise core.JointError(f"{core.joint_label(idx)}: the stem is already applied")
        self.report({'INFO'}, f"{core.joint_label(idx)}: stem applied")
        return {'FINISHED'}


class BJG_OT_finalize(_Base, bpy.types.Operator):
    bl_idname = "bjg.finalize"
    bl_label = "Finalize"
    bl_description = "Apply the previewed sockets to the targets and delete the cutters (a hidden copy of each target is kept)"

    all_joints: BoolProperty(default=False, options={'SKIP_SAVE'})

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def run(self, context):
        indices = core.existing_indices() if self.all_joints else [self.edited(context)]
        results = []
        for idx in indices:
            n = joint.finalize_joint(context, idx)
            results.append(f"{core.joint_label(idx)}: " + (f"{n} target(s) finalized" if n else "no target"))
        self.report({'INFO'}, "Finalize " + " / ".join(results))
        return {'FINISHED'}


classes = (
    BJG_OT_generate,
    BJG_OT_generate_hint,
    BJG_OT_edit_joint,
    BJG_OT_reset_params,
    BJG_OT_rebuild_preview,
    BJG_OT_select_part,
    BJG_OT_apply_to_target,
    BJG_OT_confirm_male,
    BJG_OT_finalize,
)
