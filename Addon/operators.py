import bpy
from bpy.types import Operator
import re


def swap_side_name(name):
    """Return the mirror-side counterpart of a shape key name.

    Handles common naming conventions:
        "ArmLeft"/"ArmRight", "Arm.L"/"Arm.R", "Arm_L"/"Arm_R",
        "armleft"/"armright".
    If no convention matches, "_mirrored" is appended.
    """
    patterns = [
        (r'(.*)Left$', r'\1Right'),
        (r'(.*)Right$', r'\1Left'),
        (r'(.*)\.L$', r'\1.R'),
        (r'(.*)\.R$', r'\1.L'),
        (r'(.*)_L$', r'\1_R'),
        (r'(.*)_R$', r'\1_L'),
        (r'(.*)left$', r'\1right'),
        (r'(.*)right$', r'\1left'),
    ]

    for pattern, replacement in patterns:
        if re.match(pattern, name):
            return re.sub(pattern, replacement, name)
    return f"{name}_mirrored"


class MESH_OT_mirror_shape_key(Operator):
    """Duplicate the active shape key, mirror it across the X axis, and
    name the result using the opposite side convention.

    The new key is inserted directly after the source key. Only available
    in Object Mode with a non-basis shape key selected.
    """

    bl_idname = "mesh.mirror_shape_key"
    bl_label = "Duplicate and Mirror Shape Key"
    bl_description = (
        "Duplicate the active shape key, mirror it across the X axis, "
        "and name it using the opposite side convention. "
    )
    bl_options = {'REGISTER', 'UNDO'}

    use_topology: bpy.props.BoolProperty(
        name="Topology Mirror",
        description=(
            "Mirror using topology-based vertex matching instead of "
            "spatial proximity. More reliable on meshes whose mirrored "
            "halves are close to the center line"
        ),
        default=False,
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None
            and obj.type == 'MESH'
            and obj.mode != 'EDIT'          # shape key data is unsafe to edit in Edit Mode
            and obj.data.shape_keys is not None
            and obj.active_shape_key_index > 0
        )

    def execute(self, context):
        obj = context.active_object
        active_key = obj.active_shape_key
        original_index = obj.active_shape_key_index

        if not active_key:
            self.report({'ERROR'}, "No active shape key")
            return {'CANCELLED'}

        new_name = swap_side_name(active_key.name)
        new_key = obj.shape_key_add(name=new_name, from_mix=False)

        for i in range(len(new_key.data)):
            new_key.data[i].co = active_key.data[i].co.copy()

        new_index = len(obj.data.shape_keys.key_blocks) - 1
        obj.active_shape_key_index = new_index

        if self.use_topology:
            bpy.ops.object.shape_key_mirror(use_topology=True)
        else:
            bpy.ops.object.shape_key_mirror()

        while obj.active_shape_key_index > original_index + 1:
            bpy.ops.object.shape_key_move(type='UP')
        self.report({'INFO'}, f"Created mirrored shape key: {new_key.name}")
        return {'FINISHED'}


class MESH_OT_normalize_shape_key_range(Operator):
    """Rescale the active shape key so its slider range becomes 0–1.

    Any custom slider_min / slider_max values are folded into the vertex
    offsets, then the slider is reset to the standard 0–1 range. The
    current slider value is remapped so the visible deformation does not
    change. Only available in Object Mode with a non-basis shape key
    selected.
    """

    bl_idname = "mesh.normalize_shape_key_range"
    bl_label = "Normalize Shape Key Range"
    bl_description = (
        "Reset the active shape key's slider range to 0–1, keeping the visible deformation unchanged. "
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None
            and obj.type == 'MESH'
            and obj.mode != 'EDIT'          # shape key data is unsafe to edit in Edit Mode
            and obj.data.shape_keys is not None
            and obj.active_shape_key_index > 0
        )

    def execute(self, context):
        obj = context.active_object
        shape_key = obj.active_shape_key

        if not shape_key:
            self.report({'ERROR'}, "No active shape key")
            return {'CANCELLED'}

        current_min = shape_key.slider_min
        current_max = shape_key.slider_max
        current_range = current_max - current_min

        if current_range == 0:
            self.report({'ERROR'}, "Shape key has zero range")
            return {'CANCELLED'}

        current_value = shape_key.value
        shape_key.value = 1.0

        basis = obj.data.shape_keys.key_blocks[0]
        basis_verts = [v.co for v in basis.data]

        for i in range(len(shape_key.data)):
            deformation = shape_key.data[i].co - basis_verts[i]
            scaled_deformation = deformation * current_range
            shape_key.data[i].co = basis_verts[i] + scaled_deformation

        shape_key.slider_min = 0.0
        shape_key.slider_max = 1.0
        shape_key.value = (current_value - current_min) / current_range

        self.report({'INFO'}, "Normalized shape key range to 0–1")
        return {'FINISHED'}


def menu_func(self, context):
    layout = self.layout
    op = layout.operator(
        MESH_OT_mirror_shape_key.bl_idname,
        text="Duplicate and Mirror Shape Key",
    )
    op.use_topology = False
    op = layout.operator(
        MESH_OT_mirror_shape_key.bl_idname,
        text="Duplicate and Mirror Shape Key (Topology)",
    )
    op.use_topology = True
    layout.operator(MESH_OT_normalize_shape_key_range.bl_idname)


def register():
    bpy.utils.register_class(MESH_OT_mirror_shape_key)
    bpy.utils.register_class(MESH_OT_normalize_shape_key_range)
    bpy.types.MESH_MT_shape_key_context_menu.append(menu_func)


def unregister():
    bpy.types.MESH_MT_shape_key_context_menu.remove(menu_func)
    bpy.utils.unregister_class(MESH_OT_normalize_shape_key_range)
    bpy.utils.unregister_class(MESH_OT_mirror_shape_key)