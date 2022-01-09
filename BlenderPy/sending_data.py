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

def send(message):
    #print('len : {:010x}'.format(len(message)))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(('{:010x}'.format(len(message))+message).encode())

def receive_all(sock, n):
    # Helper function to recv n bytes or return None if EOF is hit
    data = bytearray()
    i=1
    while len(data) < n:
        #print('packet number {:}'.format(i))
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
        i+=1
    return data  
    
def ask(message):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(('{:010x}'.format(len(message))+message).encode())
        raw_msglen = s.recv(10)
        msglen = int(raw_msglen.decode(),16)
        #print(msglen)
        data=receive_all(s, msglen)
        return json.loads(data)['content']

def parse(message, kwargs=None, **keyargs):
    b=message.find('(')
    res=dict()
    if b==-1:
        res['type']='command'
        res['command']=message
        res['kwargs']=kwargs
        res['args']=[]
    else:
        res['type']='command'
        first_part=message[:b]
        res['command']=first_part
        last_part=message[b:]
        assert last_part.endswith(')') and last_part.startswith('(')
        last_part=last_part[1:-1]
        assert last_part.find('(')==-1 and last_part.find(')')==-1
        data=last_part.split(',')
        args=[]
        if kwargs is None:
            kwargs=dict()
            for i in range(len(data)):
                data[i]=data[i].lstrip('"').rstrip('"')
                if data[i].find('=')!=-1:
                    k,v=data[i].split('=')
                    kwargs[k]=v
                else:
                    args.append(data[i])
        kwargs.update(keyargs)
        res['args']=args
        res['kwargs']=kwargs
    msg=json.dumps(res)
    #print(msg)
    return msg

def delete_all():
    assert ask(parse('delete_all()'))=="DONE"
    
class GeometricEntity:
    
    @property
    def vertices_absolute(self):
        mat=self.matrix_world
        verts=self.vertices
        verts_4D=np.transpose(np.hstack([verts, np.ones((len(verts),1))]))
        return np.transpose(np.dot(mat, verts_4D))
    
    @vertices_absolute.setter
    def vertices_absolute(self, val):
        mat=np.linalg.inv(self.matrix_world)
        if np.array(val).shape[1]!=4:
            val=np.hstack([np.array(val), np.ones((len(val),1))])
        self.vertices=np.transpose(np.dot(mat, np.transpose(val)))[:,:3]
        
    @property
    def xmin(self):
        return np.min(self.vertices_absolute[:,0])
    
    @property
    def xmax(self):
        return np.max(self.vertices_absolute[:,0])
    
    @property
    def ymin(self):
        return np.min(self.vertices_absolute[:,1])
    
    @property
    def ymax(self):
        return np.max(self.vertices_absolute[:,1])
    
    @property
    def zmin(self):
        return np.min(self.vertices_absolute[:,2])
    
    @property
    def zmax(self):
        return np.max(self.vertices_absolute[:,2])
    
    @xmin.setter
    def xmin(self, val):
        self.x=val-self.xmin
    
    @ymin.setter
    def ymin(self, val):
        self.y=val-self.ymin
        
    @zmin.setter
    def zmin(self, val):
        self.z=val-self.zmin
        
    @xmax.setter
    def xmax(self, val):
        self.x=val-self.xmax
        
    @ymax.setter
    def ymax(self, val):
        self.y=val-self.ymax
        
    @zmax.setter
    def zmax(self, val):
        self.z=val-self.zmax
    
    @property
    def center(self):
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
        return self.xmax-self.xmin
    
    @property
    def dy(self):
        return self.ymax-self.ymin
    
    @property
    def dz(self):
        return self.zmax-self.zmin
    
    
    
class Scene:
    
    def __init__(self):
        self._properties=PropertyDict(func='scene_property')
    
    @property
    def frame_current(self):
        return self._properties['frame_current']
    
    @frame_current.setter
    def frame_current(self, val):
        self._properties['frame_current']=val
        
    @property
    def frame_start(self):
        return self._properties['frame_start']
    
    @frame_start.setter
    def frame_start(self, val):
        self._properties['frame_start']=val
        
    @property
    def frame_end(self):
        return self._properties['frame_end']
    
    @frame_end.setter
    def frame_end(self, val):
        self._properties['frame_end']=val

