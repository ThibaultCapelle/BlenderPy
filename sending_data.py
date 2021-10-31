# -*- coding: utf-8 -*-
"""
Created on Wed Aug 26 09:56:27 2020

@author: Thibault
"""

import socket, json
from parsing import Expression
import numpy as np
HOST = '127.0.0.1'
PORT = 20000

def send(message):
    print('len : {:010x}'.format(len(message)))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(('{:010x}'.format(len(message))+message).encode())

def receive_all(sock, n):
    # Helper function to recv n bytes or return None if EOF is hit
    data = bytearray()
    i=1
    while len(data) < n:
        print('packet number {:}'.format(i))
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
        print(msglen)
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
    print(msg)
    return msg

def delete_all():
    assert ask(parse('delete_all()'))=="DONE"

class ShaderDict(dict):
    
    def __init__(self, name, material_name, func, **kwargs):
        super().__init__()
        self.name=name
        self.material_name=material_name
        self.func=func
        self.params=kwargs
        
    def __setitem__(self, key, value):
        kwargs=self.params.copy()
        if isinstance(value, ShaderSocket):
            kwargs.update(value.todict(from_name=self.name,
                                       from_key=key))
            send(parse('set_'+self.func, kwargs=kwargs))
        else:
            kwargs.update(dict({'material_name':self.material_name,
                                'from_name':self.name,
                                'from_key':key,
                                'value':value}))
            send(parse('set_'+self.func, kwargs=kwargs))
    
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
                                key=res['socket_name'])
        else:
            return res

class ShaderSocket:
    
    def __init__(self, material_parent=None,
                 parent=None, key=None, value=None, **kwargs):
        assert isinstance(parent, ShaderNode)
        self.material_parent=material_parent
        self.parent=parent
        self.key=key
        self.value=value
        self._properties=PropertyDict('','', func='shadersocket_property',
                                      material_name=self.material_parent,
                                      node_name=self.parent,
                                      socket_key=self.key)
    
    def todict(self, **kwargs):
        params=dict({'material_name':self.material_parent,
                     'parent_name':self.parent.name,
                     'key':self.key,
                     'value':self.value})
        params.update(kwargs)
        return params
    
    @property
    def properties(self):
        return self._properties
    
        
class ShaderNode:
    
    def __init__(self, parent=None, shader_type='Emission',
                 name=None, **kwargs):
        assert parent is not None
        self._shadertype_dict=dict({'Emission':'ShaderNodeEmission',
                         'Add':'ShaderNodeAddShader',
                         'Math':'ShaderNodeMath',
                         'Texture_coordinates':'ShaderNodeTexCoord',
                         'Separate_XYZ':'ShaderNodeSeparateXYZ'})
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
    
    def todict(self, **kwargs):
        params=dict({'parent_name':self.parent_name,
                     'name':self.name})
        params.update(kwargs)
        return params
    
    def _format_type(self, key):
        assert key in self._shadertype_dict.keys()
        return self._shadertype_dict[key]
    
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
    
    def __init__(self, name, name_obj, func=None, **kwargs):
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
        if isinstance(value, Object):
            value=value.todict()
        kwargs['val']=value
        send(parse('set_'+self.func,
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
        self._properties=PropertyDict(self.name, self.parent_name, func='modifier_property')
    
    @property
    def properties(self):
        return self._properties
    
        
    
class Material:
    
    def __init__(self, name, color, alpha=1., transmission=0,
                 use_screen_refraction=False, refraction_depth=0.,
                 blend_method='OPAQUE', blend_method_shadow='OPAQUE',
                 use_backface_culling=False,
                 metallic=0.,
                 **kwargs):
        names = self.get_material_names()
        if name in names:
            self.material_object = self.get_material(name)
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
                         '^':'POWER'})
    
    def add_shader(self, shader_type):
        return ShaderNode(shader_type=shader_type,
                          parent=self.material_object)
    
    def coordinate_expression(self, exp, input_shader=None, special_keys=None):
        e=Expression(content=exp, tokens=[])
        if not e.isleaf():
            self.distribute_shaders(e.get_tree(),input_shader=input_shader,
                                        special_keys=special_keys)
    
    def distribute_shaders(self, tree, input_shader=None, special_keys=None):
        if isinstance(tree, dict):
            operation=list(tree.keys())[0]
            tree['shader']=self.add_shader(shader_type='Math')
            tree['shader'].properties['operation']=self.operations[operation]
            subtree=tree[operation]
            for node in subtree:
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
                        if node in special_keys:
                            tree['shader'].inputs[i]=input_shader.outputs[node]
                            
        else:
            print(tree)
        
        
    def z_dependant_color(self, positions, colors, z_offset=0, **kwargs):
        params=dict({'colors':[self.convert_color(color) for color in colors],
                     'name':self.material_object,
                     'positions':positions,
                     'z_offset':z_offset})
        params.update(kwargs)
        send(parse('z_dependant_color()', kwargs=params))
    
    def glowing(self, **kwargs):
        send(parse('glowing()', kwargs=kwargs))
    
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
    
