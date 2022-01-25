import bpy
import time

import bmesh 
from mathutils import Vector
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
        for block in bpy.data.objects:
            bpy.data.objects.remove(block, do_unlink=True)
        for block in bpy.data.lights:
            bpy.data.lights.remove(block, do_unlink=True)
            time.sleep(0.01)
        for block in bpy.data.cameras:
            bpy.data.cameras.remove(block, do_unlink=True)
            time.sleep(0.01)
        for block in bpy.data.meshes:
            bpy.data.meshes.remove(block, do_unlink=True)
            time.sleep(0.01)
        for block in bpy.data.materials:
            bpy.data.materials.remove(block, do_unlink=True)
            time.sleep(0.01)
        for block in bpy.data.textures:
            bpy.data.textures.remove(block, do_unlink=True)
            time.sleep(0.01)
        for block in bpy.data.images:
            bpy.data.images.remove(block, do_unlink=True)
            time.sleep(0.01)
        self.server.send_answer(connection, "DONE")
    
    def remove_object(self, connection=None, name_obj=None, **kwargs):
        bpy.data.objects.remove(bpy.data.objects[name_obj], do_unlink=True)
    
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
        self.server.send_answer(connection, 'FINISHED')
    
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
        self.server.send_answer(connection, 'FINISHED')
    
    def get_camera_property(self, connection=None,
                          key=None,
                          parent_name=None,
                          **kwargs):
        res=getattr(bpy.data.cameras[parent_name], key)
        self.server.send_answer(connection, res)
    
    def set_camera_property(self, connection=None,
                          key=None,
                          parent_name=None,
                          value=None,
                          **kwargs):
        setattr(bpy.data.cameras[parent_name],key, value)
        self.server.send_answer(connection, 'FINISHED')
    
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
        self.server.send_answer(connection, 'FINISHED')
    
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
        elif isinstance(value, dict):
            if from_key=='color_ramp':
                for element in node.color_ramp.elements[:-1]:
                    node.color_ramp.elements.remove(element)
                element=node.color_ramp.elements[0]
                element.position=value['positions'][0]
                element.color=value['colors'][0]
                for position, color in zip(value['positions'][1:],
                                           value['colors'][1:]):
                    new_element=node.color_ramp.elements.new(position)
                    new_element.color=color
        else:
            setattr(node, from_key, value)
        self.server.send_answer(connection, 'FINISHED')
        
    def get_shadernode_property(self, key=None, 
                             material_name=None, 
                             name=None,
                             connection=None, **kwargs):
        mat=bpy.data.materials[material_name]
        node=mat.node_tree.nodes[name]
        res=getattr(node, key)
        if isinstance(res, bpy.types.ColorRamp):
            res=[(el.position, [el.color[0], el.color[1],
                                el.color[2], el.color[3]])\
                 for el in res.elements]
        self.server.send_answer(connection,
                                    res)
    
    def set_shadersocket_property(self, material_name=None, 
                                  key=None,
                             socket_key=None,
                             value=None,
                             parent_name=None,
                             shader_socket_type=None,
                             connection=None, **kwargs):
        mat=bpy.data.materials[material_name]
        node=mat.node_tree.nodes[parent_name]
        if shader_socket_type=='input':
            socket=node.inputs[socket_key]
        elif shader_socket_type=='output':
            socket=node.outputs[socket_key]
        setattr(socket, key, value)
        self.server.send_answer(connection, 'FINISHED')
        
    def get_shadersocket_property(self, material_name=None, 
                                  key=None,
                                  socket_key=None,
                                  parent_name=None,
                                  shader_socket_type=None,
                                  connection=None, **kwargs):
        mat=bpy.data.materials[material_name]
        node=mat.node_tree.nodes[parent_name]
        if shader_socket_type=='input':
            socket=node.inputs[socket_key]
        elif shader_socket_type=='output':
            socket=node.outputs[socket_key]
        res=getattr(socket, key)
        self.server.send_answer(connection,
                                    res)
    
    def set_light_property(self,key=None,
                             value=None,
                             parent_name=None,
                             connection=None, **kwargs):
        light=bpy.data.lights[parent_name]
        if hasattr(light, key):
            setattr(light, key, value)
        self.server.send_answer(connection, 'FINISHED')
        
    def get_light_property(self, key=None,
                                  parent_name=None,
                                  connection=None, **kwargs):
        light=bpy.data.lights[parent_name]
        if hasattr(light, key):
            res=getattr(light, key)
        else:
            res=None
        self.server.send_answer(connection,
                                    res)
    
    def set_object_property(self,key=None,
                             value=None,
                             parent_name_obj=None,
                             connection=None, **kwargs):
        obj=bpy.data.objects[parent_name_obj]
        if key=='location' and isinstance(value, dict):
            for k,v in value.items():
                setattr(obj.location, k, v)
        else:
            if hasattr(obj, key):
                setattr(obj, key, value)
        self.server.send_answer(connection, 'FINISHED')
        
    def get_object_property(self, key=None,
                                  parent_name_obj=None,
                                  connection=None, **kwargs):
        obj=bpy.data.objects[parent_name_obj]
        if hasattr(obj, key):
            res=getattr(obj, key)
        else:
            res=None
        self.server.send_answer(connection,
                                    res)
    
    def create_collection(self, connection=None,
                          name=None):
        col=bpy.data.collections.new(name)
        self.server.send_answer(connection, col.name)
    
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
        self.server.send_answer(connection, 'FINISHED')
    
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
    
    def apply_modifier(self, name=None,
                       name_obj=None,
                       connection=None,
                       modifier_type='BOOLEAN',
                       **kwargs):
        obj=bpy.data.objects[name_obj]
        ctx = bpy.context.copy()
        ctx['object'] = obj
        ctx['modifier']= obj.modifiers[name]
        bpy.ops.object.modifier_apply(ctx, modifier=modifier_type)
        self.server.send_answer(connection,
                                'FINISHED')
    
    def get_shadernode_output(self, key=None, 
                             material_name=None, 
                             name=None,
                             connection=None, **kwargs):
        mat=bpy.data.materials[material_name]
        node=mat.node_tree.nodes[name]
        socket=node.outputs[key]
        self.server.send_answer(connection, 
                                    dict({'parent':mat.name,
                                          'name':node.name,
                                          'socket_name':socket.name,
                                          'shader_socket_type':'output'}))
    
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
    
    def create_lattice(self, connection=None, name="lattice",
                       **kwargs):
        new_lattice=bpy.data.lattices.new(name)
        new_obj=bpy.data.objects.new(name, new_lattice)
        bpy.data.collections[0].objects.link(new_obj)
        self.server.send_answer(connection, [new_lattice.name, new_obj.name])
    
    def get_lattice_points(self, connection=None, name=None,
                              **kwargs):
        lat=bpy.data.lattices[name]
        return [[p.co.x, p.co.y, p.co.z] for p in lat.points]
    
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
    
    def get_curve_points(self, connection=None, name_obj=None, name=None, **kwargs):
        curve=bpy.data.curves[name].splines[0]
        self.server.send_answer(connection, [[v.co.x, v.co.y, v.co.z] for v in curve.points.values()])
    
    def set_curve_points(self, name=None, points=None, **kwargs):
        curve=bpy.data.curves[name].splines[0]
        for co,v in zip(points, curve.points.values()):
            v.co=co+[0.]
    
    def get_scene_property(self, key=None,
                           connection=None, **kwargs):
        scene=bpy.context.scene
        if isinstance(key, list):
            while(len(key)>1):
                scene=getattr(scene, key.pop(0))
            key=key[0]
        self.server.send_answer(connection, getattr(scene, key))
    
    def set_scene_property(self, key=None, value=None,
                           connection=None, **kwargs):
        scene=bpy.context.scene
        if isinstance(key, list):
            while(len(key)>1):
                scene=getattr(scene, key.pop(0))
            key=key[0]
        setattr(scene, key, value)
        self.server.send_answer(connection, 'FINISHED')
    
    def get_vertices(self, name_msh=None,
                     connection=None, **kwargs):
        self.server.send_answer(connection,
                                [[v.co.x, v.co.y, v.co.z] for v in bpy.data.meshes[name_msh].vertices.values()])
        
    def set_vertices(self, name_msh=None,
                     connection=None, val=None, **kwargs):
        for co,v in zip(val, bpy.data.meshes[name_msh].vertices.values()):
            v.co=co
    
    def insert_keyframe_mesh(self, name_msh=None,
                     connection=None, frame='current', 
                     waiting_time_between_points=0.01,
                     **kwargs):
        if frame=='current':
            frame=bpy.context.scene.frame_current
        for i,v in enumerate(bpy.data.meshes[name_msh].vertices.values()):
            print('keyframing point nr {:}'.format(i))
            v.keyframe_insert('co', frame=frame)
            time.sleep(waiting_time_between_points)
        self.server.send_answer(connection, 'FINISHED')
    
    def insert_keyframe_object(self, name_obj=None,
                               connection=None, frame='current',
                               key=None, **kwargs):
        if frame=='current':
            frame=bpy.context.scene.frame_current
        ob=bpy.data.objects[name_obj]
        ob.keyframe_insert(key, frame=frame)
        self.server.send_answer(connection, 'FINISHED')
    
    def insert_keyframe_constraint(self, name_obj=None, name=None,
                               connection=None, frame='current',
                               key=None, **kwargs):
        const=Constraint(parent_name=name_obj, name=name)
        const.insert_keyframe(key, frame=frame)
        self.server.send_answer(connection, 'FINISHED')
    
    def insert_keyframe_shadersocket(self, connection=None,
                                     material_name=None,
                                     parent_name=None,
                                     key=None,
                                     key_to_keyframe=None,
                                     shader_socket_type=None,
                                     frame='current',
                                     **kwargs):
        print(frame)
        if frame=='current':
            frame=bpy.context.scene.frame_current
        mat=bpy.data.materials[material_name]
        time.sleep(0.5)
        node=mat.node_tree.nodes[parent_name]
        time.sleep(0.5)
        if shader_socket_type=='input':
            socket=node.inputs[key]
        elif shader_socket_type=='output':
            socket=node.outputs[key]
        time.sleep(0.5)
        print(socket.keyframe_insert(key_to_keyframe, frame=frame))
        self.server.send_answer(connection, 'FINISHED')
            
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

        
    def get_material_names(self, connection=None):
        assert connection is not None
        self.server.send_answer(connection,
                                [item.name for item in bpy.data.materials])
    
    def remove_shader(self, parent_name=None, name=None, **kwargs):
        mat=bpy.data.materials[parent_name]
        node=mat.node_tree.nodes[name]
        mat.node_tree.nodes.remove(node)
    
    def duplicate(self, connection=None, name_obj=None):
        ob=bpy.data.objects[name_obj]
        ob_copy=ob.copy()
        bpy.data.collections[0].objects.link(ob_copy)
        self.server.send_answer(connection, ob_copy.name)
       
    def create_light(self, name='light', light_type='POINT',
                     connection=None):
        new_light=bpy.data.lights.new(name, light_type)
        new_obj=bpy.data.objects.new(name, new_light)
        bpy.data.collections[0].objects.link(new_obj)
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
        bpy.context.scene.camera=new_obj
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
    
    def assign_material(self, name_obj=None, name_mat=None, **kwargs):
        #bpy.data.objects[kwargs['name_obj']].select_set(True)
        #bpy.context.view_layer.objects.active = bpy.data.objects[kwargs['name_obj']]
        ob = bpy.data.objects[name_obj]
        ob.data.materials.clear()
        if isinstance(name_mat, list):
            for name in name_mat:
                mat=bpy.data.materials.get(name)
                ob.data.materials.append(mat)
        else:
            ob.data.materials.append(bpy.data.materials.get(name_mat))
            
    def cut_mesh(self, name_msh=None, planes_co=None,
                 planes_no=None, **kwargs):
        mesh=bpy.data.meshes[name_msh]
        bm = bmesh.new()
        bm.from_mesh(mesh)
        print('Nverts0: {:}'.format(len(bm.verts)))
        for i, (co, no) in enumerate(zip(planes_co, planes_no)):
            print('slicing plane number {:}'.format(i))
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:],
                                   dist=1e-6,
                                   plane_co=co, plane_no=no)
        print('Nverts1: {:}'.format(len(bm.verts)))
        bm.normal_update() 
        bm.to_mesh(mesh) 
        bm.free()



