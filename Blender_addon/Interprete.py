import bpy, json

import bmesh 
from mathutils import Vector 
from bmesh.types import BMVert 

class Interprete:
    
    def __init__(self, server):
        self.server=server
    
    def call(self, cmd):
        print('len of args is {:}'.format(len(cmd['args'])))
        if len(cmd['args'])==0 or (len(cmd['args'])==1 and len(cmd['args'][0])==0):
            getattr(self, cmd['command'])(**cmd['kwargs'])
        else:
            getattr(self, cmd['command'])(*cmd['args'], **cmd['kwargs'])
    
    def delete_all(self, connection=None):
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
        
    def create_mesh(self, points=None, cells=None, name=None,
             thickness=None, connection=None):
        obj = Object(name, points, cells, thickness)
        self.server.send_answer(connection, 
                                [obj.name_msh, obj.name_msh])
    
    def update_material(self, connection=None, **kwargs):
        material=bpy.data.materials.get(kwargs['name'])
        material.node_tree.nodes["Principled BSDF"].inputs[0].default_value=kwargs['color']
        material.node_tree.nodes["Principled BSDF"].inputs[15].default_value=kwargs['transmission']
        material.node_tree.nodes["Principled BSDF"].inputs[16].default_value=kwargs['use_screen_refraction']
        material.use_screen_refraction=kwargs['use_screen_refraction']
        if kwargs['use_screen_refraction']:
            bpy.context.scene.eevee.use_ssr = True
            bpy.context.scene.eevee.use_ssr_refraction = True
        print('yolo')
        
    def get_material_names(self, connection=None):
        assert connection is not None
        self.server.send_answer(connection,
                                [item.name for item in bpy.data.materials])
    
    def get_material(self, name, connection=None):
        self.server.send_answer(connection, bpy.data.materials.get(name).name)
    
    def create_material(self, name, connection=None):
        self.server.send_answer(connection, self.new_material(name).name)
    
    def new_material(self, name):
        mat=bpy.data.materials.new(name)
        mat.use_nodes = True
        self.nodes = mat.node_tree.nodes
        print([node for node in self.nodes])
        #node = self.nodes.new("Principled BSDF")
        return mat
    
    def assign_material(self, **kwargs):
        bpy.data.objects[kwargs['name_obj']].select_set(True)
        bpy.context.view_layer.objects.active = bpy.data.objects[kwargs['name_obj']]
        ob = bpy.data.objects[kwargs['name_obj']]
        if ob.data.materials:
            ob.data.materials[0] = bpy.data.materials.get(kwargs['name_mat'])
        else:
            ob.data.materials.append(bpy.data.materials.get(kwargs['name_mat']))




def Material(message):
    #print(message)
    assert message['class']=='Material'


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
        
        

