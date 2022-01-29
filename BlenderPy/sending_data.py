# -*- coding: utf-8 -*-
"""
Created on Wed Aug 26 09:56:27 2020

@author: Thibault
"""

import socket
import json
import os
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
        Communication.ask('insert_keyframe_shadersocket',
                   **self.to_dict(key_to_keyframe=key, 
                                  frame=frame))
    
    @property
    def properties(self):
        return self._properties

class Image:
    
    def __init__(self, path):
        self.path=path
    
    def to_dict(self, **kwargs):
        kwargs.update(dict({'path':self.path}))
        return kwargs
        
class ShaderNode:
    
    def __init__(self, parent=None, shader_type='Emission',
                 name=None, **kwargs):
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
        self._inputs=ShaderDict(self.name, self.parent_name, 'shadernode_input')
        self._outputs=ShaderDict(self.name, self.parent_name, 'shadernode_output')
        self._properties=ShaderDict(self.name, self.parent_name, 'shadernode_property')
    
    def to_dict(self, **kwargs):
        params=dict({'parent_name':self.parent_name,
                     'name':self.name})
        params.update(kwargs)
        return params
    
    def _format_type(self, key):
        assert key in self._shadertype_dict.keys()
        return self._shadertype_dict[key]
    
    def remove(self):
        Communication.send('remove_shader', **self.to_dict())
    
    @property
    def inputs(self):
        return self._inputs
    
    @property
    def outputs(self):
        return self._outputs
    
    @property
    def properties(self):
        return self._properties


class Constraint:
    
    def __init__(self, parent=None, constraint_type='FOLLOW_PATH', **kwargs):
        kwargs['constraint_type']=constraint_type
        kwargs['parent_name']=parent
        self.parent_name=parent
        self.name=Communication.ask('create_constraint', **kwargs)
        self._properties=PropertyDict(self.name, self.parent_name,
                                      func='constraint_property')
    
    def insert_keyframe(self, key, frame='current'):
        Communication.ask('insert_keyframe_constraint', key=key, frame=frame,
                          name_obj=self.parent_name, name=self.name)
    
    @property
    def properties(self):
        return self._properties
    
class PropertyDict(dict):
    
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
    
    def __init__(self, parent=None, modifier_type='CURVE', **kwargs):
        kwargs['modifier_type']=modifier_type
        kwargs['parent_name']=parent
        self.parent_name=parent
        self.name=Communication.ask('create_modifier', **kwargs)
        self._properties=PropertyDict(self.name, self.parent_name,
                                      func='modifier_property')
    
    @property
    def properties(self):
        return self._properties
    
    def apply(self):
        if self.properties['type']=='BOOLEAN':
            kwargs=dict({'name':self.name,
                         'name_obj':self.parent_name})
            time.sleep(0.1)
            Communication.ask('apply_modifier', **kwargs)
        
    