class ShaderDict(dict):
    
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
            ask(parse('set_'+self.func, kwargs=kwargs))
        else:
            kwargs.update(dict({'material_name':self.material_name,
                                'from_name':self.name,
                                'from_key':key,
                                'value':value}))
            ask(parse('set_'+self.func, kwargs=kwargs))
    
    def __getitem__(self, key):
        kwargs=self.params.copy()
        kwargs.update(dict({'material_name':self.material_name,
                     'name':self.name,
                     'key':key}))
        res=ask(parse('get_'+self.func, kwargs=kwargs))
        if isinstance(res, dict):
            node=ShaderNode(**res)
            return ShaderSocket(material_parent=node.parent_name,
                                parent=node, 
                                key=res['socket_name'],
                                shader_socket_type=res['shader_socket_type'])
        else:
            return res

class ShaderSocket:
    
    def __init__(self, material_parent=None, shader_socket_type='input',
                 parent=None, key=None, value=None, **kwargs):
        assert isinstance(parent, ShaderNode)
        self.material_parent=material_parent
        self.parent=parent
        self.key=key
        self.value=value
        self.shader_socket_type=shader_socket_type
        self._properties=PropertyDict('','', func='shadersocket_property',
                                      material_name=self.material_parent,
                                      node_name=self.parent,
                                      socket_key=self.key)
    
    def to_dict(self, **kwargs):
        params=dict({'material_name':self.material_parent,
                     'parent_name':self.parent.name,
                     'key':self.key,
                     'value':self.value})
        params.update(kwargs)
        return params
    
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
            self.name=ask(parse('create_shadernode()', kwargs=kwargs))
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
        send(parse('remove_shader()', kwargs=self.to_dict()))
    
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
        self.name=ask(parse('create_constraint()', kwargs=kwargs))
        self._properties=PropertyDict(self.name, self.parent_name,
                                      func='constraint_property')
    
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
        ask(parse('set_'+self.func,
                   kwargs=kwargs))
    
    def __getitem__(self, key):
        kwargs=self.params.copy()
        kwargs.update(dict({'key':key,
                     'parent_name':self.name,
                     'parent_name_obj':self.name_obj}))
        res=ask(parse('get_'+self.func, kwargs=kwargs))
        if isinstance(res, dict):
            return Object(**res)
        else:
            return res

class Modifier:
    
    def __init__(self, parent=None, modifier_type='CURVE', **kwargs):
        kwargs['modifier_type']=modifier_type
        kwargs['parent_name']=parent
        self.parent_name=parent
        self.name=ask(parse('create_modifier()', kwargs=kwargs))
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
            print(ask(parse('apply_modifier', kwargs=kwargs)))
        
    
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
        send(parse('update_material()', kwargs=params))
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
    
    def get_shader(self, name):
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
            print(tree)
        return return_shader
        
        
    def z_dependant_color(self, positions, colors, z_offset=0, **kwargs):
        params=dict({'colors':[self.convert_color(color) for color in colors],
                     'name':self.material_object,
                     'positions':positions,
                     'z_offset':z_offset})
        params.update(kwargs)
        send(parse('z_dependant_color()', kwargs=params))
    
    def surface_noise(self, scale=3, detail=2, roughness=0.5,
                      orientation='Z', origin='Generated'):
        noise=self.add_shader('Noise')
        coord=self.add_shader('Texture_coordinates')
        sepxyz=self.add_shader('Separate_XYZ')
        sepxyz.inputs['Vector']=coord.outputs['Normal']
        sup=self.add_shader('Math')
        sup.properties['operation']=self.operations['>']
        sup.inputs[0]=sepxyz.outputs[orientation]
        sup.inputs[1]=0.5
        mult=self.add_shader('Math')
        mult.properties['operation']=self.operations['*']
        mult.inputs[0]=sup.outputs['Value']
        
        output=self.get_shader('Material Output')
        noise.inputs['Vector']=coord.outputs[origin]
        mult.inputs[1]=noise.outputs['Fac']
        output.inputs['Displacement']=mult.outputs['Value']
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
    
    def metallic_texture(self, **kwargs):
        send(parse('metallic_texture()', kwargs=kwargs))
    
    def gaussian_laser(self, ZR, W0, I):
        params=dict({'name':self.material_object,
                     'ZR':ZR,
                     'W0':W0,
                     'I':I})
        send(parse('gaussian_laser()', kwargs=params))
        
    def get_material(self, name):
        return ask(parse('get_material({:})'.format(name)))
    
    def create_material(self, name):
        return ask(parse('create_material({:})'.format(name)))
    
    def get_material_names(self):
        return ask(parse('get_material_names()'))
    
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
    
    def load_image_shader_dir(self, directory):
        BSDF=self.get_shader('Principled BSDF')
        output=self.get_shader('Material Output')
        root='-'.join(os.path.split(directory)[1].split('-')[:-1])
        colornode=self.add_shader('Image')
        colornode.properties['image']=Image(os.path.join(directory, root+'_Color.jpg'))
        BSDF.inputs['Base Color']=colornode.outputs['Color']
        
        if root+'_Metalness.jpg' in os.listdir(directory):
            metalnode=self.add_shader('Image')
            metalnode.properties['image']=Image(os.path.join(directory, root+'_Metalness.jpg'))
            BSDF.inputs['Metallic']=metalnode.outputs['Color']
        roughnessnode=self.add_shader('Image')
        roughnessnode.properties['image']=Image(os.path.join(directory, root+'_Roughness.jpg'))
        BSDF.inputs['Roughness']=roughnessnode.outputs['Color']
        normalnode=self.add_shader('Image')
        normalnode.properties['image']=Image(os.path.join(directory, root+'_NormalGL.jpg'))
        BSDF.inputs['Normal']=normalnode.outputs['Color']
        displacementnode=self.add_shader('Image')
        displacementnode.properties['image']=Image(os.path.join(directory, root+'_Displacement.jpg'))
        output.inputs['Displacement']=displacementnode.outputs['Color']

