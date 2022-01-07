# -*- coding: utf-8 -*-
"""
Created on Wed Oct 20 10:50:42 2021

@author: Thibault
"""

from shapely import geometry
import triangle
import pygmsh
import numpy as np
from BlenderPy.sending_data import (Material, Mesh, delete_all,
                          Light, Camera, Curve, Object,
                          ShaderNode, Plane, GeometricEntity)
    
class PlaneGeom(Mesh, GeometricEntity):
    
    def __init__(self, name='', thickness=1,
                 characteristic_length_max=0.03,
                 material=Material('nitrure', '#F5D15B', alpha=0.3, blend_method='BLEND',
                 use_backface_culling=True, blend_method_shadow='NONE'),
                 rounding_decimals=12, subdivide=1, refine=None):
        self.refine=refine
        self.subdivide=subdivide
        self.name=name
        self.thickness=thickness
        self.geom=pygmsh.opencascade.geometry.Geometry(characteristic_length_max=characteristic_length_max)
        self.material=material
        self.rounding_decimals=rounding_decimals
    
    def send_to_blender(self, use_triangle=False, from_external_loading=False):
        if not use_triangle and not from_external_loading:
            self._pymesh=pygmsh.generate_mesh(self.geom)
            super().__init__(mesh=self._pymesh, name=self.name,
                                    thickness=self.thickness,
                                    subdivide=self.subdivide)
        elif use_triangle and not from_external_loading:
            self.generate_triangulation_from_shapely_linestring(self.line)
            super().__init__(cells=self.cells, points=self.cell_points, name=self.name,
                                    thickness=self.thickness,
                                    subdivide=self.subdivide)
        else:
            super().__init__(cells=self.cells, points=self.cell_points,
                                    name=self.name,
                                    thickness=self.thickness,
                                    subdivide=self.subdivide)
    
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
    
    def generate_polygon_from_shapely_linestring(self, poly):
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
    
    def generate_shapely_polygon_from_points(self, points):
        return geometry.Polygon(points[0], holes=points[1])
        
    def generate_triangulation_from_point_list(self, points):
        xy=points[0]
        self._to_triangle_vertices=xy
        self._to_triangle_segments=[(len(xy)-1,0)]+\
                        [(i,i+1) for i in range(len(xy)-1)]
        if len(points[1])==0:
            t=triangle.triangulate({'vertices': self._to_triangle_vertices,
                        'segments': self._to_triangle_segments},
                       opts="p")
            if self.refine is not None:
                t=triangle.triangulate(t, opts="pra{:}".format(self.refine))
            self.cell_points, self.cells = ([p+[0.] for p in t['vertices'].tolist()],
                                       [("triangle", t['triangles'].tolist())])
        else:
            print('we have a fucking hole')
            holes=[]
            for hole in points[1]:
                holes.append(hole.pop(-1))
                N=len(self._to_triangle_vertices)
                self._to_triangle_segments+=[(N+len(hole)+-1,N)]+\
                        [(N+i,N+i+1) for i in range(len(hole)-1)]
                self._to_triangle_vertices+=hole
                
            t=triangle.triangulate({'vertices': self._to_triangle_vertices,
                            'segments': self._to_triangle_segments,
                            'holes':holes},
                           opts="p")
            self.cell_points, self.cells = ([p+[0.] for p in t['vertices'].tolist()],
                                       [("triangle", t['triangles'].tolist())])
            
    def generate_triangulation_from_shapely_linestring(self, poly):
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
            if self.refine is not None:
                t=triangle.triangulate(t, opts="pra{:}".format(self.refine))
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
    
    
            
    
class Path(PlaneGeom):

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
        self.generate_polygon_from_shapely_linestring(self.line)
        
class Arrow(PlaneGeom):
    
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
        self.poly=self.generate_polygon_from_shapely_linestring(self.line)
        self.head=self.geom.add_polygon([(self.length,-self.head_width/2,0),
                                         (self.length+self.head_length,0,0),
                                         (self.length,self.head_width/2,0)])
        self.arrow=self.geom.boolean_union([self.poly, self.head])
    
class Polygon(PlaneGeom):
    
    def __init__(self, points,
                 **kwargs):
        super().__init__(**kwargs)
        self.points=points
        self.generate()
    
    def generate(self):
        self.line=geometry.LineString(self.points)
        self.xy=self.format_line(self.line)
        self.geom.add_polygon(self.xy)

class Cylinder(PlaneGeom):
    
    def __init__(self, name='Cylinder', radius=1, height=1,
                 **kwargs):
        self.line=geometry.Point(0,0).buffer(radius).exterior
        super().__init__(name=name, thickness=height, **kwargs)
        self.send_to_blender(use_triangle=True)

class Box(PlaneGeom):
    
    def __init__(self, name='Box', Lx=1, Ly=1, Lz=1, **kwargs):
        self.line=geometry.box(-Lx/2,-Ly/2,Lx/2, Ly/2).exterior
        super().__init__(name=name, thickness=Lz, **kwargs)
        self.send_to_blender(use_triangle=True)

        
if __name__=='__main__':
        
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
    #curve=Curve([(theta,0.5*np.sin(theta)*np.sin(30*theta),0) for theta in np.linspace(0, 10*np.pi, 3000)], name='hello')
    
    antenna.send_to_blender(use_triangle=True)
    #curve.location=list(antenna.points[-1])+[0.]
    #arrow.follow_path(curve_2)
    arrow.curve_modifier(curve_2)
    '''c=Cylinder(height=arrow.length,
               subdivide=10,
               radius=arrow.width)
    c.send_to_blender(use_triangle=True)
    c.rotation=[0,np.pi/2,0]
    c.curve_modifier(curve_2)
    c.copy_location(arrow)'''
    metal=Material('imported', '#6B5252')
    metal.load_image_shader_dir(r'C:\Users\Thibault\Downloads\Concrete003_1K-JPG')
    glow=Material("glow", '#D70A0A')
    emission=glow.add_shader('Emission')
    emission.inputs['Strength']=40.
    glow.get_shader('Material Output').inputs['Surface']=emission.outputs['Emission']
    arrow.assign_material(glow)
    arrow.location=[0.,0.,0.2]
    antenna.assign_material(metal)
    light=Light(light_type='SUN', power=2, radius=3, location=[1,0,4])
    plane=Plane(size=100, location=[0., 0., -0.1])
    
    #%%
    from sending_data import (Material)
    
    glow=Material("glow", '#D70A0A')
    coordinates=glow.add_shader('Texture_coordinates')
    separate=glow.add_shader('Separate_XYZ')
    separate.inputs['Vector']=coordinates.outputs['Generated']
    special_keys=dict({'X':separate.outputs['X'], 'Y':separate.outputs['Y']})
    math_shader=glow.coordinate_expression('4e^(-(X^2+Y^2)/(0.1)^2)',
                                      special_keys=special_keys)
    emission=glow.add_shader('Emission')
    emission.inputs['Strength']=math_shader.outputs['Value']
    add_shader=glow.add_shader('Add')
    add_shader.inputs[0]=glow.get_shader('Principled BSDF').outputs['BSDF']
    add_shader.inputs[1]=emission.outputs['Emission']
    s=glow.get_shader('Material Output')
    s.inputs['Surface']=add_shader.outputs['Shader']
    #%%
    import meshio
    from sending_data import Mesh
    mesh=Mesh(mesh=meshio.read(r'Y:\membrane\Equipment\Homebuilt\Machined parts\Microwave_cavity_push_project\coupling_from_below\bottom.STL'),
              name='bottom')