class Material:
    
    def __init__(self, name='material', color='#FFFFFF', alpha=1., transmission=0,
                 use_screen_refraction=False, refraction_depth=0.,
                 blend_method='OPAQUE', blend_method_shadow='OPAQUE',
                 use_backface_culling=False, create_new=True,
                 metallic=0.,
                 **kwargs):
        if not create_new:
            names = self.get_material_names()
            if name in names:
                self.material_object = self.get_material(name)
            else:
                self.material_object = self.create_material(name)
        else:
            self.material_object = self.create_material(name)
        self.color=self.convert_color(color)
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
        self.shadernodes_dimensions=dict()
        for name in names:
            self.shadernodes_dimensions[name]=ShaderNode(name=name, parent=self.material_object,
                                                shader_type=name).properties['location']
    
    @property
    def xmax_shadernode_dimensions(self):
        return np.max(np.array(list(self.shadernodes_dimensions.values()))[:,0])
    
    @property
    def ymax_shadernode_dimensions(self):
        return np.max(np.array(list(self.shadernodes_dimensions.values()))[:,1])
    
    @property
    def xmin_shadernode_dimensions(self):
        return np.min(np.array(list(self.shadernodes_dimensions.values()))[:,0])
    
    @property
    def ymin_shadernode_dimensions(self):
        return np.min(np.array(list(self.shadernodes_dimensions.values()))[:,1])
    
    @property
    def height_shadernode_dimensions(self):
        return self.ymax_shadernode_dimensions-self.ymin_shadernode_dimensions
    
    @property
    def width_shadernode_dimensions(self):
        return self.xmax_shadernode_dimensions-self.xmin_shadernode_dimensions
    
    def add_shader(self, shader_type):
        dx, dy=200, 200
        i,j=0,0
        while [i*dx, j*dy] in list(self.shadernodes_dimensions.values()):
            i+=1
            if i*dx>self.width_shadernode_dimensions:
                i=0
                j+=1
                if j*dy>self.height_shadernode_dimensions:
                    j=0
                    i=int(self.width_shadernode_dimensions)/dx+1
                    break
        res= ShaderNode(shader_type=shader_type,
                          parent=self.material_object)
        res.properties['location']=[i*dx, j*dy]
        self.shadernodes_dimensions[res.name]=[i*dx, j*dy]
        return res
    
    def get_shader(self, name=None, find_math_operation=None):
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
    
    def coordinate_expression(self, exp, input_shader=None, special_keys=None):
        e=Expression(content=exp, tokens=[])
        if not e.is_leaf():
            tree=e.get_tree()
            tree['parent']=None
            return self.distribute_shaders(tree,input_shader=input_shader,
                                           special_keys=special_keys)
    
    def distribute_shaders(self, tree, input_shader=None, special_keys=None):
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
                self.distribute_shaders(node, input_shader=input_shader,
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
        coord=self.add_shader('Texture_coordinates')
        sep=self.add_shader('Separate_XYZ')
        sep.inputs['Vector']=coord.outputs[coordinate]
        color_ramp=self.add_shader('Color_Ramp')
        color_ramp.inputs['Fac']=sep.outputs['Z']
        color_ramp.properties['color_ramp']=dict({'positions':positions,
                             'colors':[self.convert_color(color) for color in colors]})
        principled=self.get_shader('Principled BSDF')
        principled.inputs['Base Color']=color_ramp.outputs['Color']
    
    def surface_noise(self, scale=3, detail=2, roughness=0.5,
                      dimension='2D',
                      orientation='Z', origin='Generated'):
        noise=self.add_shader('Noise')
        coord=self.add_shader('Texture_coordinates')
        output=self.get_shader('Material Output')
        
        if dimension=='2D':
            sepxyz=self.add_shader('Separate_XYZ')
            sepxyz2=self.add_shader('Separate_XYZ')
            combine=self.add_shader('Combine_XYZ')
            combine.inputs['X']=sepxyz2.outputs['X']
            combine.inputs['Y']=sepxyz2.outputs['Y']
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
        emission=self.add_shader('Emission')
        emission.inputs['Color']=self.convert_color(color)
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
    
    def convert_color(self, color, alpha=1):
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

    def __init__(self, name='metal', color='#DCC811', randomness=1, detail=10,
                 roughness=0.5, orientation='Z', origin='Generated',
                 **kwargs):
        super().__init__(name, color, **kwargs) 
        output=self.get_shader('Material Output')
        glossy=self.add_shader('Glossy')
        coord=self.add_shader('Texture_coordinates')
        output.inputs['Surface']=glossy.outputs['BSDF']
        glossy.inputs['Color']=self.convert_color(color)
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
    
    def __init__(self, color='#AF2020', expression=None, strength=None, **kwargs):
         super().__init__(**kwargs)
         emission=self.add_shader('Emission')
         emission.inputs['Color']=self.convert_color(color)
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
    
    def __init__(self, expression, 
                 colors=None,
                 positions=None,
                 coordinate='Generated',
                 **kwargs):
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
                             'colors':[self.convert_color(color) for color in colors]})
        principled=self.get_shader('Principled BSDF')
        principled.inputs['Base Color']=color_ramp.outputs['Color']
        
