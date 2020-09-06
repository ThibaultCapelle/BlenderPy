import bpy, json

import bmesh 
from mathutils import Vector 
from bmesh.types import BMVert 

class Interprete:
    
    def __init__(self, server):
        self.server=server
    
    def call(self, cmd):
        if len(cmd['args'])==0 or\
        (len(cmd['args'])==1 and len(cmd['args'][0])==0)or\
        'args' not in cmd.keys():
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
        material.node_tree.nodes["Principled BSDF"].inputs['Alpha'].default_value=kwargs['alpha']
        material.blend_method = kwargs['blend_method']

        material.use_screen_refraction=kwargs['use_screen_refraction']
        if kwargs['use_screen_refraction']:
            bpy.context.scene.eevee.use_ssr = True
            bpy.context.scene.eevee.use_ssr_refraction = True
        print(kwargs)
        material.use_backface_culling=kwargs['use_backface_culling']
    
    def z_dependant_color(self, connection=None, **kwargs):
        material=bpy.data.materials.get(kwargs['name'])
        Texcoords=material.node_tree.nodes.new(type="ShaderNodeTexCoord")
        SeparateXYZ=material.node_tree.nodes.new(type="ShaderNodeSeparateXYZ")
        material.node_tree.links.new(Texcoords.outputs['Generated'],
                                     SeparateXYZ.inputs['Vector'])
        ColorRamp=material.node_tree.nodes.new(type="ShaderNodeValToRGB")
        material.node_tree.links.new(SeparateXYZ.outputs['Z'],
                                     ColorRamp.inputs['Fac'])
        Principled_BDSF=material.node_tree.nodes['Principled BSDF']
        material.node_tree.links.new(ColorRamp.outputs['Color'],
                                     Principled_BDSF.inputs['Base Color'])
        for element in ColorRamp.color_ramp.elements[:-1]:
            ColorRamp.color_ramp.elements.remove(element)
        element=ColorRamp.color_ramp.elements[0]
        element.position=kwargs['positions'][0]
        element.color=kwargs['colors'][0]
        for position, color in zip(kwargs['positions'][1:],
                                   kwargs['colors'][1:]):
            new_element=ColorRamp.color_ramp.elements.new(position)
            new_element.color=color
            
    def gaussian_laser(self, connection=None, **kwargs):
        W0=kwargs['W0']
        ZR=kwargs['ZR']
        I=kwargs['I']
        material=bpy.data.materials.get(kwargs['name'])
        Texcoords=material.node_tree.nodes.new(type="ShaderNodeTexCoord")
        SeparateXYZ=material.node_tree.nodes.new(type="ShaderNodeSeparateXYZ")
        material.node_tree.links.new(Texcoords.outputs['Generated'],
                                     SeparateXYZ.inputs['Vector'])
        powx=material.node_tree.nodes.new(type="ShaderNodeMath")
        powx.operation='POWER'
        powy=material.node_tree.nodes.new(type="ShaderNodeMath")
        powy.operation='POWER'
        
        diffx, diffy, diffz=(material.node_tree.nodes.new(type="ShaderNodeMath"),
                             material.node_tree.nodes.new(type="ShaderNodeMath"),
                             material.node_tree.nodes.new(type="ShaderNodeMath"))
        for op, coord in zip([diffx, diffy, diffz], ['X', 'Y', 'Z']):
            op.operation='SUBTRACT'
            material.node_tree.links.new(SeparateXYZ.outputs[coord],
                                         op.inputs[0])
            op.inputs[1].default_value=0.5
        material.node_tree.links.new(diffx.outputs[0],
                                     powx.inputs[0])
        powx.inputs[1].default_value=2
        material.node_tree.links.new(diffy.outputs[0],
                                     powy.inputs[0])
        powy.inputs[1].default_value=2
        add=material.node_tree.nodes.new(type="ShaderNodeMath")
        add.operation='ADD'
        material.node_tree.links.new(powx.outputs[0],
                                     add.inputs[0])   
        material.node_tree.links.new(powy.outputs[0],
                                     add.inputs[1])
        minus=material.node_tree.nodes.new(type="ShaderNodeMath")
        minus.operation='SUBTRACT'
        minus.inputs[0].default_value=0
        material.node_tree.links.new(add.outputs[0],
                                     minus.inputs[1])
        divide=material.node_tree.nodes.new(type="ShaderNodeMath")
        divide.operation='DIVIDE'
        divide.inputs[1].default_value=ZR
        material.node_tree.links.new(diffz.outputs[0],
                                     divide.inputs[0])
        powz=material.node_tree.nodes.new(type="ShaderNodeMath")
        powz.operation='POWER'
        material.node_tree.links.new(divide.outputs[0],
                                     powz.inputs[0])
        powz.inputs[1].default_value=2
        
        addz=material.node_tree.nodes.new(type="ShaderNodeMath")
        addz.operation='ADD'
        addz.inputs[1].default_value=1
        material.node_tree.links.new(powz.outputs[0],
                                     addz.inputs[0])
        #1+(z/ZR)**2
        
        multiply=material.node_tree.nodes.new(type="ShaderNodeMath")
        multiply.operation='MULTIPLY'
        multiply.inputs[1].default_value=W0*W0
        material.node_tree.links.new(addz.outputs[0],
                                     multiply.inputs[0])
        #w(z)**2
        divide=material.node_tree.nodes.new(type="ShaderNodeMath")
        divide.operation='DIVIDE'
        material.node_tree.links.new(minus.outputs[0],
                                     divide.inputs[0])
        material.node_tree.links.new(multiply.outputs[0],
                                     divide.inputs[1])
        
        powfinal=material.node_tree.nodes.new(type="ShaderNodeMath")
        powfinal.operation='POWER'
        powfinal.inputs[0].default_value=2.71
        material.node_tree.links.new(divide.outputs[0],
                                     powfinal.inputs[1])
        #e(-r**2/w(z)**2)
        wz=material.node_tree.nodes.new(type="ShaderNodeMath")
        wz.operation='SQRT'
        material.node_tree.links.new(multiply.outputs[0],
                                     wz.inputs[0])
        
        divide=material.node_tree.nodes.new(type="ShaderNodeMath")
        divide.operation='DIVIDE'
        divide.inputs[0].default_value=W0
        material.node_tree.links.new(wz.outputs[0],
                                     divide.inputs[1])
        multiply=material.node_tree.nodes.new(type="ShaderNodeMath")
        multiply.operation='MULTIPLY'
        material.node_tree.links.new(divide.outputs[0],
                                     multiply.inputs[0])
        material.node_tree.links.new(powfinal.outputs[0],
                                     multiply.inputs[1])
        
        multiplyfinal=material.node_tree.nodes.new(type="ShaderNodeMath")
        multiplyfinal.operation='MULTIPLY'
        material.node_tree.links.new(multiply.outputs[0],
                                     multiplyfinal.inputs[0])
        multiplyfinal.inputs[1].default_value=I
        
        emission=material.node_tree.nodes.new(type="ShaderNodeEmission")
        emission.inputs['Color'].default_value=[0.8984375, 0.1484375,
                       0.1484375, 1.] #'#E62626'
        material.node_tree.links.new(multiplyfinal.outputs[0],
                                     emission.inputs['Strength'])
        output=material.node_tree.nodes['Material Output']
        material.node_tree.links.new(emission.outputs['Emission'],
                                     output.inputs['Volume'])
        material.node_tree.nodes.remove(material.node_tree.nodes['Principled BSDF'])
        
    def get_material_names(self, connection=None):
        assert connection is not None
        self.server.send_answer(connection,
                                [item.name for item in bpy.data.materials])

    
    def create_light(self, name='light', connection=None, power=100, radius=0.2,
                     location=[0,0,0]):
        names=[item.name for item in bpy.data.lights]
        bpy.ops.object.light_add(type='POINT', radius=radius,
                                 location=(location[0], location[1], location[2]))
        new_names=[item.name for item in bpy.data.lights]
        for item in new_names:
            if item not in names:
                created_name=item
                break
        new_name=name+'.{:}'.format(1+len([item for item in bpy.data.lights if name in item.name]))
        bpy.data.lights[created_name].name=new_name
        bpy.data.lights[new_name].energy=power
        self.server.send_answer(connection, new_name)
    
    def create_camera(self, **kwargs):
        names, names_obj=([item.name for item in bpy.data.cameras],
                          [item.name for item in bpy.data.objects])
        location, rotation=kwargs['location'], kwargs['rotation']
        bpy.ops.object.camera_add(location=(location[0], location[1], location[2]),
                                            rotation=(rotation[0], rotation[1], rotation[2]))
        new_names, new_names_obj=([item.name for item in bpy.data.cameras],
                          [item.name for item in bpy.data.objects])
        for item in new_names:
            if item not in names:
                created_name=item
                break
        for item in new_names_obj:
            if item not in names_obj:
                created_name_obj=item
                break
        new_name=kwargs['name']+'.{:}'.format(1+len([item for item in bpy.data.cameras if kwargs['name'] in item.name]))
        new_name_obj=kwargs['name']+'.{:}'.format(1+len([item for item in bpy.data.objects if kwargs['name'] in item.name]))
        bpy.data.cameras[created_name].name=new_name
        bpy.data.objects[created_name_obj].name=new_name_obj
        self.server.send_answer(kwargs['connection'], [new_name, new_name_obj])
    
    def get_camera_position(self, **kwargs):
        camera=bpy.data.objects[kwargs['name_obj']]
        res=[camera.location.x,
             camera.location.y,
             camera.location.z]
        self.server.send_answer(kwargs['connection'], res)
    
    def set_camera_position(self, **kwargs):
        camera=bpy.data.objects[kwargs['name_obj']]
        camera.location.x=kwargs['position'][0]
        camera.location.y=kwargs['position'][1]
        camera.location.z=kwargs['position'][2]
        
    def get_camera_rotation(self, **kwargs):
        camera=bpy.data.objects[kwargs['name_obj']]
        res=[camera.rotation_euler.x,
             camera.rotation_euler.y,
             camera.rotation_euler.z]
        self.server.send_answer(kwargs['connection'], res)
    
    def set_camera_rotation(self, **kwargs):
        camera=bpy.data.objects[kwargs['name_obj']]
        camera.rotation_euler.x=kwargs['rotation'][0]
        camera.rotation_euler.y=kwargs['rotation'][1]
        camera.rotation_euler.z=kwargs['rotation'][2]
        
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
        
        

