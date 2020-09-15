import bpy, json

import bmesh 
from mathutils import Vector 
from bmesh.types import BMVert 
import numpy as np

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
        self.server.send_answer(connection, "DONE")
        
    def create_mesh(self, points=None, cells=None, name=None,
             thickness=None, connection=None):
        obj = Object(name, points, cells, thickness)
        self.server.send_answer(connection, 
                                [obj.name_msh, obj.name_msh])
    
    def update_material(self, connection=None, **kwargs):
        material=bpy.data.materials.get(kwargs['name'])
        node=material.node_tree.nodes["Principled BSDF"]
        node.inputs[0].default_value=kwargs['color']
        node.inputs[15].default_value=kwargs['transmission']
        node.inputs[16].default_value=kwargs['use_screen_refraction']
        node.inputs['Alpha'].default_value=kwargs['alpha']
        material.blend_method = kwargs['blend_method']
        material.shadow_method = kwargs['blend_method_shadow']
        material.use_screen_refraction=kwargs['use_screen_refraction']
        if 'roughness' in kwargs.keys():
            node.inputs['Roughness'].default_value=kwargs['roughness']
        if 'metallic' in kwargs.keys():
            node.inputs['Metallic'].default_value=kwargs['metallic']
        if kwargs['use_screen_refraction']:
            bpy.context.scene.eevee.use_ssr = True
            bpy.context.scene.eevee.use_ssr_refraction = True
        print(kwargs)
        material.use_backface_culling=kwargs['use_backface_culling']
    
    def get_cursor_location(self, **kwargs):
        self.server.send_answer(kwargs['connection'], 
                                [bpy.context.scene.cursor.location.x,
                                 bpy.context.scene.cursor.location.y,
                                 bpy.context.scene.cursor.location.z])
    
    def set_cursor_location(self, **kwargs):
        bpy.context.scene.cursor.location.x=kwargs['location'][0]
        bpy.context.scene.cursor.location.y=kwargs['location'][1]
        bpy.context.scene.cursor.location.z=kwargs['location'][2]
        bpy.data.objects[kwargs['name']].select_set(True)
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    
    def z_dependant_color(self, connection=None, **kwargs):
        material=bpy.data.materials.get(kwargs['name'])
        
        ColorRamp=material.node_tree.nodes.new(type="ShaderNodeValToRGB")
        SeparateXYZ=material.node_tree.nodes.new(type="ShaderNodeSeparateXYZ")
        Principled_BDSF=material.node_tree.nodes['Principled BSDF']
        material.node_tree.links.new(ColorRamp.outputs['Color'],
                                     Principled_BDSF.inputs['Base Color'])
        material.node_tree.links.new(ColorRamp.outputs['Alpha'],
                                     Principled_BDSF.inputs['Alpha'])
        for element in ColorRamp.color_ramp.elements[:-1]:
            ColorRamp.color_ramp.elements.remove(element)
        element=ColorRamp.color_ramp.elements[0]
        element.position=kwargs['positions'][0]
        element.color=kwargs['colors'][0]
        for position, color in zip(kwargs['positions'][1:],
                                   kwargs['colors'][1:]):
            new_element=ColorRamp.color_ramp.elements.new(position)
            new_element.color=color
        if 'name_msh' in kwargs.keys():
            msh=bpy.data.meshes.get(kwargs['name_msh'])
            bm=bmesh.new()
            bm.from_mesh(msh)
            
            zmin, zmax=(np.min([v.co.z for v in bm.verts]),
                        np.max([v.co.z for v in bm.verts]))
            bm.free()
            Geometry=material.node_tree.nodes.new(type="ShaderNodeNewGeometry")
            material.node_tree.links.new(Geometry.outputs['Position'],
                                         SeparateXYZ.inputs['Vector'])
            add=material.node_tree.nodes.new(type="ShaderNodeMath")
            add.operation='ADD'
            add.inputs[1].default_value=kwargs['z_offset']
            
            material.node_tree.links.new(SeparateXYZ.outputs['Z'],
                                         add.inputs[0])
            divide=material.node_tree.nodes.new(type="ShaderNodeMath")
            divide.operation='DIVIDE'
            divide.inputs[1].default_value=kwargs['z_scale']
            material.node_tree.links.new(add.outputs[0],
                                         divide.inputs[0])
            material.node_tree.links.new(divide.outputs[0],
                                         ColorRamp.inputs['Fac'])
        else:
            Texcoords=material.node_tree.nodes.new(type="ShaderNodeTexCoord")
            material.node_tree.links.new(Texcoords.outputs['Generated'],
                                         SeparateXYZ.inputs['Vector'])
            material.node_tree.links.new(SeparateXYZ.outputs['Z'],
                                         ColorRamp.inputs['Fac'])
    
    
    def make_oscillations(self, **kwargs):
        scene=bpy.context.scene
        scene.frame_end=kwargs['N_frames']
        scene.frame_start=1
        scene.frame_current=scene.frame_start
        obj=bpy.data.objects[kwargs['name_obj']]
        extension_scale, extension_rotation, extension_motion=([kwargs['target_scale'][i]-kwargs['center_scale'][i] for i in range(3)],
                                                               [kwargs['target_rotation'][i]-kwargs['center_rotation'][i] for i in range(3)],
                                                               [kwargs['target_motion'][i]-kwargs['center_motion'][i] for i in range(3)] 
                                                               )
        if kwargs['Q']==0:
            for i in range(5):
                scene.frame_current=int(i*kwargs['N_frames']/4)
                
                obj.scale.x=kwargs['center_scale'][0]+np.cos(np.pi*i/2)*extension_scale[0]
                obj.scale.y=kwargs['center_scale'][1]+np.cos(np.pi*i/2)*extension_scale[1]
                obj.scale.z=kwargs['center_scale'][2]+np.cos(np.pi*i/2)*extension_scale[2]

                obj.location.x=kwargs['center_motion'][0]+np.cos(np.pi*i/2)*extension_motion[0]
                obj.location.y=kwargs['center_motion'][1]+np.cos(np.pi*i/2)*extension_motion[1]
                obj.location.z=kwargs['center_motion'][2]+np.cos(np.pi*i/2)*extension_motion[2]
            
                obj.rotation_euler.x=kwargs['center_rotation'][0]+np.cos(np.pi*i/2)*extension_rotation[0]
                obj.rotation_euler.y=kwargs['center_rotation'][1]+np.cos(np.pi*i/2)*extension_rotation[1]
                obj.rotation_euler.z=kwargs['center_rotation'][2]+np.cos(np.pi*i/2)*extension_rotation[2]
            
                obj.keyframe_insert("scale")
                obj.keyframe_insert("location")
                obj.keyframe_insert("rotation_euler")
        else:
            Q=kwargs['Q']
            N_frames_per_oscillation=int(kwargs['N_frames']/kwargs['N_oscillations'])
            for i in range(kwargs['N_oscillations']):
                for j in range(4):
                    
                    scene.frame_current=int(i*N_frames_per_oscillation+j*N_frames_per_oscillation/4)
                    damping=(i+float(j)/4)/Q
                    obj.scale.x=kwargs['center_scale'][0]+np.exp(-damping)*np.cos(np.pi*j/2)*extension_scale[0]
                    obj.scale.y=kwargs['center_scale'][1]+np.exp(-damping)*np.cos(np.pi*j/2)*extension_scale[1]
                    obj.scale.z=kwargs['center_scale'][2]+np.exp(-damping)*np.cos(np.pi*j/2)*extension_scale[2]
    
                    obj.location.x=kwargs['center_motion'][0]+np.exp(-damping)*np.cos(np.pi*j/2)*extension_motion[0]
                    obj.location.y=kwargs['center_motion'][1]+np.exp(-damping)*np.cos(np.pi*j/2)*extension_motion[1]
                    obj.location.z=kwargs['center_motion'][2]+np.exp(-damping)*np.cos(np.pi*j/2)*extension_motion[2]
                
                    obj.rotation_euler.x=kwargs['center_rotation'][0]+np.exp(-damping)*np.cos(np.pi*j/2)*extension_rotation[0]
                    obj.rotation_euler.y=kwargs['center_rotation'][1]+np.exp(-damping)*np.cos(np.pi*j/2)*extension_rotation[1]
                    obj.rotation_euler.z=kwargs['center_rotation'][2]+np.exp(-damping)*np.cos(np.pi*j/2)*extension_rotation[2]
                
                    obj.keyframe_insert("scale")
                    obj.keyframe_insert("location")
                    obj.keyframe_insert("rotation_euler")
        self.server.send_answer(kwargs['connection'], "DONE")
            
            
        
        
    def gaussian_laser(self, connection=None, **kwargs):
        W0=kwargs['W0']
        ZR=kwargs['ZR']
        I=kwargs['I']
        material=bpy.data.materials.get(kwargs['name'])
        Texcoords=material.node_tree.nodes.new(type="ShaderNodeTexCoord")
        Texcoords.location.x=-100
        SeparateXYZ=material.node_tree.nodes.new(type="ShaderNodeSeparateXYZ")
        SeparateXYZ.location.x=Texcoords.location.x+Texcoords.width+20
        material.node_tree.links.new(Texcoords.outputs['Generated'],
                                     SeparateXYZ.inputs['Vector'])
        
        
        diffx, diffy, diffz=(material.node_tree.nodes.new(type="ShaderNodeMath"),
                             material.node_tree.nodes.new(type="ShaderNodeMath"),
                             material.node_tree.nodes.new(type="ShaderNodeMath"))
        diffx.location.y=500
        diffy.location.y=0
        diffz.location.y=-500
        diffx.location.x=SeparateXYZ.location.x+SeparateXYZ.width+20
        diffy.location.x=diffx.location.x
        diffz.location.x=diffx.location.x
        for op, coord in zip([diffx, diffy, diffz], ['X', 'Y', 'Z']):
            op.operation='SUBTRACT'
            material.node_tree.links.new(SeparateXYZ.outputs[coord],
                                         op.inputs[0])
            op.inputs[1].default_value=0.5
        
        powx=material.node_tree.nodes.new(type="ShaderNodeMath")
        powx.operation='POWER'
        powx.location.x=diffz.location.x+diffz.width+20
        powx.location.y=200
        powy=material.node_tree.nodes.new(type="ShaderNodeMath")
        powy.operation='POWER'
        powy.location.x=powx.location.x
        powy.location.y=-200
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
        bpy.context.scene.eevee.volumetric_tile_size = '2'

        
    def get_material_names(self, connection=None):
        assert connection is not None
        self.server.send_answer(connection,
                                [item.name for item in bpy.data.materials])

    
    def create_light(self, name='light', connection=None, power=100, radius=0.2,
                     location=[0,0,0]):
        
        new_light=bpy.data.lights.new(name, type='POINT')
        new_obj=bpy.data.objects.new(name, new_light)
        new_obj.location.x=location[0]
        new_obj.location.y=location[1]
        new_obj.location.z=location[2]
        bpy.data.collections[0].objects.link(new_obj)
        new_light.energy=power
        self.server.send_answer(connection, [new_light.name, new_obj.name])
    
    def create_plane(self, **kwargs):
        location, size, name, connection=(kwargs['location'], kwargs['size'],
                                          kwargs['name'], kwargs['connection'])
        points=[[location[0]-size/2, location[1]-size/2, location[2]],
                [location[0]-size/2, location[1]+size/2, location[2]],
                [location[0]+size/2, location[1]+size/2, location[2]],
                [location[0]+size/2, location[1]-size/2, location[2]]]
        cells=[[0,1,2,3]]
        self.create_mesh(points=points, cells=cells, name=name, connection=connection)
        
    def create_camera(self, **kwargs):
        location, rotation, name=kwargs['location'], kwargs['rotation'], kwargs['name']
        
        new_cam=bpy.data.cameras.new(name)
        new_obj=bpy.data.objects.new(name, new_cam)
        new_obj.location.x=location[0]
        new_obj.location.y=location[1]
        new_obj.location.z=location[2]
        
        new_obj.rotation_euler.x=rotation[0]
        new_obj.rotation_euler.y=rotation[1]
        new_obj.rotation_euler.z=rotation[2]
        
        bpy.data.collections[0].objects.link(new_obj)
        self.server.send_answer(kwargs['connection'], [new_cam.name, new_obj.name])
    
    def get_camera_position(self, **kwargs):
        camera=bpy.data.objects[kwargs['name_obj']]
        res=[camera.location.x,
             camera.location.y,
             camera.location.z]
        self.server.send_answer(kwargs['connection'], res)
    
    def get_light_position(self, **kwargs):
        light=bpy.data.objects[kwargs['name_obj']]
        res=[light.location.x,
             light.location.y,
             light.location.z]
        self.server.send_answer(kwargs['connection'], res)
    
    def get_light_power(self, **kwargs):
        light=bpy.data.lights[kwargs['name']]
        self.server.send_answer(kwargs['connection'], light.energy)
    
    def set_light_power(self, **kwargs):
        light=bpy.data.lights[kwargs['name']]
        light.energy=kwargs['power']
    
    def set_camera_position(self, **kwargs):
        camera=bpy.data.objects[kwargs['name_obj']]
        camera.location.x=kwargs['position'][0]
        camera.location.y=kwargs['position'][1]
        camera.location.z=kwargs['position'][2]
    
    def set_light_position(self, **kwargs):
        light=bpy.data.objects[kwargs['name_obj']]
        light.location.x=kwargs['position'][0]
        light.location.y=kwargs['position'][1]
        light.location.z=kwargs['position'][2]
        
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
        
    def get_object_rotation(self, **kwargs):
        obj=bpy.data.objects[kwargs['name_obj']]
        res=[obj.rotation_euler.x,
             obj.rotation_euler.y,
             obj.rotation_euler.z]
        self.server.send_answer(kwargs['connection'], res)
    
    def set_object_rotation(self, **kwargs):
        obj=bpy.data.objects[kwargs['name_obj']]
        obj.rotation_euler.x=kwargs['rotation'][0]
        obj.rotation_euler.y=kwargs['rotation'][1]
        obj.rotation_euler.z=kwargs['rotation'][2]
    
    def get_object_location(self, **kwargs):
        obj=bpy.data.objects[kwargs['name_obj']]
        res=[obj.location.x,
             obj.location.y,
             obj.location.z]
        self.server.send_answer(kwargs['connection'], res)
    
    def set_object_location(self, **kwargs):
        obj=bpy.data.objects[kwargs['name_obj']]
        obj.rotation_euler.x=kwargs['location'][0]
        obj.rotation_euler.y=kwargs['location'][1]
        obj.rotation_euler.z=kwargs['location'][2]
    
    def get_object_scale(self, **kwargs):
        obj=bpy.data.objects[kwargs['name_obj']]
        res=[obj.scale.x,
             obj.scale.y,
             obj.scale.z]
        self.server.send_answer(kwargs['connection'], res)
    
    def set_object_scale(self, **kwargs):
        obj=bpy.data.objects[kwargs['name_obj']]
        obj.scale.x=kwargs['scale'][0]
        obj.scale.y=kwargs['scale'][1]
        obj.scale.z=kwargs['scale'][2]
        
    def get_material(self, name, connection=None):
        self.server.send_answer(connection, bpy.data.materials.get(name).name)
    
    def create_material(self, name, connection=None):
        self.server.send_answer(connection, self.new_material(name).name)
    
    def new_material(self, name):
        mat=bpy.data.materials.new(name)
        mat.use_nodes = True
        self.nodes = mat.node_tree.nodes
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
        
        