class ZColorRampMaterial(PositionDependantMaterial):
    
    def __init__(self, colors=None, positions=None,
                          coordinate='Generated', **kwargs):
        super().__init__('Z', colors=colors,
                         positions=positions,
                         coordinate=coordinate,
                         **kwargs)

            
class GaussianLaserMaterial(EmissionMaterial):
    
    def __init__(self, alpha=0.001, waist=0.1, strength=3, **kwargs):
        expression='{:}*e^(-((x-0.5)^2+(y-0.5)^2)/{:}/(1+(z-0.5)^2/{:}))'.format(strength, alpha, waist**2)
        super().__init__(expression=expression, **kwargs) 
    
class Object:
    
    def __init__(self, name_obj=None, filepath=None,
                 location=None, scale=None,
                 material=None, rotation=None,
                 **kwargs):
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
        if isinstance(material, list):
            kwargs = dict({'name_obj':self.name_obj,
                           'name_mat':[mat.material_object for mat in material]})
        else:
            kwargs = dict({'name_obj':self.name_obj,
                           'name_mat':material.material_object})
        Communication.send('assign_material', **kwargs)
    
    def load(self, filepath):
        with open(filepath, 'r') as f:
            data=json.load(f)
        for k, v in data.items():
            self.properties[k]=v
    
    def duplicate(self):
        return Object(name_obj=Communication.ask('duplicate',
                                                 name_obj=self.name_obj))
    
    def follow_path(self, target=None, use_curve_follow=True,
                    forward_axis='FORWARD_X'):
        constraint=self.assign_constraint(constraint_type='FOLLOW_PATH')
        constraint.properties['target']=target
        constraint.properties['use_curve_follow']=use_curve_follow
        constraint.properties['forward_axis']=forward_axis
        self.constraints.append(constraint)
        return constraint
    
    def insert_keyframe(self, key, frame='current'):
        Communication.ask('insert_keyframe_object',
                          key=key, frame=frame,
                          name_obj=self.name_obj)
        
    def assign_constraint(self, constraint_type='FOLLOW_PATH', **kwargs):
        return Constraint(parent=self.name_obj,
                                   constraint_type=constraint_type,
                                   **kwargs)
    
    def curve_modifier(self, target=None, deform_axis='POS_X'):
        modifier=self.assign_modifier(modifier_type='CURVE')
        modifier.properties['object']=target
        modifier.properties['deform_axis']=deform_axis
        self.modifiers.append(modifier)
    
    def assign_modifier(self, modifier_type='CURVE', **kwargs):
        return Modifier(parent=self.name_obj,
                                   modifier_type=modifier_type,
                                   **kwargs)
    
    def subtract(self, target):
        boolean=self.assign_modifier(modifier_type='BOOLEAN')
        boolean.properties['object']=target
        boolean.apply()
    
    def copy_location(self, target=None):
        self.assign_constraint(constraint_type='COPY_LOCATION')
        self.constraint.properties['target']=target
    
    def to_dict(self, **kwargs):
        kwargs.update(dict({'name_obj':self.name_obj}))
        return kwargs
    
    def remove(self):
        Communication.send('remove_object', **self.to_dict())
        
    @property
    def properties(self):
        return self._properties
    
    @property
    def scale(self):
        return self.properties['scale']
    
    @scale.setter
    def scale(self, val):
        self.properties['scale']=val
    
    @property
    def location(self):
        return self.properties['location']
    
    @location.setter
    def location(self, val):
        self.properties['location']=val
    
    @property
    def rotation(self):
        return self.properties['rotation_euler']
    
    @rotation.setter
    def rotation(self, val):
        self.properties['rotation_euler']=val
    
    @property
    def x(self):
        return self.location[0]
    
    @property
    def y(self):
        return self.location[1]
    
    @property
    def z(self):
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
    
    def __init__(self, name='camera',
                 **kwargs):
        self.add_camera(name)
        super().__init__(**kwargs)
        self._cam_properties=PropertyDict(self.name, '',
                                          func='camera_property')
    
    def add_camera(self, name):
        self.name, self.name_obj=Communication.ask('create_camera',
                                                   name=name)
    
    @property
    def cam_properties(self):
        return self._cam_properties

