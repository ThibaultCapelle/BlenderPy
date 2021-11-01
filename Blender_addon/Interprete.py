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
    
    def assign_constraint(self, connection=None,
                          key=None,
                          const_name=None,
                          parent_name=None,
                          val=None,
                          **kwargs):
        if key=='target':
            val=bpy.data.objects[val]
        setattr(bpy.data.objects[parent_name].constraints[const_name],key, val)
    
    def set_modifier_property(self, connection=None,
                          key=None,
                          parent_name_obj=None,
                          parent_name=None,
                          value=None,
                          **kwargs):
        if isinstance(value, dict):
            value=bpy.data.objects[value['name_obj']]
        setattr(bpy.data.objects[parent_name_obj].modifiers[parent_name],key, value)
    
    def get_modifier_property(self, connection=None,
                          key=None,
                          parent_name_obj=None,
                          parent_name=None,
                          **kwargs):
        res=getattr(bpy.data.objects[parent_name_obj].modifiers[parent_name], key)
        if isinstance(res, bpy.types.Object):
            self.server.send_answer(connection, 
                                dict({'name_obj':res.name}))
        else:
            self.server.send_answer(connection, res)
    
    def set_constraint_property(self, connection=None,
                          key=None,
                          parent_name_obj=None,
                          parent_name=None,
                          value=None,
                          **kwargs):
        if isinstance(value, dict):
            value=bpy.data.objects[value['name_obj']]
        setattr(bpy.data.objects[parent_name_obj].constraints[parent_name],key, value)
    
    def get_constraint_property(self, connection=None,
                          key=None,
                          parent_name_obj=None,
                          parent_name=None,
                          **kwargs):
        res=getattr(bpy.data.objects[parent_name_obj].constraints[parent_name], key)
        if isinstance(res, bpy.types.Object):
            self.server.send_answer(connection, 
                                dict({'name_obj':res.name}))
        else:
            self.server.send_answer(connection, res)
    
    def create_constraint(self, connection=None, **kwargs):
        constraint=Constraint(**kwargs)
        self.server.send_answer(connection, 
                                constraint.name)
    
    def create_modifier(self, connection=None, **kwargs):
        modifier=Modifier(**kwargs)
        self.server.send_answer(connection, 
                                modifier.name)
        
    def create_mesh(self, points=None, cells=None, name=None,
             thickness=None, subdivide=1, connection=None):
        obj = Object(name, points, cells, thickness, subdivide=subdivide)
        self.server.send_answer(connection, 
                                [obj.name_obj, obj.name_msh])
    
    def create_shadernode(self, connection=None, **kwargs):
        node=ShaderNode(**kwargs)
        self.server.send_answer(connection, 
                                node.name)
    
    def set_shadernode_input(self, material_name=None, 
                             from_name=None,
                             from_key=None,
                             value=None,
                             key=None,
                             parent_name=None,
                             connection=None, **kwargs):
        mat=bpy.data.materials[material_name]
        to_socket=mat.node_tree.nodes[from_name].inputs[from_key]
        if key is None:
            to_socket.default_value=value
        else:
            from_socket=mat.node_tree.nodes[parent_name].outputs[key]
            mat.node_tree.links.new(from_socket,
                                    to_socket)
    
    def set_shadernode_property(self, material_name=None, 
                             from_name=None,
                             from_key=None,
                             value=None,
                             parent_name=None,
                             connection=None, **kwargs):
        mat=bpy.data.materials[material_name]
        node=mat.node_tree.nodes[from_name]
        if 'path' in kwargs.keys():
            value=bpy.data.images.load(kwargs['path'], check_existing=True)
        setattr(node, from_key, value)
        
    def get_shadernode_property(self, key=None, 
                             material_name=None, 
                             name=None,
                             connection=None, **kwargs):
        mat=bpy.data.materials[material_name]
        node=mat.node_tree.nodes[name]
        res=getattr(node, key)
        self.server.send_answer(connection,
                                    res)
    
    def set_shadersocket_property(self, material_name=None, 
                                  key=None,
                             socket_key=None,
                             value=None,
                             parent_name=None,
                             connection=None, **kwargs):
        mat=bpy.data.materials[material_name]
        node=mat.node_tree.nodes[parent_name]
        socket=node[socket_key]
        setattr(socket, key, value)
        
    def get_shadersocket_property(self, material_name=None, 
                                  key=None,
                                  socket_key=None,
                                  parent_name=None,
                                  connection=None, **kwargs):
        mat=bpy.data.materials[material_name]
        node=mat.node_tree.nodes[parent_name]
        socket=node[socket_key]
        res=getattr(socket, key)
        self.server.send_answer(connection,
                                    res)
    
    def set_light_property(self,key=None,
                             value=None,
                             parent_name=None,
                             connection=None, **kwargs):
        light=bpy.data.lights[parent_name]
        setattr(light, key, value)
        
    def get_light_property(self, key=None,
                                  parent_name=None,
                                  connection=None, **kwargs):
        light=bpy.data.lights[parent_name]
        res=getattr(light, key)
        self.server.send_answer(connection,
                                    res)
    
    def set_object_property(self,key=None,
                             value=None,
                             parent_name=None,
                             connection=None, **kwargs):
        obj=bpy.data.objects[parent_name]
        setattr(obj, key, value)
        
    def get_object_property(self, key=None,
                                  parent_name=None,
                                  connection=None, **kwargs):
        obj=bpy.data.objects[parent_name]
        res=getattr(obj, key)
        self.server.send_answer(connection,
                                    res)
    
    def set_shadernode_output(self, material_name=None, 
                             from_name=None,
                             from_key=None,
                             value=None,
                             key=None,
                             parent_name=None,
                             connection=None, **kwargs):
        print((from_name, from_key, parent_name, key))
        mat=bpy.data.materials[material_name]
        from_socket=mat.node_tree.nodes[from_name].outputs[from_key]
        to_socket=mat.node_tree.nodes[parent_name].inputs[key]
        mat.node_tree.links.new(from_socket,
                                    to_socket)
    
    def get_shadernode_input(self, key=None, 
                             material_name=None, 
                             name=None,
                             connection=None, **kwargs):
        mat=bpy.data.materials[material_name]
        node=mat.node_tree.nodes[name]
        socket=node.inputs[key]
        if len(socket.links)==0:
            self.server.send_answer(connection,
                                    dict({'parent':mat.name,
                                          'name':node.name,
                                          'socket_name':socket.name,
                                          'shader_socket_type':'input'}))
        else:
            input_node=socket.links[0].from_node
            input_socket=socket.links[0].from_socket
            self.server.send_answer(connection,
                                    dict({'parent':mat.name,
                                          'name':input_node.name,
                                          'socket_name':input_socket.name,
                                          'shader_socket_type':'output'}))
    
    def get_shadernode_output(self, key=None, 
                             material_name=None, 
                             name=None,
                             connection=None, **kwargs):
        mat=bpy.data.materials[material_name]
        node=mat.node_tree.nodes[name]
        socket=node.outputs[key]
        #if len(socket.links)==0:
        self.server.send_answer(connection, 
                                    dict({'parent':mat.name,
                                          'name':node.name,
                                          'socket_name':socket.name,
                                          'shader_socket_type':'output'}))
        '''else:
            output_node=socket.links[0].to_node
            output_socket=socket.links[0].to_socket
            self.server.send_answer(connection,
                                    dict({'parent':mat.name,
                                          'name':output_node.name,
                                          'socket_name':output_socket.name,
                                          'shader_socket_type':'input'}))'''
    
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
    
    def create_curve(self, location=[0,0,0], name="curve",
                     points=[(0,0,0), (1,0,0)], **kwargs):
        new_curve=bpy.data.curves.new(name, 'CURVE')
        new_spline=new_curve.splines.new('POLY')
        new_spline.points[0].co=Vector((points[0][0], 
                         points[0][1],
                         points[0][2],
                         0.))
        new_spline.points.add(len(points)-1)
        for i, p in enumerate(points[1:]):
            new_spline.points[i+1].co=Vector((p[0], p[1], p[2], 0.))
        new_obj=bpy.data.objects.new(name, new_curve)
        new_obj.location.x=location[0]
        new_obj.location.y=location[1]
        new_obj.location.z=location[2]
        
        bpy.data.collections[0].objects.link(new_obj)
        self.server.send_answer(kwargs['connection'], [new_curve.name, new_obj.name])
    
    
    def draw_curve(self, points=None, **kwargs):
        print(bpy.context.scene)
        win      = bpy.context.window
        scr      = win.screen
        areas3d  = [area for area in scr.areas if area.type == 'VIEW_3D']
        region   = [region for region in areas3d[0].regions if region.type == 'WINDOW']
        override = {'window':win,
            'screen':scr,
            'area'  :areas3d[0],
            'region':region,
            'scene' :bpy.context.scene,
            }
        bpy.ops.curve.primitive_nurbs_path_add(radius=1,
                                               enter_editmode=True,
                                               align='WORLD',
                                               location=(0, 0, 0),
                                               scale=(1, 1, 1))
        #bpy.ops.object.mode_set(mode='EDIT_CURVE')
        print(bpy.context.mode)
        stroke=[]
        for point in points:
            stroke.append({"name":"",
                           "location":points,
                           "pressure":1,
                           "size":0,
                           "pen_flip":False,
                           "time":0,
                           "is_start":False})
        bpy.ops.curve.draw(override,
                           error_threshold=0.042712,
                           fit_method='REFIT',
                           corner_angle=1.22173,
                           use_cyclic=False,
                           stroke=stroke,
                           wait_for_input=False)

    
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
    
    def glowing(self, connection=None, color=[0.8984375, 0.1484375,
                       0.1484375, 1.],
                strength=100, name="glow",
                **kwargs):
        material=bpy.data.materials.get(name)
        Principled_BSDF=material.node_tree.nodes['Principled BSDF']
        emission=material.node_tree.nodes.new(type="ShaderNodeEmission")
        emission.inputs['Color'].default_value= color
        add=material.node_tree.nodes.new(type="ShaderNodeAddShader")
        output=material.node_tree.nodes['Material Output']
        material.node_tree.links.new(emission.outputs['Emission'],
                                         add.inputs[0])
        material.node_tree.links.new(Principled_BSDF.outputs['BSDF'],
                                         add.inputs[1])
        material.node_tree.links.new(add.outputs['Shader'],
                                         output.inputs['Surface'])
    
    def metallic_texture(self, connection=None, name='metal',
                         Voronoi_scale=3.3,
                         bump_strength=0.458,
                         bump_distance=4.2,
                         noise_scale=36.8,
                         noise_detail=5,
                         noise_scale_rough=1,
                         noise_detail_rough=7,
                         **kwargs):
        material=bpy.data.materials.get(name)
        # Normal input of BDSF
        Texcoords=material.node_tree.nodes.new(type="ShaderNodeTexCoord")
        mapping=material.node_tree.nodes.new(type="ShaderNodeMapping")
        noise_1=material.node_tree.nodes.new(type="ShaderNodeTexNoise")
        voronoi_1=material.node_tree.nodes.new(type="ShaderNodeTexVoronoi")
        coloramp=material.node_tree.nodes.new(type="ShaderNodeValToRGB")
        bump=material.node_tree.nodes.new(type="ShaderNodeBump")
        Principled_BDSF=material.node_tree.nodes['Principled BSDF']
        material.node_tree.links.new(bump.outputs['Normal'],
                                         Principled_BDSF.inputs['Normal'])
        material.node_tree.links.new(coloramp.outputs['Color'],
                                         bump.inputs['Normal'])
        material.node_tree.links.new(voronoi_1.outputs['Color'],
                                         coloramp.inputs['Fac'])
        material.node_tree.links.new(noise_1.outputs['Color'],
                                         voronoi_1.inputs['Vector'])
        material.node_tree.links.new(mapping.outputs['Vector'],
                                         noise_1.inputs['Vector'])
        material.node_tree.links.new(Texcoords.outputs['Object'],
                                         mapping.inputs['Vector'])
        # Roughness input of BDSF
        noise_2=material.node_tree.nodes.new(type="ShaderNodeTexNoise")
        coloramp_2=material.node_tree.nodes.new(type="ShaderNodeValToRGB")
        material.node_tree.links.new(coloramp_2.outputs['Color'],
                                         Principled_BDSF.inputs['Roughness'])
        material.node_tree.links.new(noise_2.outputs['Color'],
                                         coloramp_2.inputs['Fac'])
        
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

    
    def create_light(self, name='light', light_type='POINT',
                     connection=None, power=100, radius=0.2,
                     location=[0,0,0]):
        
        new_light=bpy.data.lights.new(name, light_type)
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
    
    def create_cylinder(self, connection=None,
                        location=None, radius=None, thickness=None,
                        name=None, subdivide=10, Npoints=100, **kwargs):
        points=[location]+[[location[0]+radius*np.cos(theta),
                 location[1]+radius*np.sin(theta),
                 location[2]] for theta in np.linspace(0,2*np.pi, Npoints)]
        cells=[[0,i, (i+1)%len(points)] for i in range(1, len(points))]
        #print([points, cells])
        self.create_mesh(points=points, cells=cells, thickness=thickness,
                         name=name, connection=connection,
                         subdivide=subdivide)
        
        
    def create_cube(self, **kwargs):
        location, size, name, connection=(kwargs['location'], kwargs['size'],
                                          kwargs['name'], kwargs['connection'])
        points=[[location[0]-size/2, location[1]-size/2, location[2]+size/2],
                [location[0]-size/2, location[1]+size/2, location[2]+size/2],
                [location[0]+size/2, location[1]+size/2, location[2]+size/2],
                [location[0]+size/2, location[1]-size/2, location[2]+size/2],
                [location[0]-size/2, location[1]-size/2, location[2]-size/2],
                [location[0]-size/2, location[1]+size/2, location[2]-size/2],
                [location[0]+size/2, location[1]+size/2, location[2]-size/2],
                [location[0]+size/2, location[1]-size/2, location[2]-size/2]]
        cells=[[0,1,2,3],
               [4,5,6,7],
               [0,3,7,4],
               [0,1,5,4],
               [2,3,7,6],
               [1,2,6,5]]
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
        obj.location.x=kwargs['location'][0]
        obj.location.y=kwargs['location'][1]
        obj.location.z=kwargs['location'][2]
    
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

