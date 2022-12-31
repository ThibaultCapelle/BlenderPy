# -*- coding: utf-8 -*-
"""
Created on Wed Aug 26 09:56:27 2020

@author: Thibault
"""

import socket
import json
import time
from BlenderPy.parsing import Expression
import numpy as np
HOST = '127.0.0.1'
PORT = 20000

def delete_all():
    '''Delete all objects, meshes, cameras, ...'''
    assert Communication.ask('delete_all')=="DONE"
    
class Communication:
    '''A static class for communicating with the server'''

    @staticmethod
    def send(message, **kwargs):
        '''Send a message to the Blender Server
        
        Take a message, format it, encode it with its length at the
        beginning, and send it to the Blender server.
        
        Parameters:
            message: string to send
        
        Return:
            None
        '''
        message=Communication.parse(message, **kwargs)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(('{:010x}'.format(len(message))+message).encode())
    
    @staticmethod
    def receive_all(sock, n):
        '''Receive a message of a given length from the server.
        
        After having found its length, receive packets until
        the amount of data is equal to this length
        
        Parameters:
            sock: socket to read from
            n: expected length of the data
        
        Return:
            data: the raw data
        '''
        data = bytearray()
        i=1
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
            i+=1
        return data  
    
    @staticmethod
    def ask(message, **kwargs):
        '''Ask a question to the Blender Server.
        
        Open a socket,encode properly the data to send like the 
        send method with the length of the data at the beginning,
        then send the data, receive the beginning of the answer
        which contains the length of the answer, and then call
        receive_all to receive the data.
        Then, return the json extracted dictionnary that contain
        the data.
        
        Parameters:
            message: the question to ask
        
        Return:
            the data
        '''
        message=Communication.parse(message, **kwargs)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(('{:010x}'.format(len(message))+message).encode())
            raw_msglen = s.recv(10)
            msglen = int(raw_msglen.decode(),16)
            data=Communication.receive_all(s, msglen)
            return json.loads(data)['content']
    
    @staticmethod
    def parse(message, **kwargs):
        '''Format a message to be sent to the Blender Server.
        
        Parameters:
            message: the question to ask
        
        Return:
            the data
        '''
        res=dict()
        res['command']=message
        res['kwargs']=kwargs
        msg=json.dumps(res)
        return msg
    
class GeometricEntity:
    '''a class encompassing the geometric absolute positioning
    of vertices of meshes'''
    
    def set_origin(self, position):
        '''set the origin of a mesh to a position. The vertices
        position will have this point as a new origin
        
        Parameters:
            position: the position you want to set to
        
        Returns:
            None
        '''
        verts=self.vertices_absolute
        x,y,z=self.x, self.y, self.z
        verts[:,0]-=position[0]-x
        verts[:,1]-=position[1]-y
        verts[:,2]-=position[2]-z
        self.vertices_absolute=verts
        self.location=position
    
    @property
    def vertices_absolute(self):
        '''get the position of the vertices in
        absolute coordinates
        
        Parameters:
            None
        
        Returns:
            a numpy array representing the absolute coordinates
        '''
        mat=self.matrix_world
        verts=self.vertices
        verts_4D=np.transpose(np.hstack([verts, np.ones((len(verts),1))]))
        return np.transpose(np.dot(mat, verts_4D))
    
    @vertices_absolute.setter
    def vertices_absolute(self, val):
        '''set the position of the vertices in
        absolute coordinates
        
        Parameters:
            val: a numpy array or a list representing the desired positions
        
        Returns:
            None
        '''
        mat=np.linalg.inv(self.matrix_world)
        if np.array(val).shape[1]!=4:
            val=np.hstack([np.array(val), np.ones((len(val),1))])
        self.vertices=np.transpose(np.dot(mat, np.transpose(val)))[:,:3]
        
    @property
    def xmin(self):
        '''minimum x position'''
        
        return np.min(self.vertices_absolute[:,0])
    
    @property
    def xmax(self):
        '''maximum x position'''
        return np.max(self.vertices_absolute[:,0])
    
    @property
    def ymin(self):
        '''minimum y position'''
        return np.min(self.vertices_absolute[:,1])
    
    @property
    def ymax(self):
        '''maximum y position'''
        return np.max(self.vertices_absolute[:,1])
    
    @property
    def zmin(self):
        '''minimum z position'''
        return np.min(self.vertices_absolute[:,2])
    
    @property
    def zmax(self):
        '''maximum z position'''
        return np.max(self.vertices_absolute[:,2])
    
    @xmin.setter
    def xmin(self, val):
        self.x+=val-self.xmin
    
    @ymin.setter
    def ymin(self, val):
        self.y+=val-self.ymin
        
    @zmin.setter
    def zmin(self, val):
        self.z+=val-self.zmin
        
    @xmax.setter
    def xmax(self, val):
        self.x+=val-self.xmax
        
    @ymax.setter
    def ymax(self, val):
        self.y+=val-self.ymax
        
    @zmax.setter
    def zmax(self, val):
        self.z+=val-self.zmax
    
    @property
    def center(self):
        '''absolute center'''
        return np.array([0.5*(self.xmin+self.xmax),
                         0.5*(self.ymin+self.ymax),
                         0.5*(self.zmin+self.zmax)])
    
    @center.setter
    def center(self, val):
        center=self.center
        self.x+=val[0]-center[0]
        self.y+=val[1]-center[1]
        self.z+=val[2]-center[2]
    
    @property
    def dx(self):
        '''Absolute x extension'''
        return self.xmax-self.xmin
    
    @property
    def dy(self):
        '''Absolute y extension'''
        return self.ymax-self.ymin
    
    @property
    def dz(self):
        '''Absolute z extension'''
        return self.zmax-self.zmin
    
    
    
