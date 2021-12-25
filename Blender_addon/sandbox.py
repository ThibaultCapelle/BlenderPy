# -*- coding: utf-8 -*-
"""
Created on Fri Aug 28 17:51:50 2020

@author: Thibault
"""

from Blender_server.sending_data import delete_all, Cube
from Blender_server.meshing import Cylinder, Box
import numpy as np

delete_all()

thick=0.1
Lx=2
Ly=2
w_trench=0.2
L_trench=5*w_trench
w_bloc=0.4
L_bloc=0.2
membrane=Box('membrane',
             Lx=Lx, Ly=Ly, Lz=thick)
cylinder1=Cylinder(radius=w_trench/2, height=2*thick)

cylinder1.properties['scale']=[L_trench/w_trench,1.,1.]
bloc=Box('phono', Lx=L_bloc, Ly=w_bloc, Lz=2*thick)
#%%
cylinder1.properties['location']=[Lx/4,Ly/4,-thick]
cylinder1.properties['rotation_euler']=[0,0,np.pi/4]
cylinder2=Cylinder(radius=0.1, height=1.5)
cylinder2.properties['location']=[Lx/4,-Ly/4,-0.75]
cylinder2.properties['scale']=[5,1.,1.]
cylinder2.properties['rotation_euler']=[0,0,-np.pi/4]
cylinder3=Cylinder(radius=0.1, height=1.5)
cylinder3.properties['location']=[-Lx/4,-Ly/4,-0.75]
cylinder3.properties['scale']=[5,1.,1.]
cylinder3.properties['rotation_euler']=[0,0,np.pi/4]
cylinder4=Cylinder(radius=0.1, height=1.5)
cylinder4.properties['location']=[-Lx/4,Ly/4,-0.75]
cylinder4.properties['scale']=[5,1.,1.]
cylinder4.properties['rotation_euler']=[0,0,-np.pi/4]
#%%
for cylinder in [cylinder1, cylinder2, cylinder3, cylinder4]:
    boolean=membrane.assign_modifier(modifier_type='BOOLEAN')
    boolean.properties['object']=cylinder
    boolean.apply()
#%%
from BlenderPy import meshing, sending_data
sending_data.delete_all()
box=meshing.Box()
verts=box._blender_mesh.vertices   
box._blender_mesh.insert_keyframe(frame=0) 
verts[0][1]=3
box._blender_mesh.vertices=verts
box._blender_mesh.insert_keyframe(frame=100) 
print(sending_data.Scene().frame_start)
print(sending_data.Scene().frame_end)