class Curve(Object):
    
    def __init__(self, points, **kwargs):
        self.name, self.name_obj=Communication.ask('create_curve',
                                                   points=points,
                                                   **kwargs) 
        super().__init__(**kwargs)
    
    @property
    def points(self):
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
    
    def __init__(self, name='light',
                 power=2, radius=0.25, light_type='POINT',
                 filepath=None, **kwargs):
        self.add_light(name, light_type=light_type)
        super().__init__(**kwargs)
        self._light_properties=PropertyDict(self.name,
                                           self.name_obj,
                                           func='light_property')
        self.light_properties['energy']=power
        self.light_properties['shadow_soft_size']=radius
        if filepath is not None:
            self.load(filepath)
            self.load_light(filepath)
        
    def add_light(self, name, light_type='POINT'):
        res=dict()
        kwargs = dict()
        kwargs['light_type']=light_type
        res['args']=[]
        res['command']='create_light'
        res['kwargs']=kwargs
        self.name, self.name_obj=Communication.ask('create_light',
                                                   light_type=light_type)
    
    def load_light(self, filepath):
        with open(filepath, 'r') as f:
            data=json.load(f)
        for k, v in data.items():
            self.light_properties[k]=v
    
    @property
    def light_properties(self):
        return self._light_properties
        

class Mesh(Object, GeometricEntity):
    
    def __init__(self, mesh=None, cells=None, points=None,
                 thickness=None, name='mesh', subdivide=1,
                 material=None, **kwargs):
        self.subdivide=subdivide
        self.thickness=thickness
        self.cells=cells
        self.points=points
        self.mesh=mesh
        self.name_obj, self.name_msh = self.send_mesh(self.mesh, 
                                                      thickness=self.thickness,
                                                      name=name)
        super().__init__(**kwargs)
        if material is not None:
            self.assign_material(material)
        
    def send_mesh(self, mesh, thickness=None, name='mesh'):
        if self.mesh is not None:
            points=[[float(coord) for coord in p] for p in self.points]
            cells=[]
            for celltype in self.cells:
                if celltype.type=='triangle':
                    cells+=[[int(ind) for ind in cell] for cell in celltype.data]
            
        else:
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
         Communication.ask('insert_keyframe_mesh',
                           name_msh=self.name_msh,
                           frame=frame,
                           waiting_time_between_points=waiting_time_between_points)
        
    def cut_mesh(self, plane_points, plane_normals):
        Communication.send('cut_mesh', name_msh=self.name_msh,
                           planes_co=plane_points,
                           planes_no=plane_normals)
    
    def smooth(self):
        Communication.ask('smooth', name_msh=self.name_msh)
    
    def divide(self, Nx=None, Ny=None, Nz=None):
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
        return self._properties[['data', 'use_auto_smooth']]
    
    @use_auto_smooth.setter
    def use_auto_smooth(self, val):
        self._properties[['data', 'use_auto_smooth']]=val
    
    @property
    def auto_smooth_angle(self):
        return self._properties[['data', 'auto_smooth_angle']]
    
    @auto_smooth_angle.setter
    def auto_smooth_angle(self, val):
        self._properties[['data', 'auto_smooth_angle']]=val

    @property
    def parent(self):
        return Object(self.name_obj)

    @property
    def vertices(self):
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
    
                          
                      
                      
            