class Scene:
    '''Class representing a scene. Used for changing the frame numbers,
    and render properties'''
    
    def __init__(self, use_bloom=True, volumetric_tile_size=2,
                 frame_current=1, frame_start=1,
                 frame_end=250):
        self._properties=PropertyDict(func='scene_property')
        self.use_bloom=use_bloom
        self.volumetric_tile_size=volumetric_tile_size
        self.frame_current=frame_current
        self.frame_start=frame_start
        self.frame_end=frame_end
    
    @property
    def volumetric_tile_size(self):
        '''for the eevee render, change the tile size.
        It should be a power of two, and the lowest is 2, 
        which corresponds to the finest representation of
        an emission volume'''
        return int(self._properties[['eevee', 'volumetric_tile_size']])
    
    @volumetric_tile_size.setter
    def volumetric_tile_size(self, val):
        self._properties[['eevee', 'volumetric_tile_size']]=str(val)
    
    @property
    def use_bloom(self):
        '''for the eevee render, activate or not the bloom,
        which creates a "halo" around emission materials'''
        return self._properties[['eevee', 'use_bloom']]
    
    @use_bloom.setter
    def use_bloom(self, val):
        self._properties[['eevee', 'use_bloom']]=val
    
    @property
    def frame_current(self):
        '''current frame'''
        return self._properties['frame_current']
    
    @frame_current.setter
    def frame_current(self, val):
        self._properties['frame_current']=val
        
    @property
    def frame_start(self):
        '''first frame number'''
        return self._properties['frame_start']
    
    @frame_start.setter
    def frame_start(self, val):
        self._properties['frame_start']=val
        
    @property
    def frame_end(self):
        '''last frame number'''
        return self._properties['frame_end']
    
    @frame_end.setter
    def frame_end(self, val):
        self._properties['frame_end']=val

class ShaderDict(dict):
    '''Class representing the Shadernodes inputs, outputs
    and properties. It rewrites the setter and getter
    of the dict class to use the properties as a dictionary 
    with the server'''
    
    def __init__(self, name, material_name, func, **kwargs):
        super().__init__()
        self.name=name
        self.material_name=material_name
        self.func=func
        self.params=kwargs
        
    def __setitem__(self, key, value):
        kwargs=self.params.copy()
        if hasattr(value, 'to_dict'):
            kwargs.update(value.to_dict(material_name=self.material_name,
                                        from_name=self.name,
                                       from_key=key))
            Communication.ask('set_'+self.func, **kwargs)
        else:
            kwargs.update(dict({'material_name':self.material_name,
                                'from_name':self.name,
                                'from_key':key,
                                'value':value}))
            Communication.ask('set_'+self.func, **kwargs)
    
    def __getitem__(self, key):
        kwargs=self.params.copy()
        kwargs.update(dict({'material_name':self.material_name,
                     'name':self.name,
                     'key':key}))
        res=Communication.ask('get_'+self.func, **kwargs)
        if isinstance(res, dict):
            node=ShaderNode(**res)
            return ShaderSocket(material_parent=node.parent_name,
                                parent=node, 
                                key=res['socket_name'],
                                shader_socket_type=res['shader_socket_type'])
        else:
            return res

class ShaderSocket:
    '''Class representing the ShaderSocket of a ShaderNode'''
    
    def __init__(self, material_parent=None, shader_socket_type='input',
                 parent=None, key=None, value=None, **kwargs):
        '''
        Parameters:
            material_parent: a Material object
            
            shader_socket_type: either 'input' or 'output'
            
            parent: the ShaderNode this socket belongs to
            
            key: the key of the socket
            
            value: the value of the socket
        '''
            
        assert isinstance(parent, ShaderNode)
        self.material_parent=material_parent
        self.parent=parent
        self.key=key
        self.value=value
        self.shader_socket_type=shader_socket_type
        self._properties=PropertyDict(self.parent.name,
                                      '', func='shadersocket_property',
                                      **self.to_dict(socket_key=self.key))
    
    def to_dict(self, **kwargs):
        '''returns a dictionnary representing the ShaderSocket
        and extra parameters with kwargs'''
        params=dict({'material_name':self.material_parent,
                     'parent_name':self.parent.name,
                     'shader_socket_type':self.shader_socket_type,
                     'key':self.key,
                     'value':self.value})
        params.update(kwargs)
        return params
    
    def insert_keyframe(self, key, frame='current'):
        '''insert a keyframe for this socket for the parameter 'key' at
        the frame 'frame' '''
        Communication.ask('insert_keyframe_shadersocket',
                   **self.to_dict(key_to_keyframe=key, 
                                  frame=frame))
    
    @property
    def properties(self):
        '''a PropertyDict to get and set properties of this ShaderSocket'''
        return self._properties
        
class ShaderNode:
    '''Class representing a ShaderNode of a Material'''
    
    def __init__(self, parent=None, shader_type='Emission',
                 name=None, **kwargs):
        '''
        Parameters:
            parent: a Material object
            
            shader_type: the type of ShaderNode. Can be 'Emission',
            'Add', 'Math', 'Texture_coordinates', 'Separate_XYZ',
            'Combine_XYZ', 'Principled BSDF', 'Material Output',
            'Image', 'Glossy', 'Noise', 'Color_Ramp'
            
            name: the name the ShaderNode will receive
        '''
        self.shader_type=shader_type
        assert parent is not None
        self._shadertype_dict=dict({'Emission':'ShaderNodeEmission',
                         'Add':'ShaderNodeAddShader',
                         'Math':'ShaderNodeMath',
                         'Texture_coordinates':'ShaderNodeTexCoord',
                         'Separate_XYZ':'ShaderNodeSeparateXYZ',
                         'Combine_XYZ':'ShaderNodeCombineXYZ',
                         'Principled BSDF':'ShaderNodeBsdfPrincipled',
                         'Material Output':'ShaderNodeOutputMaterial',
                         'Image':'ShaderNodeTexImage',
                         'Glossy':'ShaderNodeBsdfGlossy',
                         'Noise':'ShaderNodeTexNoise',
                         'Color_Ramp':'ShaderNodeValToRGB'})
        if name==None:
            kwargs['shader_type']=self._format_type(shader_type)
            kwargs['parent_name']=parent
            self.parent_name=parent
            self.name=Communication.ask('create_shadernode', **kwargs)
        else:
            self.parent_name=parent
            self.name=name
        self._inputs=ShaderDict(self.name, self.parent_name,
                                'shadernode_input')
        self._outputs=ShaderDict(self.name, self.parent_name,
                                 'shadernode_output')
        self._properties=ShaderDict(self.name, self.parent_name,
                                    'shadernode_property')
    
    def to_dict(self, **kwargs):
        '''returns a dictionnary representing the ShaderNode
        and extra parameters with kwargs'''
        params=dict({'parent_name':self.parent_name,
                     'name':self.name})
        params.update(kwargs)
        return params
    
    def _format_type(self, key):
        assert key in self._shadertype_dict.keys()
        return self._shadertype_dict[key]
    
    def remove(self):
        '''remove the ShaderNode from the material'''
        Communication.send('remove_shader', **self.to_dict())
    
    @property
    def inputs(self):
        '''ShaderDict to access the input ShaderSockets. The setter will
        create a link to another ShaderSocket output'''
        return self._inputs
    
    @property
    def outputs(self):
        '''ShaderDict to access the output ShaderSockets. The setter will
        create a link to another ShaderSocket input'''
        return self._outputs
    
    @property
    def properties(self):
        '''a PropertyDict to get and set properties of this ShaderNode'''
        return self._properties


