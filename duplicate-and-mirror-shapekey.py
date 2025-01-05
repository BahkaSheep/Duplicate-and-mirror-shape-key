bl_info = {
    "name": "Mirror Shape Key",
    "author": "Created by Bahka and Claude",
    "version": (1, 0),
    "blender": (4, 3, 0),
    "location": "Properties > Object Data Properties > Shape Keys > Specials Menu",
    "description": "Adds mirror options to shape key specials menu",
    "category": "Mesh",
}

import bpy
from bpy.types import Operator
import re

def swap_side_name(name):
    # Define patterns and their replacements
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

    # Try each pattern
    for pattern, replacement in patterns:
        if re.match(pattern, name):
            return re.sub(pattern, replacement, name)

    # If no pattern matches, add _mirrored
    return f"{name}_mirrored"

class MESH_OT_mirror_shape_key(Operator):
    """Duplicate and mirror the selected shape key"""
    bl_idname = "mesh.mirror_shape_key"
    bl_label = "Duplicate and Mirror Shape Key"
    bl_options = {'REGISTER', 'UNDO'}

    use_topology: bpy.props.BoolProperty(
        name="Topology Mirror",
        description="Use topology based mirroring",
        default=False
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH' and
                obj.data.shape_keys and
                obj.active_shape_key_index > 0)

    def execute(self, context):
        obj = context.active_object
        active_key = obj.active_shape_key
        original_index = obj.active_shape_key_index

        if not active_key:
            self.report({'ERROR'}, "No active shape key")
            return {'CANCELLED'}

        # Generate new name by swapping left/right or adding _mirrored
        new_name = swap_side_name(active_key.name)

        new_key = obj.shape_key_add(name=new_name, from_mix=False)

        for i in range(len(new_key.data)):
            new_key.data[i].co = active_key.data[i].co.copy()

        # The new key is at the end of the list
        new_index = len(obj.data.shape_keys.key_blocks) - 1
        obj.active_shape_key_index = new_index

        # Mirror the shape key
        if self.use_topology:
            bpy.ops.object.shape_key_mirror(use_topology=True)
        else:
            bpy.ops.object.shape_key_mirror()

        # Move the new shape key to just after the original
        while obj.active_shape_key_index > original_index + 1:
            bpy.ops.object.shape_key_move(type='UP')
        self.report({'INFO'}, f"Created mirrored shape key: {new_key.name}")
        return {'FINISHED'}

def menu_func(self, context):
    op = self.layout.operator(MESH_OT_mirror_shape_key.bl_idname, text="Duplicate and Mirror Shape Key")
    op.use_topology = False
    op = self.layout.operator(MESH_OT_mirror_shape_key.bl_idname, text="Duplicate and Mirror Shape Key (Topology)")
    op.use_topology = True

def register():
    bpy.utils.register_class(MESH_OT_mirror_shape_key)
    bpy.types.MESH_MT_shape_key_context_menu.append(menu_func)

def unregister():
    bpy.utils.unregister_class(MESH_OT_mirror_shape_key)
    bpy.types.MESH_MT_shape_key_context_menu.remove(menu_func)

if __name__ == "__main__":
    register()