class Object:
    
    def __init__(self, name_obj=None, **kwargs):
        if name_obj is not None:
            self.name_obj=name_obj
    
    def assign_material(self, material):
        kwargs = dict({'name_obj':self.name_obj,
                       'name_mat':material.material_object})
        send(parse('assign_material()', kwargs=kwargs))
    
    def follow_path(self, target=None, use_curve_follow=True,
                    forward_axis='FORWARD_X'):
        self.assign_constraint(constraint_type='FOLLOW_PATH')
        self.constraint.properties['target']=target
        self.constraint.properties['use_curve_follow']=use_curve_follow
        self.constraint.properties['forward_axis']=forward_axis
    
    def assign_constraint(self, constraint_type='FOLLOW_PATH', **kwargs):
        self.constraint=Constraint(parent=self._blender_mesh.name_obj,
                                   constraint_type=constraint_type,
                                   **kwargs)
    
    def curve_modifier(self, target=None, deform_axis='POS_X'):
        self.assign_modifier(modifier_type='CURVE')
        self.modifier.properties['object']=target
        self.modifier.properties['deform_axis']=deform_axis
    
    def assign_modifier(self, modifier_type='CURVE', **kwargs):
        self.modifier=Modifier(parent=self._blender_mesh.name_obj,
                                   modifier_type=modifier_type,
                                   **kwargs)
    
    def copy_location(self, target=None):
        self.assign_constraint(constraint_type='COPY_LOCATION')
        self.constraint.properties['target']=target
    
    def todict(self):
        return dict({'name_obj':self.name_obj})
        
    
    @property
    def location(self):
        kwargs = dict({'name_obj':self.name_obj})
        res=dict({'kwargs':kwargs, 'args':[],
                  'command':'get_object_location'})
        return ask(json.dumps(res))
    
    @location.setter
    def location(self, val):
        if len(val)<3:
            val=list(val)+[0. for i in range(3-len(val))]
        kwargs = dict({'name_obj':self.name_obj,
                       'location':val})
        res=dict({'kwargs':kwargs, 'args':[],
                  'command':'set_object_location'})
        send(json.dumps(res))
        
    @property
    def rotation(self):
        kwargs = dict({'name_obj':self.name_obj})
        res=dict({'kwargs':kwargs, 'args':[],
                  'command':'get_object_rotation'})
        return ask(json.dumps(res))
    
    @rotation.setter
    def rotation(self, val):
        kwargs = dict({'name_obj':self.name_obj,
                       'rotation':val})
        res=dict({'kwargs':kwargs, 'args':[],
                  'command':'set_object_rotation'})
        send(json.dumps(res))
    
    @property
    def scale(self):
        kwargs = dict({'name_obj':self.name_obj})
        res=dict({'kwargs':kwargs, 'args':[],
                  'command':'get_object_scale'})
        return ask(json.dumps(res))
    
    @scale.setter
    def scale(self, val):
        kwargs = dict({'name_obj':self.name_obj,
                       'scale':val})
        res=dict({'kwargs':kwargs, 'args':[],
                  'command':'set_object_scale'})
        send(json.dumps(res))

class Camera(Object):
    
    def __init__(self, name, location, rotation):
        self.add_camera(name, location, rotation)
    
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

class Curve(Object):
    
    def __init__(self, points, **kwargs):
        res=dict()
        kwargs['points']=points
        res['points']=points
        res['type']='curve'
        res['args']=[]
        res['command']='create_curve'
        res['kwargs']=kwargs
        self.name, self.name_obj=ask(json.dumps(res))
        
class Plane(Object):
    
    def __init__(self, name, location, size):
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
    
    def __init__(self, name, location, power, radius=0.25):
        self.add_light(name, location, power, radius)
        
    def add_light(self, name, location, power, radius):
        res=dict()
        kwargs = dict()
        kwargs['location']=location
        kwargs['power']=power
        kwargs['radius']=radius
        kwargs['name']=name
        res['type']='light'
        res['args']=[]
        res['command']='create_light'
        res['kwargs']=kwargs
        self.name, self.name_obj=ask(json.dumps(res))
        
    @property
    def power(self):
        res = dict()
        kwargs = dict()
        kwargs['name']=self.name
        kwargs['name_obj']=self.name_obj
        res['command']='get_light_power'
        res['args']=[]
        res['kwargs']=kwargs
        return ask(json.dumps(res))
    
    @power.setter
    def power(self, val):
        res = dict()
        kwargs = dict()
        kwargs['name']=self.name
        kwargs['name_obj']=self.name_obj
        kwargs['power']=val
        res['command']='set_light_power'
        res['args']=[]
        res['kwargs']=kwargs
        send(json.dumps(res))
        

class Mesh:
    
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
        
    def send_mesh(self, mesh, thickness=None, name='mesh'):
        if self.mesh is not None:
            points, cells = self.mesh.points, self.mesh.cells
            res=dict()
            kwargs = dict()
            kwargs['points']=[[coord for coord in p] for p in points]
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
                if celltype[0]=='triangle':
                    kwargs['cells']+=[[int(ind) for ind in cell] for cell in celltype[1]]
            print(kwargs)
         
        kwargs['name']=name
        kwargs['thickness']=thickness
        kwargs['subdivide']=self.subdivide
        res['type']='mesh'
        res['args']=[]
        res['command']='create_mesh'
        res['kwargs']=kwargs
        return ask(json.dumps(res)) 
    
    def assign_material(self, material):
        kwargs = dict({'name_obj':self.name_obj,
                       'name_mat':material.material_object})
        send(parse('assign_material()', kwargs=kwargs))
    
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
    
                          
                      
                      
            