class Constraint:
    '''Class representing a constraint for an object'''
    
    def __init__(self, parent=None, constraint_type='FOLLOW_PATH', **kwargs):
        ''': creates a new constraint and link it to an Object
        
        Parameters:
            parent: an Object
            
            constraint_type: the type of Constraint. Can be ‘CAMERA_SOLVER’,
            ‘FOLLOW_TRACK’, ‘OBJECT_SOLVER’, ‘COPY_LOCATION’, ‘COPY_ROTATION’,
            ‘COPY_SCALE’, ‘COPY_TRANSFORMS’, ‘LIMIT_DISTANCE’,
            ‘LIMIT_LOCATION’, ‘LIMIT_ROTATION’, ‘LIMIT_SCALE’,
            ‘MAINTAIN_VOLUME’, ‘TRANSFORM’, ‘TRANSFORM_CACHE’, ‘CLAMP_TO’,
            ‘DAMPED_TRACK’, ‘IK’, ‘LOCKED_TRACK’, ‘SPLINE_IK’, ‘STRETCH_TO’,
            ‘TRACK_TO’, ‘ACTION’, ‘ARMATURE’, ‘CHILD_OF’, ‘FLOOR’,
            ‘FOLLOW_PATH’, ‘PIVOT’, ‘SHRINKWRAP’
        '''
        kwargs['constraint_type']=constraint_type
        kwargs['parent_name']=parent
        self.parent_name=parent
        self.name=Communication.ask('create_constraint', **kwargs)
        self._properties=PropertyDict(self.name, self.parent_name,
                                      func='constraint_property')
    
    def insert_keyframe(self, key, frame='current'):
        '''insert a keyframe for this constraint for the parameter 'key' at
        the frame 'frame' '''
        Communication.ask('insert_keyframe_constraint', key=key, frame=frame,
                          name_obj=self.parent_name, name=self.name)
    
    @property
    def properties(self):
        '''PropertyDict to get and set the properties of this constaint '''
        return self._properties
    
class PropertyDict(dict):
    '''Class representing an object properties. It rewrites the setter
    and getter of the dict class to use the properties as a dictionary 
    with the server'''
    
    def __init__(self, name=None, name_obj=None, func=None, **kwargs):
        super().__init__()
        self.name=name
        self.name_obj=name_obj
        self.func=func
        self.params=kwargs
        
    def __setitem__(self, key, value):
        kwargs=self.params.copy()
        kwargs.update(dict({'key':key,
                     'parent_name':self.name,
                     'parent_name_obj':self.name_obj}))
        if hasattr(value, 'to_dict'):
            value=value.to_dict()
        kwargs['value']=value
        Communication.ask('set_'+self.func,
                          **kwargs)
    
    def __getitem__(self, key):
        kwargs=self.params.copy()
        kwargs.update(dict({'key':key,
                     'parent_name':self.name,
                     'parent_name_obj':self.name_obj}))
        res=Communication.ask('get_'+self.func, **kwargs)
        if isinstance(res, dict):
            return Object(**res)
        else:
            return res

class Modifier:
    '''Class representing a modifier for an object'''
    
    def __init__(self, parent=None, modifier_type='CURVE', **kwargs):
        '''
        Parameters:
            parent: an Object
            
            modifier_type: the type of Modifier. Can be ‘DATA_TRANSFER’,
            ‘MESH_CACHE’, ‘MESH_SEQUENCE_CACHE’, ‘NORMAL_EDIT’,
            ‘WEIGHTED_NORMAL’, ‘UV_PROJECT’, ‘UV_WARP’, ‘VERTEX_WEIGHT_EDIT’,
            ‘VERTEX_WEIGHT_MIX’, ‘VERTEX_WEIGHT_PROXIMITY’, ‘ARRAY’, ‘BEVEL’,
            ‘BOOLEAN’, ‘BUILD’, ‘DECIMATE’, ‘EDGE_SPLIT’, ‘NODES’, ‘MASK’,
            ‘MIRROR’, ‘MESH_TO_VOLUME’, ‘MULTIRES’, ‘REMESH’, ‘SCREW’, ‘SKIN’,
            ‘SOLIDIFY’, ‘SUBSURF’, ‘TRIANGULATE’, ‘VOLUME_TO_MESH’, ‘WELD’,
            ‘WIREFRAME’, ‘ARMATURE’, ‘CAST’, ‘CURVE’, ‘DISPLACE’, ‘HOOK’, 
            ‘LAPLACIANDEFORM’, ‘LATTICE’, ‘MESH_DEFORM’, ‘SHRINKWRAP’,
            ‘SIMPLE_DEFORM’, ‘SMOOTH’, ‘CORRECTIVE_SMOOTH’, ‘LAPLACIANSMOOTH’,
            ‘SURFACE_DEFORM’, ‘WARP’, ‘WAVE’, ‘VOLUME_DISPLACE’, ‘CLOTH’, 
            ‘COLLISION’, ‘DYNAMIC_PAINT’, ‘EXPLODE’, ‘FLUID’, ‘OCEAN’,
            ‘PARTICLE_INSTANCE’, ‘PARTICLE_SYSTEM’, ‘SOFT_BODY’, ‘SURFACE’
        '''
        kwargs['modifier_type']=modifier_type
        kwargs['parent_name']=parent
        self.parent_name=parent
        self.modifier_type=modifier_type
        self.name=Communication.ask('create_modifier', **kwargs)
        self._properties=PropertyDict(self.name, self.parent_name,
                                      func='modifier_property')
    
    @property
    def properties(self):
        '''PropertyDict to get and set the properties of this Modifier '''
        return self._properties
    
    def apply(self):
        '''apply the modifier'''
        kwargs=dict({'name':self.name,
                     'name_obj':self.parent_name,
                     'modifier_type': self.modifier_type})
        time.sleep(0.1)
        Communication.ask('apply_modifier', **kwargs)
        
    