class MetallicMaterial(Material):

    def __init__(self, name, color, target=None, randomness=1, detail=10,
                 roughness=0.5, **kwargs):
        super().__init__(name, color, **kwargs) 
        output=self.get_shader('Material Output')
        glossy=self.add_shader('Glossy')
        output.inputs['Surface']=glossy.outputs['BSDF']
        glossy.inputs['Color']=self.convert_color(color)
        noise=self.add_shader('Noise')
        coord=self.add_shader('Texture_coordinates')
        noise.inputs['Vector']=coord.outputs['Generated']
        output.inputs['Displacement']=noise.outputs['Fac']
        noise.inputs['Scale']=randomness
        noise.inputs['Detail']=detail
        noise.inputs['Roughness']=roughness
        coord.properties['object']=target

class EmissionMaterial(Material):
    
    def __init__(self, color='#AF2020', expression=None, strength=None, **kwargs):
         super().__init__(**kwargs)
         emission=self.add_shader('Emission')
         #emission.inputs['Color']=self.convert_color(color)
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

class ZColorRampMaterial(Material):
    
    def __init__(self, colors=None, positions=None, **kwargs):
        super().__init__(**kwargs)
        coord=self.add_shader('Texture_coordinates')
        sep=self.add_shader('Separate_XYZ')
        sep.inputs['Vector']=coord.outputs['Generated']
        color_ramp=self.add_shader('Color_Ramp')
        color_ramp.inputs['Fac']=sep.outputs['Z']
        color_ramp.properties['color_ramp']=dict({'positions':positions,
                             'colors':[self.convert_color(color) for color in colors]})
        principled=self.get_shader('Principled BSDF')
        principled.inputs['Base Color']=color_ramp.outputs['Color']
            
class GaussianLaserMaterial(EmissionMaterial):
    
    def __init__(self, alpha=0.001, waist=0.1, strength=3, **kwargs):
        expression='{:}e^(-((x-0.5)^2+(y-0.5)^2)/{:}/(1+(z-0.5)^2/{:}))'.format(strength, alpha, waist**2)
        super().__init__(expression=expression, **kwargs) 

class Collection:
    
    def __init__(self, name=None, **kwargs):
        self.name_col=ask(parse('create_collection()', name=name))
        self._properties=PropertyDict('', self.name_col, func='collection_property')
    
    def link(self, obj):
        assert isinstance(obj, Object)
        ask(parse('link_object', name_col=self.name_col,
                  name_obj=obj.name_obj))
    
    @property
    def properties(self):
        return self._properties
    