def Material(message):
    assert message['class']=='Material'
    
class KeyframePossibleObject:
    
    def __init__(self, ob, **kwargs):
        self.ob=ob
    
    def insert_keyframe(self, key, frame='current'):
        if frame=='current':
            frame=bpy.context.scene.frame_current
        if hasattr(self.ob, key) and hasattr(self.ob, 'keyframe_insert'):
            self.ob.keyframe_insert(key, frame=frame)

class ShaderNode:
    
    def __init__(self, parent_name=None, shader_type=None, **kwargs):
        self.parent=bpy.data.materials[parent_name]
        self.type=shader_type
        self.node=self.parent.node_tree.nodes.new(self.type)
        self.name=self.node.name

class Constraint(KeyframePossibleObject):
    
    def __init__(self, parent_name=None, constraint_type=None,
                 name=None, **kwargs):
        self.parent=bpy.data.objects[parent_name]
        if name is None:
            self.type=constraint_type
            self.const=self.parent.constraints.new(self.type)
            self.name=self.const.name
        else:
            self.name=name
            ob=bpy.data.objects[parent_name].constraints[name]
            super().__init__(ob)

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
        if self.thickness is not None and self.thickness>0 :
            mesh=bpy.data.meshes[self.name_msh]
            bm = bmesh.new()   # create an empty BMesh
            bm.from_mesh(mesh)
            r = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
            verts = [e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)]
            bmesh.ops.translate(bm, vec=Vector((0,0,self.thickness)), verts=verts)
            print('extrusion was done')
            for i in range(self.subdivide-1):
                print('I will subdivide')
                bmesh.ops.bisect_plane(bm,
                                           geom=bm.verts[:]+bm.edges[:]+bm.faces[:],
                                           dist=0.001,
                                       plane_co=[0,0,(i+1)*self.thickness/self.subdivide],
                                       plane_no=[0,0,1])
            # Update mesh and free Bmesh 
            bm.normal_update() 
            bm.to_mesh(mesh) 
            bm.free()
        
        