class Material:
    '''Class representing a Material.'''
    
    def __init__(self, name='material', color='#FFFFFF', alpha=1., transmission=0,
                 use_screen_refraction=False, refraction_depth=0.,
                 blend_method='OPAQUE', blend_method_shadow='OPAQUE',
                 use_backface_culling=False, create_new=True,
                 metallic=0.,
                 **kwargs):
        '''
        Parameters:
            name: the name of the material
            
            create_new: create a new material. If False, try to get an existing
            
            material with the same name, and if it fails, create a new one
            
            other arguments: properties of the Principled BSDF shader
        '''
    
        if not create_new:
            names = self.get_material_names()
            if name in names:
                self.material_object = self.get_material(name)
            else:
                self.material_object = self.create_material(name)
        else:
            self.material_object = self.create_material(name)
        self.color=Material.convert_color(color)
        params=dict({'name':self.material_object, 'color':self.color,
                     'alpha':alpha, 'transmission':transmission,
                     'use_screen_refraction':use_screen_refraction,
                     'refraction_depth':refraction_depth,
                     'blend_method':blend_method,
                     'use_backface_culling':use_backface_culling,
                     'blend_method_shadow':blend_method_shadow,
                     'metallic':metallic})
        params.update(kwargs)
        Communication.send('update_material', **params)
        self.operations=dict({'*':'MULTIPLY',
                         '/':'DIVIDE',
                         '+':'ADD',
                         '-':'SUBTRACT',
                         '^':'POWER',
                         '>':'GREATER_THAN',
                         '<':'LESS_THAN',
                         'ABS':'ABSOLUTE',
                         'sqrt':'SQRT',
                         'cos':'COSINE',
                         'sin':'SINE'})
        names=['Principled BSDF', 'Material Output']
        self._shadernodes_dimensions=dict()
        for name in names:
            self._shadernodes_dimensions[name]=ShaderNode(name=name,
                                       parent=self.material_object,
                                       shader_type=name).properties['location']
    
    @property
    def _xmax_shadernode_dimensions(self):
        return np.max(np.array(list(self._shadernodes_dimensions.values()))[:,0])
    
    @property
    def _ymax_shadernode_dimensions(self):
        return np.max(np.array(list(self._shadernodes_dimensions.values()))[:,1])
    
    @property
    def _xmin_shadernode_dimensions(self):
        return np.min(np.array(list(self._shadernodes_dimensions.values()))[:,0])
    
    @property
    def _ymin_shadernode_dimensions(self):
        return np.min(np.array(list(self._shadernodes_dimensions.values()))[:,1])
    
    @property
    def _height_shadernode_dimensions(self):
        return self._ymax_shadernode_dimensions-self._ymin_shadernode_dimensions
    
    @property
    def _width_shadernode_dimensions(self):
        return self._xmax_shadernode_dimensions-self._xmin_shadernode_dimensions
    
    def add_shader(self, shader_type):
        '''Add a ShaderNode to this Material.
        
        Parameters:
            shader_type: the type of this shader. See ShaderNode
        
        Returns:
            the created ShaderNode
        '''
        dx, dy=200, 200
        i,j=0,0
        while [i*dx, j*dy] in list(self._shadernodes_dimensions.values()):
            i+=1
            if i*dx>self._width_shadernode_dimensions:
                i=0
                j+=1
                if j*dy>self._height_shadernode_dimensions:
                    j=0
                    i=int(self._width_shadernode_dimensions)/dx+1
                    break
        res= ShaderNode(shader_type=shader_type,
                          parent=self.material_object)
        res.properties['location']=[i*dx, j*dy]
        self._shadernodes_dimensions[res.name]=[i*dx, j*dy]
        return res
    
    def get_shader(self, name=None, find_math_operation=None):
        '''Get an existing ShaderNode from his name.
        
        Parameters:
            name: the name of the shader
            
            find_math_operation: if not None, find the first 
            
            Math ShaderNode to have this operation
        '''
        if find_math_operation is not None:
            for node_name in self.shadernodes_dimensions.keys():
                if 'Math' in node_name:
                    node=self.get_shader(
                            name=node_name)
                    if (node._properties['operation']==
                        self.operations[find_math_operation]):
                        return node
        else:
            return ShaderNode(parent=self.material_object, name=name)
    
    def coordinate_expression(self, exp, special_keys=None):
        '''Construct a tree of Math ShaderNodes representing the math operation
        exp.
        
        Parameters:
            exp: String representing the math operation. Can use +,-,/,*,||,
            sqrt, ^, e, sin, cos
            
            special_keys: a dict linking the keys representing the input of
            this expression to ShaderSockets. for example:
                dict({'x':separation_shader.outputs['X']})
        
        Returns:
            the last ShaderNode, whose outputs['Value'] can be linked to
            another ShaderNode
        '''
        e=Expression(content=exp, tokens=[])
        if not e.is_leaf():
            tree=e.get_tree()
            tree['parent']=None
            return self._distribute_shaders(tree,
                                           special_keys=special_keys)
    
    def _distribute_shaders(self, tree, special_keys=None):
        return_shader=None
        if isinstance(tree, dict):
            operation=list(tree.keys())[0]
            tree['shader']=self.add_shader(shader_type='Math')
            tree['shader'].properties['operation']=self.operations[operation]
            if tree['parent'] is None:
                return_shader=tree['shader']
            subtree=tree[operation]
            for node in subtree:
                if isinstance(node, dict):
                    node['parent']=tree['shader']
                self._distribute_shaders(node, 
                                        special_keys=special_keys)
            for i, node in enumerate(subtree):
                if isinstance(node, dict):
                    tree['shader'].inputs[i]=node['shader'].outputs['Value']
                else:
                    try:
                        tree['shader'].inputs[i]=float(node)
                    except ValueError:
                        if node=='e':
                            tree['shader'].inputs[i]=np.e
                        if node in special_keys.keys():
                            tree['shader'].inputs[i]=special_keys[node]
                            
        else:
            pass
        return return_shader
        
        
            
        
    def z_dependant_color(self, colors=None, positions=None,
                          coordinate='Generated'):
        '''add a color ramp based on the Z texture coordinate
        
        Parameters:
           colors: a list of colors to use in the color ramp
           
           positions: a list of float positions to use in the color ramp 
           
           coordinate: which texture coordinate should be considered.
           
        Returns:
            None
        '''
        
        coord=self.add_shader('Texture_coordinates')
        sep=self.add_shader('Separate_XYZ')
        sep.inputs['Vector']=coord.outputs[coordinate]
        color_ramp=self.add_shader('Color_Ramp')
        color_ramp.inputs['Fac']=sep.outputs['Z']
        color_ramp.properties['color_ramp']=dict({'positions':positions,
                             'colors':[Material.convert_color(color) for color in colors]})
        principled=self.get_shader('Principled BSDF')
        principled.inputs['Base Color']=color_ramp.outputs['Color']
    
    def surface_noise(self, scale=3, detail=2, roughness=0.5,
                      dimension='2D',
                      orientation='Z', origin='Generated'):
        '''add a displacement noise
        
        Parameters:
           scale: the scale of the noise Texture
           
           detail: the detail of the noise Texture
           
           roughness: the roughness of the noise Texture
           
           dimensions: either '2D' or '3D'. If '3D', apply the noise to all
           faces, if '2D', apply the noise only to a given direction
           
           orientation: either 'X', 'Y', or 'Z'. The normal to use in case 
           dimensions is '2D'
           
           origin: which Texture coordinates to use for the noise
           
        Returns:
            None
        '''
        noise=self.add_shader('Noise')
        coord=self.add_shader('Texture_coordinates')
        output=self.get_shader('Material Output')
        
        if dimension=='2D':
            sepxyz=self.add_shader('Separate_XYZ')
            sepxyz2=self.add_shader('Separate_XYZ')
            combine=self.add_shader('Combine_XYZ')
            for direction in ['X', 'Y', 'Z']:
                if orientation!=direction:
                    combine.inputs[direction]=sepxyz2.outputs[direction]
            sepxyz.inputs['Vector']=coord.outputs['Normal']
            sup=self.add_shader('Math')
            sup.properties['operation']=self.operations['>']
            sup.inputs[0]=sepxyz.outputs[orientation]
            sup.inputs[1]=0.5
            mult=self.add_shader('Math')
            mult.properties['operation']=self.operations['*']
            mult.inputs[0]=sup.outputs['Value']
            sepxyz2.inputs['Vector']=coord.outputs[origin]
            noise.inputs['Vector']=combine.outputs['Vector']
            mult.inputs[1]=noise.outputs['Fac']
            output.inputs['Displacement']=mult.outputs['Value']
        elif dimension=='3D':
            output.inputs['Displacement']=noise.outputs['Fac']
        noise.inputs['Scale']=scale
        noise.inputs['Detail']=detail
        noise.inputs['Roughness']=roughness
    
    def glowing(self, color='#FFFFFF', strength=10, **kwargs):
        '''add a glowing emission to a Material
        
        Parameters:
           color: the color of the glowing
           
           strength: the strength of the glowing
           
        Returns:
            None
        '''
        
        emission=self.add_shader('Emission')
        emission.inputs['Color']=Material.convert_color(color)
        emission.inputs['Strength']=strength
        output=self.get_shader('Material Output')
        add_shader=self.add_shader('Add')
        add_shader.inputs[0]=output.inputs['Surface']
        output.inputs['Surface']=add_shader.outputs['Shader']
        add_shader.inputs[1]=emission.outputs['Emission']

        
    def get_material(self, name):
        return Communication.ask('get_material', name=name)
    
    def create_material(self, name):
        return Communication.ask('create_material', name=name)
    
    def get_material_names(self):
        return Communication.ask('get_material_names')
    
    @staticmethod
    def convert_color(color, alpha=1):
        if len(color)==3:
            if alpha is None:
                alpha=1.0
            return color+[alpha]
        elif len(color)==4:
            return color
        elif color[0]=='#':
            if len(color)==7:
                if alpha is None:
                    alpha=1.0
            else:
                alpha=int(color[7:9], 16)/256.
            return [int(color[i:i+2], 16)/256. for i in [1,3,5]] +[alpha]
 
