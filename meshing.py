# -*- coding: utf-8 -*-
"""
Created on Wed Oct 20 10:50:42 2021

@author: Thibault
"""

from shapely import geometry
import triangle
import pygmsh
import numpy as np
from sending_data import (Material, Mesh, delete_all,
                          Light, Camera, Curve, Object,
                          ShaderNode)
thick_membrane=0.025


class Plane_Geom(Object):
    
    def __init__(self, name='', thickness=1,
                 characteristic_length_max=0.03,
                 material=Material('nitrure', '#F5D15B', alpha=0.3, blend_method='BLEND',
                 use_backface_culling=True, blend_method_shadow='NONE'),
                 rounding_decimals=12, subdivide=1):
        self.subdivide=subdivide
        self.name=name
        self.thickness=thickness
        self.geom=pygmsh.opencascade.geometry.Geometry(characteristic_length_max=characteristic_length_max)
        self.material=material
        self.rounding_decimals=rounding_decimals
    
    def send_to_blender(self, use_triangle=False):
        if not use_triangle:
            self._pymesh=pygmsh.generate_mesh(self.geom)
            self._blender_mesh=Mesh(mesh=self._pymesh, name=self.name,
                                    thickness=self.thickness,
                                    subdivide=self.subdivide)
        else:
            self.generate_triangulation_from_shapely_LineString(self.line)
            self._blender_mesh=Mesh(cells=self.cells, points=self.cell_points, name=self.name,
                                    thickness=self.thickness,
                                    subdivide=self.subdivide)
        self.name_obj=self._blender_mesh.name_obj
        self._blender_mesh.assign_material(self.material)
    
    def format_line(self, line, gmsh=True):
        if not gmsh:
            x_s, y_s=line.xy
            res = [(x,y,0) for x,y in zip(x_s, y_s)]
            if res[-1]==res[0]:
                res=res[:-1]
            return res
        else:
            x_s, y_s=line.xy
            xy=[(np.around(x, decimals=self.rounding_decimals),
                      np.around(y, decimals=self.rounding_decimals),0) for x,y in zip(np.array(x_s), np.array(y_s))][:-1]
            i=0
            while (i+1)<len(xy):
                if xy[i+1]==xy[i]:
                    xy.remove(xy[i+1])                
                else:
                    i=i+1
            if xy[0]==xy[-1]:
                xy.remove(xy[-1])
            return xy
    
    def generate_polygon_from_shapely_LineString(self, poly):
        if hasattr(poly, 'exterior'):
            self.xy=self.format_line(poly.exterior)
        else:
            self.xy=self.format_line(poly)
        self.holes=[]
        if len(poly.interiors)==0:
            return self.geom.add_polygon([[p[0], p[1], 0] for p in self.xy])
        else:
            for interior in poly.interiors:
                xy=self.format_line(interior)
                x_s, y_s=interior.xy
                self.holes.append(self.geom.add_polygon(xy))
            self.poly=self.geom.add_polygon(self.xy)
            for hole in self.holes:
                self.poly=self.geom.boolean_difference([self.poly.surface], [hole.surface])
                
            return self.poly
    
    def generate_triangulation_from_shapely_LineString(self, poly):
        if hasattr(poly, 'exterior'):
            self.xy=self.format_line(poly.exterior, gmsh=False)
        else:
            self.xy=self.format_line(poly, gmsh=False)
        self.holes=[]
        xy=[[p[0], p[1]] for p in self.xy]
        self._to_triangle_vertices=xy
        self._to_triangle_segments=[(len(xy)-1,0)]+\
                        [(i,i+1) for i in range(len(xy)-1)]
        if not hasattr(poly, 'interiors') or  hasattr(poly, 'interiors') and len(poly.interiors)==0:
            t=triangle.triangulate({'vertices': self._to_triangle_vertices,
                        'segments': self._to_triangle_segments},
                       opts="p")
            self.cell_points, self.cells = ([p+[0.] for p in t['vertices'].tolist()],
                                       [("triangle", t['triangles'].tolist())])
        else:
            holes=[]
            for interior in poly.interiors:
                xy=self.format_line(interior, gmsh=False)
                xy=[[p[0], p[1]] for p in xy]
                N=len(self._to_triangle_vertices)
                self._to_triangle_segments+=[(N+len(xy)+-1,N)]+\
                        [(N+i,N+i+1) for i in range(len(xy)-1)]
                self._to_triangle_vertices+=xy
                holes.append([p[0] for p in interior.centroid.xy])
            t=triangle.triangulate({'vertices': self._to_triangle_vertices,
                            'segments': self._to_triangle_segments,
                            'holes':holes},
                           opts="p")
            self.cell_points, self.cells = ([p+[0.] for p in t['vertices'].tolist()],
                                       [("triangle", t['triangles'].tolist())])
            
    
