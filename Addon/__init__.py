bl_info = {
    "name": "Mirror Shape Key",
    "author": "Bahka and the Ai Sloppa",
    "version": (1, 0),
    "blender": (4, 3, 0),
    "location": "Properties > Object Data Properties > Shape Keys > Specials Menu",
    "description": "Adds options for mirroring and normalizing shape keys as well as warning when editing a non-basis shape key.",
    "category": "Mesh",
}

from . import operators
from . import warning

def register():
    operators.register()
    warning.register()

def unregister():
    warning.unregister()
    operators.unregister()

if __name__ == "__main__":
    register()