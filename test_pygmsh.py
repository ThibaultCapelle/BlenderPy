# -*- coding: utf-8 -*-
"""
Created on Mon Aug 31 18:31:14 2020

@author: Thibault
"""

import pygmsh
import numpy as np
from sending_data import send_mesh, delete_all

geom = pygmsh.opencascade.geometry.Geometry(characteristic_length_max=0.005)


polyocc = geom.add_rectangle([-0.5,-0.5,-0.01],1,1)
mesh = pygmsh.generate_mesh(geom)

xmin, xmax, ymin, ymax, zmin, zmax = (np.min(mesh.points[:,0]),
                                      np.max(mesh.points[:,0]),
                                      np.min(mesh.points[:,1]),
                                      np.max(mesh.points[:,1]),
                                      np.min(mesh.points[:,2]),
                                      np.max(mesh.points[:,2]))

for i in range(mesh.points.shape[0]):
    point=mesh.points[i,:]
    mesh.points[i,2]=0.5*np.sin(2.*np.pi*(point[0]-xmin)/(xmax-xmin))*\
                     0.5*np.sin(2.*np.pi*(point[1]-ymin)/(ymax-ymin))
delete_all()
send_mesh(mesh, thickness=0.01)


#%%

def add_truncated_pyramid(base_center, base_widths, height, top_widths):
    geom = pygmsh.opencascade.geometry.Geometry(characteristic_length_max=base_widths[0])
    geom.add_box([base_center[0]-base_widths[0]/2,
                  base_center[1]-base_widths[1]/2,
                  base_center[2]],
                  [base_widths[0],base_widths[1],height])
    mesh = pygmsh.generate_mesh(geom)
    xmin, xmax, ymin, ymax, zmin, zmax = (np.min(mesh.points[:,0]),
                                          np.max(mesh.points[:,0]),
                                          np.min(mesh.points[:,1]),
                                          np.max(mesh.points[:,1]),
                                          np.min(mesh.points[:,2]),
                                          np.max(mesh.points[:,2]))

    x_center, y_center=0.5*(xmax+xmin), 0.5*(ymax+ymin)
    for i in range(mesh.points.shape[0]):
        point=mesh.points[i,:]
        Wx=(point[2]-zmin)/(zmax-zmin)*(top_widths[0]-base_widths[0])+base_widths[0]
        Wy=(point[2]-zmin)/(zmax-zmin)*(top_widths[1]-base_widths[1])+base_widths[1]
        mesh.points[i,0]=x_center+Wx/base_widths[0]*(mesh.points[i,0]-x_center)
        mesh.points[i,1]=y_center+Wy/base_widths[1]*(mesh.points[i,1]-y_center)
    send_mesh(mesh)
    


#%%
    
def add_truncated_pyramid_gmsh(geom, base_center, base_width, height, top_width):
    box=geom.add_box([base_center[0]-base_width/2,
                  base_center[1]-base_width/2,
                  base_center[2]],
                  [base_width,base_width,height])
    xcenter, ycenter, zcenter=base_center
    triangle= geom.add_polygon([[xcenter-base_width/2,ycenter-base_width/2,zcenter],
                                [xcenter-base_width/2,ycenter-base_width/2,zcenter+height],
                                [xcenter-top_width/2,ycenter-base_width/2,zcenter+height]])
    
    cut=geom.extrude(triangle,translation_axis=[0,base_width,0])
    
    box=geom.boolean_difference([box],[cut[1]])
    
    
    triangle= geom.add_polygon([[xcenter-base_width/2,ycenter-base_width/2,zcenter],
                                [xcenter-base_width/2,ycenter-base_width/2,zcenter+height],
                                [xcenter-base_width/2,ycenter-top_width/2,zcenter+height]])
    
    cut=geom.extrude(triangle,translation_axis=[base_width,0,0])
    
    box=geom.boolean_difference([box],[cut[1]])
    
    triangle= geom.add_polygon([[xcenter+base_width/2,ycenter+base_width/2,zcenter],
                                [xcenter+base_width/2,ycenter+base_width/2,zcenter+height],
                                [xcenter+base_width/2,ycenter+top_width/2,zcenter+height]])
    
    cut=geom.extrude(triangle,translation_axis=[-base_width,0,0])
    
    box=geom.boolean_difference([box],[cut[1]])
    
    triangle= geom.add_polygon([[xcenter+base_width/2,ycenter+base_width/2,zcenter],
                                [xcenter+base_width/2,ycenter+base_width/2,zcenter+height],
                                [xcenter+top_width/2,ycenter+base_width/2,zcenter+height]])
    
    cut=geom.extrude(triangle,translation_axis=[0,-base_width,0])
    
    return geom.boolean_difference([box],[cut[1]])
geom = pygmsh.opencascade.geometry.Geometry(characteristic_length_max=1)
box=geom.add_box([-2,-2,-1],[4,4,1])
hole=add_truncated_pyramid_gmsh(geom, [0,0,-1], 1+2/np.tan(np.pi/180*54.7), 1, 1)
geom.boolean_difference([box],[hole])
    


mesh = pygmsh.generate_mesh(geom)
import meshio
meshio.write('mesh.vtk', mesh)
send_mesh(mesh)