class Object:
    
    def __init__(self, name_obj=None, filepath=None, **kwargs):
        if name_obj is not None:
            self.name_obj=name_obj
        self._properties=PropertyDict('', self.name_obj, func='object_property')
        self.constraints=[]
        self.modifiers=[]
        if filepath is not None:
            self.load(filepath)
    
    def assign_material(self, material):
        if isinstance(material, list):
            kwargs = dict({'name_obj':self.name_obj,
                           'name_mat':[mat.material_object for mat in material]})
        else:
            kwargs = dict({'name_obj':self.name_obj,
                           'name_mat':material.material_object})
        send(parse('assign_material()', kwargs=kwargs))
    
    def load(self, filepath):
        with open(filepath, 'r') as f:
            data=json.load(f)
        for k, v in data.items():
            self.properties[k]=v
    
    def duplicate(self):
        return Object(name_obj=ask(parse('duplicate()', name_obj=self.name_obj)))
    
    def follow_path(self, target=None, use_curve_follow=True,
                    forward_axis='FORWARD_X'):
        constraint=self.assign_constraint(constraint_type='FOLLOW_PATH')
        constraint.properties['target']=target
        constraint.properties['use_curve_follow']=use_curve_follow
        constraint.properties['forward_axis']=forward_axis
        self.constraints.append(constraint)
    
    def insert_keyframe(self, key, frame='current'):
        send(parse('insert_keyframe_object()', key=key, frame=frame,
                   name_obj=self.name_obj))
        
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
        send(parse('remove_object', kwargs=self.to_dict()))
        
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
    
    def __init__(self, name='camera', location=[5,5,5], rotation=[0,0,0],
                 **kwargs):
        self.add_camera(name, location, rotation)
        super().__init__(**kwargs)
    
    def add_camera(self, name, location, rotation):
        res=dict()
        kwargs = dict()
        kwargs['location']=location
        kwargs['rotation']=rotation
        kwargs['name']=name
        res['type']='camera'
        res['args']=[]
        res['command']='create_camera'
        res['kwargs']=kwargs
        self.name, self.name_obj=ask(json.dumps(res))
        
class Cube(Object):
    
    def __init__(self, name, location, size):
        self.add_cube(name, location, size)
        super().__init__()
        
    def add_cube(self, name, location, size):
        res=dict()
        kwargs = dict()
        kwargs['location']=location
        kwargs['size']=size
        kwargs['name']=name
        res['type']='cube'
        res['args']=[]
        res['command']='create_cube'
        res['kwargs']=kwargs
        self.name, self.name_obj=ask(json.dumps(res))

class Lattice(Object):
    
    def __init__(self, **kwargs):
        self.name, self.name_obj=ask(parse('create_lattice()', kwargs=kwargs)) 
        self._lattice_properties=PropertyDict(name=self.name, function='lattice_property')
        super().__init__()
    
    @property
    def lattice_properties(self):
        return self._lattice_properties
    
    @property
    def points(self):
        kwargs=dict({'name':self.name})
        return np.array(ask(parse('get_lattice_points()', kwargs=kwargs)))
        

class Curve(Object):
    
    def __init__(self, points, **kwargs):
        kwargs['points']=points
        self.name, self.name_obj=ask(parse('create_curve()', kwargs=kwargs)) 
        super().__init__()
    
    @property
    def points(self):
        kwargs=dict({'name':self.name, 'name_obj':self.name_obj})
        return np.array(ask(parse('get_curve_points()', kwargs=kwargs)))
    
    @points.setter
    def points(self, val):
        if hasattr(val, 'tolist'):
            val=val.tolist()
        kwargs=dict({'name':self.name, 'points':val})
        send(parse('set_curve_points()', kwargs=kwargs))
        
class Plane(Object):
    
    def __init__(self, name='plane', location=[0.,0.,0.], size=10, **kwargs):
        self.add_plane(name, location, size)
        
    def add_plane(self, name, location, size):
        res=dict()
        kwargs = dict()
        kwargs['location']=location
        kwargs['size']=size
        kwargs['name']=name
        res['type']='plane'
        res['args']=[]
        res['command']='create_plane'
        res['kwargs']=kwargs
        self.name, self.name_obj=ask(json.dumps(res))
        
class Light(Object):
    
    def __init__(self, name='light', location=[0.,0.,0.],
                 power=2, radius=0.25, light_type='POINT'):
        self.add_light(name, light_type=light_type)
        super().__init__()
        self._light_properties=PropertyDict(self.name,
                                           self.name_obj,
                                           func='light_property')
        self.light_properties['energy']=power
        self.light_properties['shadow_soft_size']=radius
        self.location=location
        
    def add_light(self, name, light_type='POINT'):
        res=dict()
        kwargs = dict()
        kwargs['light_type']=light_type
        res['args']=[]
        res['command']='create_light'
        res['kwargs']=kwargs
        self.name, self.name_obj=ask(json.dumps(res))
    
    @property
    def light_properties(self):
        return self._light_properties
        