class Path(Plane_Geom):

    def __init__(self, points, width, cap_style='flat',
                 join_style='round', resolution=16,
                 **kwargs):
        super().__init__(**kwargs)
        self.resolution=resolution
        self.width=width
        self.points=points
        self.cap_style_dict=dict({'flat':2,
                                  'round':1,
                                  'square':3})
        self.join_style_dict=dict({'mitre':2,
                                  'round':1,
                                  'bevel':3})
        self.cap_style=self.cap_style_dict[cap_style]
        self.join_style=self.join_style_dict[join_style]
        self.generate()
    
    def generate(self):
        self.line=geometry.LineString(self.points).buffer(self.width/2.,
                                cap_style=self.cap_style,
                                join_style=self.join_style,
                                resolution=self.resolution)
        self.generate_polygon_from_shapely_LineString(self.line)
        
class Arrow(Plane_Geom):
    
    def __init__(self, head_width=0.1, head_length=0.2,
                 length=1, width=0.05, **kwargs):
        super().__init__(**kwargs)
        self.head_width=head_width
        self.head_length=head_length
        self.length=length
        self.width=width
        self.generate()
    
    def generate(self):
        self.line=geometry.LineString([(0,0,0), (self.length,0,0)]).buffer(self.width/2.)
        self.poly=self.generate_polygon_from_shapely_LineString(self.line)
        self.head=self.geom.add_polygon([(self.length,-self.head_width/2,0),
                                         (self.length+self.head_length,0,0),
                                         (self.length,self.head_width/2,0)])
        self.arrow=self.geom.boolean_union([self.poly, self.head])
    
class Polygon(Plane_Geom):
    
    def __init__(self, points,
                 **kwargs):
        super().__init__(**kwargs)
        self.points=points
        self.generate()
    
    def generate(self):
        self.line=geometry.LineString(self.points)
        self.xy=self.format_line(self.line)
        self.geom.add_polygon(self.xy)

class Cylinder(Plane_Geom):
    
    def __init__(self, radius=1, height=1,
                 **kwargs):
        self.line=geometry.Point(0,0).buffer(1.0).exterior
        super().__init__(thickness=height, **kwargs)
    
width_antenna=0.5
thick_substrate=0.5
W_cell, H_cell = 10, 7.500
width_SMA, length_SMA, width_SMA_bis=1.500, 2.000,  2.000
width_cut=.100
width_circuit=.120
distance_from_side=.300
input_gap=.735
W_loop, H_loop=1.725,.735
edge_loop_distance=.200




delete_all()

path=Path([(0,0), (1,0), (1,1), (0,1), (0,0)], 0.1, name='yolo',
           thickness=None, cap_style='square', join_style='mitre',
           characteristic_length_max=1e-1)
path.send_to_blender(use_triangle=True)


antenna=Path([(distance_from_side,
                      distance_from_side),
                    (distance_from_side,length_SMA+distance_from_side),
                    (W_cell/2-input_gap/2,length_SMA+distance_from_side),
                    (W_cell/2-input_gap/2,H_cell-edge_loop_distance-H_loop),
                    (W_cell/2-W_loop/2,H_cell-edge_loop_distance-H_loop),
                    (W_cell/2-W_loop/2,H_cell-edge_loop_distance),
                    (W_cell/2+W_loop/2,H_cell-edge_loop_distance),
                    (W_cell/2+W_loop/2,H_cell-edge_loop_distance-H_loop),
                    (W_cell/2+input_gap/2,H_cell-edge_loop_distance-H_loop),
                    (W_cell/2+input_gap/2,length_SMA+distance_from_side),
                    (W_cell/2+width_SMA/2+distance_from_side,
                     length_SMA+distance_from_side),
                    (W_cell/2+width_SMA/2+distance_from_side,
                     distance_from_side)][::-1], width_circuit,
                     thickness=0.1, subdivide=2)
