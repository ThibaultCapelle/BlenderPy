
import bpy
from bpy.types import Operator
from bpy.props import FloatVectorProperty
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector

if bpy.ops.object.mode_set.poll():
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT')

for item in bpy.context.selectable_objects:
    bpy.data.objects[item.name].select_set(True)
    bpy.context.view_layer.objects.active = bpy.data.objects[item.name]
    bpy.ops.object.delete(use_global=True)
    
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)

for block in bpy.data.materials:
    if block.users == 0:
        bpy.data.materials.remove(block)

for block in bpy.data.textures:
    if block.users == 0:
        bpy.data.textures.remove(block)

for block in bpy.data.images:
    if block.users == 0:
        bpy.data.images.remove(block)



verts = [
    Vector((-1, 0.5, 0.3)),
    Vector((1, 0.5, 0.3)),
    Vector((1, -0.5, 0.3)),
    Vector((-1, -0.5, 0.3)),
]

edges = []
faces = [[0, 1, 2, 3]]

mesh_data = bpy.data.meshes.new("cube_mesh_data")
mesh_data.from_pydata(verts, [], faces)
mesh_data.update()

obj = bpy.data.objects.new("My_Object", mesh_data)

collection = bpy.context.collection
collection.objects.link(obj)