class Mesh(Object, GeometricEntity):
    
    def __init__(self, mesh=None, cells=None, points=None,
                 thickness=None, name='mesh', subdivide=1, **kwargs):
        self.subdivide=subdivide
        self.thickness=thickness
        self.cells=cells
        self.points=points
        self.mesh=mesh
        self.name_obj, self.name_msh = self.send_mesh(self.mesh, 
                                                      thickness=self.thickness,
                                                      name=name)
        super().__init__()
        
    def send_mesh(self, mesh, thickness=None, name='mesh'):
        if self.mesh is not None:
            points, cells = self.mesh.points, self.mesh.cells
            res=dict()
            kwargs = dict()
            kwargs['points']=[[float(coord) for coord in p] for p in points]
            kwargs['cells']=[]
            for celltype in cells:
                if celltype.type=='triangle':
                    kwargs['cells']+=[[int(ind) for ind in cell] for cell in celltype.data]
            
        else:
            points, cells = self.points, self.cells
            kwargs = dict()
            res=dict()
            kwargs['points']=[[coord for coord in p] for p in points]
            kwargs['cells']=[]
            for celltype in cells:
                if not isinstance(celltype[0], str):
                    kwargs['cells']+=[[int(ind) for ind in celltype]]
                elif celltype[0]=='triangle':
                    kwargs['cells']+=[[int(ind) for ind in cell] for cell in celltype[1]]
         
        kwargs['name']=name
        kwargs['thickness']=thickness
        kwargs['subdivide']=self.subdivide
        res['type']='mesh'
        res['args']=[]
        res['command']='create_mesh'
        res['kwargs']=kwargs
        return ask(json.dumps(res)) 
    
    def make_oscillations(self, target_scale=[1,1,1],
                          target_rotation =[0,0,0], target_motion=[0,0,0],
                          center_scale=[1,1,1], center_rotation=[0,0,0],
                          center_motion=[0,0,0], Q=0,
                          N_frames=40, N_oscillations=10):
        kwargs = dict({'name_obj':self.name_obj,
                       'target_scale':target_scale,
                       'target_rotation':target_rotation,
                       'target_motion':target_motion,
                       'N_frames':N_frames,
                       'N_oscillations':N_oscillations,
                       'Q':Q,
                       'center_motion':center_motion,
                       'center_scale':center_scale,
                       'center_rotation':center_rotation})
        assert ask(parse('make_oscillations()', kwargs=kwargs))=="DONE"
    
    def insert_mesh_keyframe(self, frame='current'):
         kwargs = dict({'name_msh':self.name_msh, 'frame':frame})
         send(parse('insert_keyframe_mesh()', kwargs=kwargs))
        
    def cut_mesh(self, plane_points, plane_normals):
        kwargs = dict({'name_msh':self.name_msh,
                       'planes_co':plane_points,
                       'planes_no':plane_normals})
        send(parse('cut_mesh()', kwargs=kwargs))
    
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
    def parent(self):
        return Object(self.name_obj)

    @property
    def vertices(self):
        kwargs = dict({'name_msh':self.name_msh})
        return np.array(ask(parse('get_vertices()', kwargs=kwargs)))
    
    @vertices.setter
    def vertices(self, val):
        if hasattr(val, 'tolist'):
            val=val.tolist()
        kwargs = dict({'name_msh':self.name_msh,
                       'val':val})
        send(parse('set_vertices()', kwargs=kwargs))
    
    @property
    def cursor_location(self):
        res=dict()
        kwargs = dict()
        kwargs['name']=self.name_obj
        res['args']=[]
        res['command']='get_cursor_location'
        res['kwargs']=kwargs
        return ask(json.dumps(res)) 
    
    @cursor_location.setter
    def cursor_location(self, val):
        res=dict()
        kwargs = dict()
        kwargs['name']=self.name_obj
        kwargs['location']=val
        res['args']=[]
        res['command']='set_cursor_location'
        res['kwargs']=kwargs
        send(json.dumps(res))
        

if __name__=='__main__':
    import pygmsh
    delete_all()
    material=Material('hello', '#F5D15B', alpha=0.5, blend_method='BLEND')
    geom=pygmsh.opencascade.geometry.Geometry(characteristic_length_max=0.25)

    mirror_1=geom.add_cylinder([0,0,0],
                               [0,0,1], 1)
    mesh = pygmsh.generate_mesh(geom)
    mirror_1_mesh=Mesh(mesh, name='mirror_1')
    '''mirror_1_mesh.assign_material(material)
    material.z_dependant_color([0.,0.5,1.],
                               ['#3213CDFF',
                                '#FFFFFF10',
                                '#F60818FF'])'''
    mirror_1_mesh.make_oscillations(target_scale=[1,1,2])
    
                          
                      
                      
            