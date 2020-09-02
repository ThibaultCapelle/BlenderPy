import bpy, json

import bmesh 
from mathutils import Vector 
from bmesh.types import BMVert 


def delete_all():
    objs = [ob for ob in bpy.context.scene.objects]
    bpy.ops.object.delete({"selected_objects": objs})
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

def Material(message):
    #print(message)
    assert message['class']=='Material'
    
def Mesh(message):
    #print(message)
    points, cells = message['points'], message['cells']
    obj = Object(message["name"], points, cells, message["thickness"])

class Object:
    
    def __init__(self, name, points, cells, thickness):
        self.thickness=thickness
        self.name_root=name
        self.name_obj=self.name_root+'.'+str(1+len([o for o in bpy.data.objects if self.name_root in o.name]))
        self.name_msh=self.name_root+'.'+str(1+len([o for o in bpy.data.meshes if self.name_root in o.name]))
        
        self.points=points
        self.cells=cells
        self.mesh_data = bpy.data.meshes.new(self.name_msh)
        self.mesh_data.from_pydata(points, [], cells)
        self.mesh_data.update()
    
        self.obj = bpy.data.objects.new(self.name_obj, self.mesh_data)
        collection = bpy.context.collection
        collection.objects.link(self.obj)
        self.extrude()
    
    def select_obj(self):
        for obj in bpy.data.objects:
            if self.name_obj==obj.name:
                obj.select_set(True)
                break
    
    def select_msh(self):
        for obj in bpy.data.meshes:
            if self.name_msh==obj.name:
                obj.select_set(True)
                break
    
    def extrude(self):
        if self.thickness is not None:
            self.select_obj()
            # Create BMesh object  
            bm = bmesh.new() 
            bm.from_mesh(self.mesh_data) 
            # Get geometry to extrude 
            bm.faces.ensure_lookup_table()
            faces = bm.faces 
            # Extrude 
            extruded = bmesh.ops.extrude_face_region(bm, geom=faces)
            # Move extruded geometry 
            translate_verts = [v for v in extruded['geom'] if isinstance(v, BMVert)]
            up = Vector((0, 0, self.thickness)) 
            bmesh.ops.translate(bm, vec=up, verts=translate_verts) 
            # Remove doubles 
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001) 
            # Update mesh and free Bmesh 
            bm.normal_update() 
            bm.to_mesh(self.obj.data) 
            bm.free()
        
        