class MetallicMaterial(Material):
    '''Class representing a Mettalic Material made of a glossy BDSF shader
    with a surface noise'''

    def __init__(self, name='metal', color='#DCC811', randomness=1, detail=10,
                 roughness=0.5, orientation='Z', origin='Generated',
                 **kwargs):
        '''Parameters:
            name: the desired name of the material
            
            color: the desired color of the material
            
            randomness: the scale of the Texture noise
            
            detail: the detail of the Texture noise
            
            roughness: the roughness of the Texture noise
            
            orientation: see surface_noise for the Material class
            
            origin:  see surface_noise for the Material class
        '''
        
        super().__init__(name, color, **kwargs) 
        output=self.get_shader('Material Output')
        glossy=self.add_shader('Glossy')
        coord=self.add_shader('Texture_coordinates')
        output.inputs['Surface']=glossy.outputs['BSDF']
        glossy.inputs['Color']=Material.convert_color(color)
        noise=self.add_shader('Noise')
        coord=self.add_shader('Texture_coordinates')
        noise.inputs['Vector']=coord.outputs[origin]
        
        noise.inputs['Scale']=randomness
        noise.inputs['Detail']=detail
        noise.inputs['Roughness']=roughness
        sepxyz=self.add_shader('Separate_XYZ')
        sepxyz.inputs['Vector']=coord.outputs['Normal']
        sup=self.add_shader('Math')
        sup.properties['operation']=self.operations['>']
        sup.inputs[0]=sepxyz.outputs[orientation]
        sup.inputs[1]=0.5
        mult=self.add_shader('Math')
        mult.properties['operation']=self.operations['*']
        mult.inputs[0]=sup.outputs['Value']
        mult.inputs[1]=noise.outputs['Fac']
        output.inputs['Displacement']=mult.outputs['Value']