arrow=Arrow(length=5, width=0.15, head_width=0.3, thickness=None)
arrow.send_to_blender()
curve_2=Curve([[p[0], p[1], 0.0] for p in antenna.points], name='translate')
#curve=Curve([[p[0], p[1], np.cos(i/100*np.pi)] for i,p in enumerate(antenna.points)], name='hello')
curve=Curve([(theta,0.5*np.sin(theta)*np.sin(30*theta),0) for theta in np.linspace(0, 10*np.pi, 3000)], name='hello')

antenna.send_to_blender(use_triangle=True)
curve.location=list(antenna.points[-1])+[0.]
#arrow.follow_path(curve_2)
arrow.curve_modifier(curve_2)
c=Cylinder(height=arrow.length,
           subdivide=10,
           radius=arrow.width)
c.send_to_blender(use_triangle=True)
c.rotation=[0,np.pi/2,0]
c.curve_modifier(curve_2)
c.copy_location(arrow)
material=Material('metal', '#5E5C5C', alpha=1., blend_method='OPAQUE',
                 use_backface_culling=False, blend_method_shadow='NONE')
glow=Material("glow", '#D70A0A')
glow.glowing()
arrow.assign_material(glow)
material.metallic_texture()
antenna.assign_material(material)

glow.coordinate_expression('-4e^(-(x^2+y^2)/(0.1)^2)')

#%%
'''Wx_membrane, Wy_membrane = 10, 10
Wx_membrane_2, Wy_membrane_2 = 5, 5
geom=pygmsh.opencascade.geometry.Geometry(characteristic_length_max=0.03)
membrane = geom.add_rectangle([-Wx_membrane/2,-Wy_membrane/2,0],
                              Wx_membrane,Wy_membrane, corner_radius=0.01)
rectangle_2=geom.add_rectangle([-Wx_membrane_2/2,-Wy_membrane_2/2,0],
                              Wx_membrane_2,Wy_membrane_2, corner_radius=0.005)
membrane_gmsh=geom.boolean_difference([membrane], [rectangle_2])
mesh = pygmsh.generate_mesh(geom)
membrane=Mesh(mesh, name='membrane', thickness=thick_membrane)

nitrure=Material('nitrure', '#F5D15B', alpha=0.3, blend_method='BLEND',
                 use_backface_culling=True, blend_method_shadow='NONE')
membrane.assign_material(nitrure)'''
path=Path([(0,0), (1,0), (1,1), (0,1), (0,0)], 0.1, name='yolo',
           thickness=None, cap_style='round', join_style='round',
           characteristic_length_max=1e-1)

path.send_to_blender()

arrow=Arrow(length=5, thickness=None)
arrow.send_to_blender()
curve=Curve([(theta,0.5*np.sin(theta)*np.sin(30*theta),0) for theta in np.linspace(0, 10*np.pi, 3000)], name='hello')
curve_2=Curve([(theta,0,0) for theta in np.linspace(0, 10*np.pi*6, 100)], name='translate')

arrow.follow_path(curve_2)
arrow.curve_modifier(curve)
'''
from sending_data import Curve, delete_all
import numpy as np
delete_all()
curve=Curve([(theta,np.sin(theta),0) for theta in np.linspace(0, 10*np.pi, 100)], name='hello')'''
'''
geom = pygmsh.opencascade.geometry.Geometry(characteristic_length_max=0.03)
geom.add_polygon([(0,0,0),(0,1,0),(1,1,0),(1,0,0)])
mesh = pygmsh.generate_mesh(geom)
membrane=Mesh(mesh, name='membrane', thickness=thick_membrane)

nitrure=Material('nitrure', '#F5D15B', alpha=0.3, blend_method='BLEND',
                 use_backface_culling=True, blend_method_shadow='NONE')
membrane.assign_material(nitrure)'''