class ShaderNode:
    
    def __init__(self, parent_name=None, shader_type=None, **kwargs):
        self.parent=bpy.data.materials[parent_name]
        self.type=shader_type
        self.node=self.parent.node_tree.nodes.new(self.type)
        self.name=self.node.name

class Constraint:
    
    def __init__(self, parent_name, constraint_type, **kwargs):
        self.parent=bpy.data.objects[parent_name]
        self.type=constraint_type
        self.const=self.parent.constraints.new(self.type)
        self.name=self.const.name

class Modifier:
    
    def __init__(self, parent_name, modifier_type, **kwargs):
        self.parent=bpy.data.objects[parent_name]
        self.type=modifier_type
        self.mod=self.parent.modifiers.new(self.type, self.type)
        self.name=self.mod.name

class Object:
    
    def __init__(self, name, points, cells, thickness, subdivide=1):
        self.subdivide=subdivide
        self.thickness=thickness
        self.name=name
        self.points=points
        self.cells=cells
        self.mesh_data = bpy.data.meshes.new(self.name)
        self.name_msh=self.mesh_data.name
        self.mesh_data.from_pydata(points, [], cells)
        self.mesh_data.update()
    
        self.obj = bpy.data.objects.new(self.name, self.mesh_data)
        
        collection = bpy.context.collection
        collection.objects.link(self.obj)
        self.name_obj=self.obj.name
        print(self.name_obj)
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
        print('entering extrude')
        print(self.thickness)
        if self.thickness is not None:
            print('thickness is not None')
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
            print('I started the extrusion')
            translate_verts = [v for v in extruded['geom'] if isinstance(v, BMVert)]
            up = Vector((0, 0, self.thickness)) 
            bmesh.ops.translate(bm, vec=up, verts=translate_verts) 
            print('extrusion was done')
            for i in range(self.subdivide-1):
                print('I will subdivide')
                bmesh.ops.bisect_plane(bm,
                                           geom=bm.verts[:]+bm.edges[:]+bm.faces[:],
                                           dist=0.001,
                                       plane_co=[0,0,(i+1)*self.thickness/self.subdivide],
                                       plane_no=[0,0,1])
        # Remove doubles 
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001) 
            # Update mesh and free Bmesh 
            bm.normal_update() 
            bm.to_mesh(self.obj.data) 
            bm.free()
        
        