class EmissionMaterial(Material):
    '''class representing an Emission volume material'''
    
    def __init__(self, color='#AF2020', expression=None, strength=None, **kwargs):
         '''initialize.
         
         Parameters:
             color: the color of the emission
             
             expression: if not None, an expression to specify the strength of
             the emission. See coordinate_expression for Material
             
             strength: if no expression is provided, this fixed float will be
             set to the strength of the emission
         '''
         
         super().__init__(**kwargs)
         emission=self.add_shader('Emission')
         emission.inputs['Color']=Material.convert_color(color)
         output=self.get_shader('Material Output')
         output.inputs['Volume']=emission.outputs['Emission']
         Principled=self.get_shader('Principled BSDF')
         Principled.remove()
         
         if expression is not None:
             coords=self.add_shader('Texture_coordinates')
             sepxyz=self.add_shader('Separate_XYZ')
             sepxyz.inputs['Vector']=coords.outputs['Generated']
             shader=self.coordinate_expression(expression, 
                                               special_keys=dict({'x':sepxyz.outputs['X'],
                                                             'y':sepxyz.outputs['Y'],
                                                             'z':sepxyz.outputs['Z']}))
             emission.inputs['Strength']=shader.outputs['Value'] 
         elif strength is not None:
             emission.inputs['Strength']=strength

class PositionDependantMaterial(Material):
    '''class representing an surface color depending on the position through
    an expression'''
    
    def __init__(self, expression, 
                 colors=None,
                 positions=None,
                 coordinate='Generated',
                 **kwargs):
        '''Initialize
        
        Parameters:
            expression: the expression to enter the color ramp. 
            See coordinate_expression for Material
            
            colors: a list of colors to put in the color ramp
            
            positions: a list of float positions to put in the color ramp
            
            coordinate: which Texture coordinate to use for the input
            of the expression
        '''
        
        super().__init__(**kwargs)
        coord=self.add_shader('Texture_coordinates')
        sepxyz=self.add_shader('Separate_XYZ')
        sepxyz.inputs['Vector']=coord.outputs[coordinate]
        color_ramp=self.add_shader('Color_Ramp')
        if len(expression)==1:
            color_ramp.inputs['Fac']=sepxyz.outputs[expression]
        else:
            shader=self.coordinate_expression(expression, 
                                           special_keys=dict({'x':sepxyz.outputs['X'],
                                                         'y':sepxyz.outputs['Y'],
                                                         'z':sepxyz.outputs['Z']}))
            color_ramp.inputs['Fac']=shader.outputs['Value']
        color_ramp.properties['color_ramp']=dict({'positions':positions,
                             'colors':[Material.convert_color(color) for color in colors]})
        principled=self.get_shader('Principled BSDF')
        principled.inputs['Base Color']=color_ramp.outputs['Color']
        
class ZColorRampMaterial(PositionDependantMaterial):
    '''PositionDependantMaterial with the expresion 'Z'
    '''
        
    def __init__(self, colors=None, positions=None,
                          coordinate='Generated', **kwargs):
        super().__init__('Z', colors=colors,
                         positions=positions,
                         coordinate=coordinate,
                         **kwargs)

            
class GaussianLaserMaterial(EmissionMaterial):
    '''EmissionMaterial with a Geussian profile.
    The Generated coordinate is used'''
    
    def __init__(self, alpha=0.001, waist=0.1, strength=3, **kwargs):
        '''Initialize
        
        Parameters:
            alpha: the divergence length of the gaussian beam
            
            waist: the waist of the beam
            
            strength: the strength of the emission
        '''
        expression='{:}*e^(-((x-0.5)^2+(y-0.5)^2)/{:}/(1+(z-0.5)^2/{:}))'\
                        .format(strength, alpha, waist**2)
        super().__init__(expression=expression, **kwargs) 
    
class Object:
    '''Class representing an Object'''
    
    def __init__(self, name_obj=None, filepath=None,
                 location=None, scale=None,
                 material=None, rotation=None,
                 **kwargs):
        '''
        Parameters:
            name_obj: the name of the object
            
            filepath: if given, a json file location containing properties to 
            set to the object
            
            location: if given, the location of the desired object
            
            scale: if given, the scale of the desired object
            
            material: if given, the material of the desired object
            
            rotation: if given, the rotation of the desired object
        '''    
        
        if name_obj is not None:
            self.name_obj=name_obj
        self._properties=PropertyDict('', self.name_obj, func='object_property')
        self.constraints=[]
        self.modifiers=[]
        if filepath is not None:
            self.load(filepath)
        if location is not None:
            self.location=location
        if scale is not None:
            self.scale=scale
        if rotation is not None:
            self.rotation=rotation
        if material is not None:
            self.assign_material(material)
    
    def assign_material(self, material):
        '''Assign a material to the object
        
        Parameters:
            material: a Material instance
        '''
        
        if isinstance(material, list):
            kwargs = dict({'name_obj':self.name_obj,
                           'name_mat':[mat.material_object for mat in material]})
        else:
            kwargs = dict({'name_obj':self.name_obj,
                           'name_mat':material.material_object})
        Communication.send('assign_material', **kwargs)
    
    def load(self, filepath):
        '''Load a Json file with properties to set
        
        Parameters;
            filepath: path the Json file
        '''
        
        with open(filepath, 'r') as f:
            data=json.load(f)
        for k, v in data.items():
            self.properties[k]=v
    
    def duplicate(self):
        '''Duplicate the object
        
        Returns:
            the new object
        '''
        
        return Object(name_obj=Communication.ask('duplicate',
                                                 name_obj=self.name_obj))
    
    def follow_path(self, target=None, use_curve_follow=True,
                    forward_axis='FORWARD_X'):
        '''Add a Follow path constraint to the object
        
        Parameters:
            target: the object to follow
            
            use_curve_follow and forward_axis: property of the constraint
        '''
        
        constraint=self.assign_constraint(constraint_type='FOLLOW_PATH')
        constraint.properties['target']=target
        constraint.properties['use_curve_follow']=use_curve_follow
        constraint.properties['forward_axis']=forward_axis
        self.constraints.append(constraint)
        return constraint
    
    def insert_keyframe(self, key, frame='current'):
        '''Keyframe a property of the object
        
        Parameters:
            key: the property to keyframe
            frame: the frame at which the keyframe should be set
        '''
        
        Communication.ask('insert_keyframe_object',
                          key=key, frame=frame,
                          name_obj=self.name_obj)
        
    def assign_constraint(self, constraint_type='FOLLOW_PATH', **kwargs):
        '''Assign a constraint to the object
        
        Parameters:
            constraint_type: type of the constraint. see Constraint
        '''
        
        return Constraint(parent=self.name_obj,
                                   constraint_type=constraint_type,
                                   **kwargs)
    
    def curve_modifier(self, target=None, deform_axis='POS_X'):
        '''Assign a Curve modifier to the object
        
        Parameters:
            target: the Curve object
            
            deform_axis: property of the constraint
        '''
        
        modifier=self.assign_modifier(modifier_type='CURVE')
        modifier.properties['object']=target
        modifier.properties['deform_axis']=deform_axis
        self.modifiers.append(modifier)
    
    def assign_modifier(self, modifier_type='CURVE', **kwargs):
        '''Assign a modifier to the object
        
        Parameters:
            modifier_type: the type of modifier. See Modifier
        
        Returns:
            the created Modifier
        '''
        return Modifier(parent=self.name_obj,
                                   modifier_type=modifier_type,
                                   **kwargs)
    
    def surface_subdivisions(self, levels=1):
        '''subdivide the Mesh to increase its smoothness
        
        Parameters:
            levels: number of iterations for the subdivision
        '''
        
        modifier=self.assign_modifier('SUBSURF')
        modifier.properties['levels']=levels
        time.sleep(0.5)
        modifier.apply()
        time.sleep(0.5)
    
    def subtract(self, target, apply=True):
        '''Assign and apply a Boolean Modifier for subtraction between
        self and another Object.
        
        Parameters:
            target: Object to subtract
        
        Returns:
            None
        '''
        boolean=self.assign_modifier(modifier_type='BOOLEAN')
        boolean.properties['object']=target
        if apply:
            boolean.apply()
    
    def copy_location(self, target=None):
        '''Apply a COPY_LOCATION constraint to the object
        
        Parameters:
            target: the Object whose location should be copied from
        
        Returns:
            None
        '''
        
        self.assign_constraint(constraint_type='COPY_LOCATION')
        self.constraint.properties['target']=target
    
    def to_dict(self, **kwargs):
        '''Returns a dictionary representing the object
        
        Parameters:
            kwargs: some keyword arguments to add to the base dictionary,
            which is only the name of the object
        
        Returns:
            the generated dictionary
        '''
        
        kwargs.update(dict({'name_obj':self.name_obj}))
        return kwargs
    
    def remove(self):
        '''Delete the Object
        '''
        Communication.send('remove_object', **self.to_dict())
        
    @property
    def properties(self):
        '''PropertyDict to get and set the Object properties
        '''
        
        return self._properties
    
    @property
    def scale(self):
        '''Scale of the Object. Expect and returns a list of 3 scalings,
        for x,y and z respectively
        '''
        return self.properties['scale']
    
    @scale.setter
    def scale(self, val):
        self.properties['scale']=val
    
    @property
    def hide(self):
        '''Scale of the Object. Expect and returns a list of 3 scalings,
        for x,y and z respectively
        '''
        return self.properties['hide_viewport']
    
    @hide.setter
    def hide(self, val):
        self.properties['hide_viewport']=val
    
    @property
    def location(self):
        '''Location of the Object. Expect and returns a list of 3 coordinates
        '''
        return self.properties['location']
    
    @location.setter
    def location(self, val):
        self.properties['location']=val
    
    @property
    def rotation(self):
        '''Rotation of the Object. Expect and returns a list of 3 rotations
        in radians around the x,y and z axis, following the Euler angles
        convention
        '''
        return self.properties['rotation_euler']
    
    @rotation.setter
    def rotation(self, val):
        self.properties['rotation_euler']=val
    
    @property
    def x(self):
        '''x coordinate of the location
        '''
        return self.location[0]
    
    @property
    def y(self):
        '''y coordinate of the location
        '''
        return self.location[1]
    
    @property
    def z(self):
        '''z coordinate of the location
        '''
        return self.location[2]
    
    @x.setter
    def x(self, val):
        self.location=dict({'x':val})
    
    @y.setter
    def y(self, val):
        self.location=dict({'y':val})
    
    @z.setter
    def z(self, val):
        self.location=dict({'z':val})
    
    @property
    def matrix_world(self):
        return np.array(self.properties['matrix_world'])

class Camera(Object):
    '''Class Representing a camera
    '''
    
    
    def __init__(self, name='camera',
                 **kwargs):
        '''
        Parameters:
            name: the name of the camera
            kwargs: Object properties
        '''
        
        self._add_camera(name)
        super().__init__(**kwargs)
        self._cam_properties=PropertyDict(self.name, '',
                                          func='camera_property')
    
    def _add_camera(self, name):
        self.name, self.name_obj=Communication.ask('create_camera',
                                                   name=name)
    
    @property
    def cam_properties(self):
        '''
        PropertyDict to get and set Camera properties
        '''
        return self._cam_properties

class Curve(Object):
    '''Class representing a Curve
    '''
    
    def __init__(self, points, **kwargs):
        '''Parameters:
            points: a list of 3D coordinates for the points of the curve
            kwargs: Object properties
        '''
        
        self.name, self.name_obj=Communication.ask('create_curve',
                                                   points=points,
                                                   **kwargs) 
        super().__init__(**kwargs)
    
    @property
    def points(self):
        '''a numpy array of the points of the curve
        '''
        return np.array(Communication.ask('get_curve_points',
                                          name=self.name,
                                          name_obj=self.name_obj))
    
    @points.setter
    def points(self, val):
        if hasattr(val, 'tolist'):
            val=val.tolist()
        Communication.send('set_curve_points',
                           name=self.name,
                           points=val)
        
class Light(Object):
    '''Class representing a light'''
    
    def __init__(self, name='light', color='#FFFFFF',
                 power=2, radius=0.25, light_type='POINT',
                 filepath=None, **kwargs):
        '''Parameters:
            name: the name of the Light object
            color: color of the light. Default to white. Expect a string
            starting with a '#' and then the hexadecimal values of red, green
            and blue.
            power: the power of the light in Watts
            radius: the radius of the light
            light_type: which type of light. Can be 'POINT', 'SUN', 'SPOT' or
            'AREA'
            filepath: the path to a JSON file with some properties to load in
            this light
        '''
        self._add_light(name, light_type=light_type)
        super().__init__(**kwargs)
        self._light_properties=PropertyDict(self.name,
                                           self.name_obj,
                                           func='light_property')
        self.power=power
        self.radius=radius
        self.color=color
        if filepath is not None:
            self.load(filepath)
            self._load_light(filepath)
        
    def _add_light(self, name, light_type='POINT'):
        res=dict()
        kwargs = dict()
        kwargs['light_type']=light_type
        res['args']=[]
        res['command']='create_light'
        res['kwargs']=kwargs
        self.name, self.name_obj=Communication.ask('create_light',
                                                   light_type=light_type)
    
    def _load_light(self, filepath):
        with open(filepath, 'r') as f:
            data=json.load(f)
        for k, v in data.items():
            self.light_properties[k]=v
    
    @property
    def power(self):
        '''Power of the light in Watts'''
        return self.light_properties['energy']
    
    @power.setter
    def power(self, val):
        self.light_properties['energy']=float(val)
    
    @property
    def color(self):
        '''Color of the light. Returns a list of float, but expect a String'''
        return self.light_properties['color']
    
    @color.setter
    def color(self, val):
        self.light_properties['color']=Material.convert_color(val)[:3]
    
    @property
    def radius(self):
        '''Radius of the light in meters'''
        return self.light_properties['shadow_soft_size']
    
    @radius.setter
    def radius(self, val):
        self.light_properties['shadow_soft_size']=float(val)
    
    @property
    def light_properties(self):
        '''PropertyDict for getting and setting the light properties.
        Typical properties are 'energy' for power, 'shadow_soft_size' for
        radius, and 'color'
        '''
        return self._light_properties
        

class Mesh(Object, GeometricEntity):
    '''Class representing a Mesh'''
    
    def __init__(self, cells=None, points=None,
                 thickness=None, name='mesh', subdivide=1,
                 **kwargs):
        '''Parameters:
            cells: a list of cells consisting in a list of integer point
            indices
            points: a list of points consisting in a list 
            of the x, y and z coordinates
            thickness: the thickness of the desired extruded 2D shape. Can be
            None, which means no extrusion
            name: the desired name for the Mesh
            subdivide: the number of division in the extrusion
            kwargs: Object properties
        '''
        
        self.subdivide=subdivide
        self.thickness=thickness
        self.cells=cells
        self.points=points
        self.name_obj, self.name_msh = self._send_mesh(thickness=self.thickness,
                                                      name=name)
        super().__init__(**kwargs)
        
    def _send_mesh(self, thickness=None, name='mesh'):
        cells=[]
        points=[[coord for coord in p] for p in self.points]
        for celltype in self.cells:
            if not isinstance(celltype[0], str):
                cells+=[[int(ind) for ind in celltype]]
            elif celltype[0]=='triangle':
                cells+=[[int(ind) for ind in cell] for cell in celltype[1]]
        return Communication.ask('create_mesh',
                                 name=name,
                                 thickness=thickness,
                                 subdivide=self.subdivide,
                                 points=points,
                                 cells=cells) 
    
    def insert_mesh_keyframe(self, frame='current',
                             waiting_time_between_points=0.01):
        '''
        Insert a keyframe on the position of each vertices of the mesh
        
        Parameters:
            frame: the frame where the keyframes should be placed. Default to
            'current', which means the current frame. Otherwise should be an
            integer
            waiting_time_between_points: number of seconds to wait between the
            keyframing of each point. Should be adjusted to maximise speed
            while not crashing Blender when keyframing a large number of
            points.
        '''
        Communication.ask('insert_keyframe_mesh',
                           name_msh=self.name_msh,
                           frame=frame,
                           waiting_time_between_points=waiting_time_between_points)
        
    def cut_mesh(self, plane_points, plane_normals):
        '''
        Cut the mesh along a list of planes to subdivide it. 
        
        Parameters:
            plane_points: a list of points that belong the plane cuts. Each 
            point is a 3D list of coordinates
            plane_normals: a list of 3D vectors that are normal to the plane
            cuts. Each vector is a 3D list of coordinates
        '''
        
        Communication.send('cut_mesh', name_msh=self.name_msh,
                           planes_co=plane_points,
                           planes_no=plane_normals)
    
    def global_cut_mesh(self, N_cuts=100):
        '''
        Cut all the edges in N_cuts parts regularly spaced. Much more
        efficient than cut_mesh
        
        Parameters:
            N_cuts: the number of cuts to perform
        '''
        Communication.send('subdivide_edges',
                           name_msh=self.name_msh,
                           N_cuts=N_cuts)
    
    def smooth(self):
        '''
        Use the smooth option
        '''
        
        Communication.ask('smooth', name_msh=self.name_msh)
    
    def divide(self, Nx=None, Ny=None, Nz=None):
        '''Use the cut_mesh method for planes regularly spaced
        in X, Y and Z, and oriented along thos axis
        
        Parameters:
            Nx: an integer that represents the number of cuts along the X axis.
            Default to None which means no cut
            Ny: an integer that represents the number of cuts along the Y axis.
            Default to None which means no cut
            Nz: an integer that represents the number of cuts along the Z axis.
            Default to None which means no cut
        '''
        if Nx is not None:
            xs=np.linspace(self.xmin, self.xmax, Nx)
            self.cut_mesh([[x,0,0] for x in xs],
                          [[1,0,0] for x in xs])
        if Ny is not None:
            ys=np.linspace(self.ymin, self.ymax, Ny)
            self.cut_mesh([[0,y,0] for y in ys],
                          [[0,1,0] for y in ys])
        if Nz is not None:
            zs=np.linspace(self.zmin, self.zmax, Nz)
            self.cut_mesh([[0,0,z] for z in zs],
                          [[0,0,1] for z in zs])
    
    @property
    def use_auto_smooth(self):
        '''Use the auto_smooth property. Expects a boolean'''
        return self._properties[['data', 'use_auto_smooth']]
    
    @use_auto_smooth.setter
    def use_auto_smooth(self, val):
        self._properties[['data', 'use_auto_smooth']]=val
    
    @property
    def auto_smooth_angle(self):
        '''Define the auto_smooth angle. Expects a float'''
        return self._properties[['data', 'auto_smooth_angle']]
    
    @auto_smooth_angle.setter
    def auto_smooth_angle(self, val):
        self._properties[['data', 'auto_smooth_angle']]=val

    @property
    def parent(self):
        '''Get the Object associated with this Mesh'''
        return Object(self.name_obj)

    @property
    def vertices(self):
        '''Get the (local) vertices of this mesh as a numpy array'''
        return np.array(Communication.ask('get_vertices',
                                          name_msh=self.name_msh))
    
    @vertices.setter
    def vertices(self, val):
        if hasattr(val, 'tolist'):
            val=val.tolist()
        Communication.send('set_vertices',
                           name_msh=self.name_msh,
                           val=val)
        

if __name__=='__main__':
    pass
    
                          
                      
                      
            