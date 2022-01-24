# -*- coding: utf-8 -*-
"""
Created on Wed Oct 20 10:50:42 2021

@author: Thibault
"""

from shapely import geometry, affinity
import triangle
import pygmsh
import numpy as np
from BlenderPy.sending_data import (Material, Mesh, delete_all,
                          Light, Camera, Curve, Object,
                          ShaderNode, Plane, GeometricEntity)
from abc import abstractmethod
import time
import os
import tempfile
import subprocess

class Vector:
    
    def __init__(self, *args):
        if len(args)==2:
            self.z=0.
            if isinstance(args[0], tuple) and isinstance(args[1], tuple):
                self.x=args[1][0]-args[0][0]
                self.y=args[1][1]-args[0][1]
            else:
                self.x=args[0]
                self.y=args[1]
        elif len(args)==1:
            self.z=0.
            if isinstance(args[0], tuple):
                self.x=args[0][0]
                self.y=args[0][1]
            elif isinstance(args[0], list) or isinstance(args[0], np.ndarray):
                self.x=args[0][0]
                self.y=args[0][1]
                if(len(args[0])==2):
                    self.z=0
                else:
                    self.z=args[0][2]
            elif np.isscalar(args[0]):
                self.x=np.real(args[0])
                self.y=np.imag(args[0])
            else:
                raise TypeError
        elif len(args)==3:
                self.x=args[0]
                self.y=args[1]
                self.z=args[2]
    
    def norm(self):
        return np.sqrt(self.x**2+self.y**2+self.z**2)
    
    def normalize(self):
        return self/self.norm()
    
    def compl(self):
        return self.x+1j*self.y
    
    def cross3(self, other):
        assert isinstance(other, Vector)
        return Vector(self.y*other.z-self.z*other.y,
                      self.z*other.x-self.x*other.z,
                      self.x*other.y-self.y*other.x)
    
    def cross(self, other):
        assert isinstance(other, Vector)
        return self.x*other.y-self.y*other.x
    
    def __add__(self,other):
        if not other.__class__ is Vector:
            print("Erreur: l'argument n'est pas un Vector")
            return NotImplemented
        else:
            return Vector(self.x+other.x, self.y+other.y, self.z+other.z)
        
    def __sub__(self, other):
        return Vector(self.x-other.x, self.y-other.y, self.z-other.z)
    
    def __mul__(self,other):
        if not other.__class__ is Vector:
            return Vector(self.x*other, self.y*other, self.z*other)
        else:
            return self.x*other.x+self.y*other.y
    
    def __rmul__(self, other):
        if not other.__class__ is Vector:
            return Vector(self.x*other, self.y*other, self.z*other)
        else:
            return self.x*other.x+self.y*other.y
    
    def __truediv__(self,other):
        return Vector(self.x/other, self.y/other, self.z/other)
    
    def __str__(self):
        return 'x:{:}, y:{:}, z:{:}'.format(self.x, self.y, self.z)

class Transformation:
    
    def __init__(self):
        pass
    
    @abstractmethod
    def update(self, points):
        pass

class Mirror(Transformation):
    
    def __init__(self, point, ax):
        assert isinstance(ax, list)
        self.point=Vector(point)
        self.ax=Vector(ax)
        self.up=Vector(0,0,1)
        self.norm=self.up.cross3(self.ax)
    
    def update(self, points):
        for i, point in enumerate(points):
            p=Vector(point)
            p0=self.point
            res=p0+((p-p0)*self.ax)*self.ax-((p-p0)*self.norm)*self.norm
            points[i]=res
        return points
    
class MultiPolygon():
    
    def __init__(self, polygons=[]):
        self.polygons=polygons
    
    def translate(self, val):
        for p in self.polygons:
            p.translate(val)
    
    def append(self, val):
        if isinstance(val, Polygon):
            self.polygons.append(val)
        elif isinstance(val, MultiPolygon):
            for p in val.polygons:
                self.polygons.append(p)
    
    def to_shapely(self):
        return geometry.MultiPolygon(polygons=[p.to_shapely()
                                               for p in self.polygons])
    
    def from_shapely(self, poly):
        self.polygons=[]
        for p in poly.geoms:
            polygon=Polygon()
            polygon.from_shapely(p)
            self.polygon.append(polygon)
    
    @property
    def left(self):
        return np.min([p.left for p in self.polygons])
    
    @left.setter
    def left(self, val):
        self.translate([val-self.left,
                        0.])
    
    @property
    def right(self):
        return np.max([p.right for p in self.polygons])
    
    @right.setter
    def right(self, val):
        self.translate([val-self.right,
                        0.])
    
    @property
    def bottom(self):
        return np.min([p.bottom for p in self.polygons])
    
    @bottom.setter
    def bottom(self, val):
        self.translate([0.,
                        val-self.bottom])
    
    @property
    def top(self):
        return np.max([p.top for p in self.polygons])
    
    @top.setter
    def top(self, val):
        self.translate([0.,
                        val-self.top])
    
    @property
    def center(self):
        return [0.5*(self.left+self.right),
                0.5*(self.bottom+self.top)]
        
    @center.setter
    def center(self, val):
        previous_center=self.center
        self.translate([val[0]-previous_center[0],
                        val[1]-previous_center[1]])
    
    @property
    def width(self):
        return self.right-self.left
    
    @property
    def height(self):
        return self.top-self.bottom



class Polygon():
    
    def __init__(self, points=[], holes=[]):
        self.points=points
        self.holes=holes
    
    def to_shapely(self):
        return geometry.Polygon(self.points, holes=self.holes)
    
    def from_shapely(self, poly):
        self.points, self.holes=self.polygon_to_points(poly)
    
    def subtract(self, other):
        if isinstance(other, Polygon) or isinstance(other, MultiPolygon):
            diff=self.to_shapely().difference(other.to_shapely())
        '''elif isinstance(other, MultiPolygon):
            diff=self.to_shapely()
            for poly in other.polygons:
                diff=diff.difference(poly.to_shapely())'''
        if isinstance(diff, geometry.multipolygon.MultiPolygon):
            res=MultiPolygon()
            polys=list(diff)
            for poly in polys:
                p=Polygon()
                p.from_shapely(poly)
                res.polygons.append(p)
            return res
        elif isinstance(diff, geometry.polygon.Polygon):
            self.from_shapely(diff)
            return self
    
    def intersect(self, other):
        if isinstance(other, Polygon):
            inter=self.to_shapely().intersection(other.to_shapely())
            self.from_shapely(inter)
        elif isinstance(other, MultiPolygon):
            inter=self.to_shapely()
            for poly in other.polygons:
                inter=inter.difference(poly.to_shapely())
            self.from_shapely(inter)
    
    def duplicate(self):
        return Polygon(points=self.points.copy(),
                       holes=self.holes.copy())
        
    def xy_to_points(self, line):
        xs, ys=(np.array(line.xy[0]),
                np.array(line.xy[1]))
        return [[x,y] for x,y in zip(xs, ys)]
    
    def polygon_to_points(self, polygon):
        points_ext=self.xy_to_points(polygon.exterior)
        points_int=[]
        for i, interior in enumerate(polygon.interiors):
            points_int.append(self.xy_to_points(interior))
        return points_ext, points_int

    
    def translate(self, vect):
        for i, p in enumerate(self.points):
            self.points[i]=[p[0]+vect[0],
                            p[1]+vect[1]]
        for i, hole in enumerate(self.holes):
            for j, p in enumerate(hole):
                self.holes[i][j]=[p[0]+vect[0],
                                  p[1]+vect[1]]
    
    def mirror(self, point, ax):
        mir=Mirror(point, ax)
        self.points=[[p.x, p.y] for p in mir.update(self.points)]
        return self
    
    def generate_poly_file(self,
                           filename=os.path.join(os.getcwd(), 
                                                 'polygon.poly')):
        self._to_triangle_vertices=self.points
        self._to_triangle_segments=[(len(self.points)-1,0)]+\
                        [(i,i+1) for i in range(len(self.points)-1)]
        if len(self.holes)!=0:
            holes=[]
            for hole in self.holes:
                holes.append([np.mean([p[0] for p in hole]),
                              np.mean([p[1] for p in hole])])
                N=len(self._to_triangle_vertices)
                self._to_triangle_segments+=[(N+len(hole)+-1,N)]+\
                        [(N+i,N+i+1) for i in range(len(hole)-1)]
                self._to_triangle_vertices+=hole
        with open(filename, 'w') as f:
            f.write('{:} 2 0 0\n'.format(len(self._to_triangle_vertices)))
            for i, p in enumerate(self._to_triangle_vertices):
                f.write('{:} {:} {:}\n'.format(i, p[0], p[1]))
            f.write('{:} 0\n'.format(len(self._to_triangle_segments)))
            for i, p in enumerate(self._to_triangle_segments):
                f.write('{:} {:} {:}\n'.format(i, p[0], p[1]))
            f.write('{:}\n'.format(len(holes)))
            for i, p in enumerate(holes):
                f.write('{:} {:} {:}\n'.format(i, p[0], p[1]))
            
    @property
    def left(self):
        return np.min([p[0] for p in self.points])
    
    @left.setter
    def left(self, val):
        self.translate([val-self.left,
                        0.])
    
    @property
    def right(self):
        return np.max([p[0] for p in self.points])
    
    @right.setter
    def right(self, val):
        self.translate([val-self.right,
                        0.])
    
    @property
    def bottom(self):
        return np.min([p[1] for p in self.points])
    
    @bottom.setter
    def bottom(self, val):
        self.translate([0.,
                        val-self.bottom])
    
    @property
    def top(self):
        return np.max([p[1] for p in self.points])
    
    @top.setter
    def top(self, val):
        self.translate([0.,
                        val-self.top])
    
    @property
    def center(self):
        return [0.5*(self.left+self.right),
                0.5*(self.bottom+self.top)]
        
    @center.setter
    def center(self, val):
        previous_center=self.center
        self.translate([val[0]-previous_center[0],
                        val[1]-previous_center[1]])
    
    @property
    def width(self):
        return self.right-self.left
    
    @property
    def height(self):
        return self.top-self.bottom
    
class Circle(Polygon):
    
    def __init__(self, x0=0, y0=0, radius=1., N=32):
        points=[[x0+radius*np.cos(theta),
                 y0+radius*np.sin(theta)] 
                 for theta in np.linspace(0, 2*np.pi, N)]
        super().__init__(points=points)

class AngularSector(Polygon):
    
    def __init__(self, x0=0, y0=0, radius=1., N=32,
                 theta_1=0, theta_2=np.pi/2):
        points=[[x0+radius*np.cos(theta),
                 y0+radius*np.sin(theta)] 
                 for theta in np.linspace(theta_1, theta_2, N)]+[[0.,0.]]
        super().__init__(points=points)

class RoundCorner(Polygon):
    
    def __init__(self, x0=0, y0=0, radius=1., N=32,
                 theta_1=0, theta_2=np.pi/2, width=0.1):
        points=[[x0+(radius+width/2)*np.cos(theta),
                 y0+(radius+width/2)*np.sin(theta)] 
                 for theta in np.linspace(theta_1, theta_2, N)]
        points+=[[x0+(radius-width/2)*np.cos(theta),
                 y0+(radius-width/2)*np.sin(theta)] 
                 for theta in np.linspace(theta_2, theta_1, N)]
        super().__init__(points=points)
        
class Rectangle(Polygon):
    
    def __init__(self, x0=0, y0=0, Lx=1, Ly=1):
        points=[[x0-Lx/2, x0-Ly/2],
                [x0-Lx/2, x0+Ly/2],
                [x0+Lx/2, x0+Ly/2],
                [x0+Lx/2, x0-Ly/2]]
        super().__init__(points=points)

class Triangle:
    
    @staticmethod
    def generate_poly_file(points, holes):
        f=tempfile.mkstemp(suffix = '.poly')
        _to_triangle_vertices=points
        _to_triangle_segments=[(len(points)-1,0)]+\
                        [(i,i+1) for i in range(len(points)-1)]
        if len(holes)!=0:
            holes_point=[]
            for hole in holes:
                holes_point.append([np.mean([p[0] for p in hole]),
                              np.mean([p[1] for p in hole])])
                N=len(_to_triangle_vertices)
                _to_triangle_segments+=[(N+len(hole)+-1,N)]+\
                        [(N+i,N+i+1) for i in range(len(hole)-1)]
                _to_triangle_vertices+=hole
        with open(f[1], 'w') as f:
            f.write('{:} 2 0 0\n'.format(len(_to_triangle_vertices)))
            for i, p in enumerate(_to_triangle_vertices):
                f.write('{:} {:} {:}\n'.format(i, p[0], p[1]))
            f.write('{:} 0\n'.format(len(_to_triangle_segments)))
            for i, p in enumerate(_to_triangle_segments):
                f.write('{:} {:} {:}\n'.format(i, p[0], p[1]))
            f.write('{:}\n'.format(len(holes)))
            for i, p in enumerate(holes_point):
                f.write('{:} {:} {:}\n'.format(i, p[0], p[1]))
        return f.name
    
    @staticmethod
    def use_external_program(file_input):
        program=os.path.join(os.path.dirname(__file__), 'triangle.exe')
        return subprocess.Popen([program, '-pqPz', file_input], shell=True)
    
    @staticmethod
    def triangulate(points, holes):
        filename=Triangle.generate_poly_file(points, holes)
        program=Triangle.use_external_program(filename)
        dirname=os.path.dirname(filename)
        basename=os.path.basename(filename)
        rootname=basename.split('.')[0]
        program.wait()
        program.terminate()
        for file_ele in os.listdir(dirname):
            if file_ele.startswith(rootname) and file_ele.endswith('.ele'):
                file_ele=os.path.join(dirname, file_ele)
                break
        cells=[]
        with open(file_ele, 'r') as f:
            lines=f.readlines()
        for i, line in enumerate(lines):
            if not line.startswith('#') and i!=0:
                cell = [int(k) for k in line.split(' ') if k!='']
                cells.append([cell[1], cell[2], cell[3]])
        for file_node in os.listdir(dirname):
            if file_node.startswith(rootname) and file_node.endswith('.node'):
                file_node=os.path.join(dirname, file_node)
                break
        points=[]
        with open(file_node, 'r') as f:
            lines=f.readlines()
        for i, line in enumerate(lines):
            if not line.startswith('#') and i!=0:
                point = [float(k) for k in line.split(' ') if k!='']
                points.append([point[1], point[2], 0.])
        
        for file in os.listdir(dirname):
            if file.startswith(rootname):
                filename=os.path.join(dirname, file)
                try:
                    os.remove(filename)
                except PermissionError:
                    pass
        return points, cells
        
    
class PlaneGeom(Mesh, GeometricEntity):
    
    def __init__(self, polygon=None, name='', thickness=1,
                 characteristic_length_max=0.03,
                 material=Material('nitrure', '#F5D15B', alpha=0.3, blend_method='BLEND',
                 use_backface_culling=True, blend_method_shadow='NONE'),
                 rounding_decimals=12, subdivide=1, refine=None):
        time.sleep(0.1)
        time.sleep(0.1)
        self.refine=refine
        self.subdivide=subdivide
        self.name=name
        self.thickness=thickness
        self.geom=pygmsh.opencascade.geometry.Geometry(characteristic_length_max=characteristic_length_max)
        self.material=material
        self.rounding_decimals=rounding_decimals
        time.sleep(0.1)
        if polygon is not None:
            if isinstance(polygon, Polygon):
                if len(polygon.holes)==0:
                    self.cell_points=[[p[0], p[1], 0.] for p in polygon.points]
                    self.cells=[[i for i, p in enumerate(polygon.points)]]
                    self.send_to_blender(from_external_loading=True)
                else:
                    time.sleep(0.1)
                    self.cell_points, self.cells = Triangle.triangulate(polygon.points,
                                                                 polygon.holes)
                    time.sleep(0.1)
                    self.send_to_blender(from_external_loading=True)
            elif isinstance(polygon, MultiPolygon):
                self.cell_points, self.cells=[], []
                offset=0
                for poly in polygon.polygons:
                    if len(poly.holes)==0:
                        self.cell_points+=[[p[0],
                                            p[1],
                                            0.] for p in poly.points]
                        self.cells.append([offset+i for
                                           i,p in enumerate(poly.points)])
                    else:
                        '''res = self.generate_triangulation_from_point_list(
                                                             [poly.points,
                                                              poly.holes],
                                                              overwrite=False)'''
                        res=Triangle.triangulate(poly.points, poly.holes)
                        points, cells=res
                        self.cell_points+=points
                        for cell in cells:
                            self.cells.append([offset+p for
                                               p in cell])
                    offset=len(self.cell_points)
                self.send_to_blender(from_external_loading=True)
                        
                            
    def send_to_blender(self, use_triangle=False, from_external_loading=False):
        if not use_triangle and not from_external_loading:
            self._pymesh=pygmsh.generate_mesh(self.geom)
            super().__init__(mesh=self._pymesh, name=self.name,
                                    thickness=self.thickness,
                                    subdivide=self.subdivide,
                                    material=self.material)
        elif use_triangle and not from_external_loading:
            self.generate_triangulation_from_shapely_linestring(self.line)
            super().__init__(cells=self.cells, points=self.cell_points, name=self.name,
                                    thickness=self.thickness,
                                    subdivide=self.subdivide,
                                    material=self.material)
        else:
            super().__init__(cells=self.cells, points=self.cell_points,
                                    name=self.name,
                                    thickness=self.thickness,
                                    subdivide=self.subdivide,
                                    material=self.material)
    
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
        
    def generate_triangulation_from_point_list(self, points, overwrite=True):
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
            if overwrite:
                self.cell_points, self.cells = ([p+[0.] for p in t['vertices'].tolist()],
                                                 [("triangle", t['triangles'].tolist())])
            else:
                return ([p+[0.] for p in t['vertices'].tolist()],
                         [("triangle", t['triangles'].tolist())])
        else:
            time.sleep(0.5)
            holes=[]
            for hole in points[1]:
                holes.append([np.mean([p[0] for p in hole]),
                              np.mean([p[1] for p in hole])])
                N=len(self._to_triangle_vertices)
                self._to_triangle_segments+=[(N+len(hole)+-1,N)]+\
                        [(N+i,N+i+1) for i in range(len(hole)-1)]
                self._to_triangle_vertices+=hole
            time.sleep(0.5)
            t=triangle.triangulate({'vertices': self._to_triangle_vertices,
                            'segments': self._to_triangle_segments,
                            'holes':holes},
                           opts="p")
            if overwrite:
                self.cell_points, self.cells = ([p+[0.] for p in t['vertices'].tolist()],
                                       [("triangle", t['triangles'].tolist())])
            else:
                return ([p+[0.] for p in t['vertices'].tolist()],
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
        self.send_to_blender(use_triangle=True)
    
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
        #self.generate()
        self.cell_points=[[-width/2, -length, 0.],
                          [width/2, -length, 0.],
                          [width/2, 0., 0.],
                          [head_width/2, 0., 0.],
                          [0., head_length, 0.],
                          [-head_width/2, 0., 0.],
                          [-width/2, 0., 0.]]
        self.cells=[[i for i,p in enumerate(self.cell_points)]]
        super().__init__(**kwargs)
        self.send_to_blender(from_external_loading=True)
    
    def generate(self):
        self.line=geometry.LineString([(0,0,0), (self.length,0,0)]).buffer(self.width/2.)
        self.poly=self.generate_polygon_from_shapely_linestring(self.line)
        self.head=self.geom.add_polygon([(self.length,-self.head_width/2,0),
                                         (self.length+self.head_length,0,0),
                                         (self.length,self.head_width/2,0)])
        self.arrow=self.geom.boolean_union([self.poly, self.head])

class Cylinder(PlaneGeom):
    
    def __init__(self, name='Cylinder', radius=1, height=1,
                 N_points=32, **kwargs):
        #self.line=geometry.Point(0,0).buffer(radius).exterior
        self.cell_points=[[radius*np.cos(theta), radius*np.sin(theta), -height/2] 
                        for theta in np.linspace(0, 2*np.pi, N_points)]
        self.cells=[[i for i in range(N_points)]]
        super().__init__(name=name, thickness=height, **kwargs)
        self.send_to_blender(from_external_loading=True)

class Box(PlaneGeom):
    
    def __init__(self, name='Box', Lx=1, Ly=1, Lz=1, **kwargs):
        #self.line=geometry.box(-Lx/2,-Ly/2,Lx/2, Ly/2).exterior
        self.cell_points=[[-Lx/2, -Ly/2, -Lz/2],
                          [-Lx/2, Ly/2, -Lz/2],
                          [Lx/2, Ly/2, -Lz/2],
                          [Lx/2, -Ly/2, -Lz/2]]
        self.cells=[[0, 1, 2, 3]]
        super().__init__(name=name, thickness=Lz, **kwargs)
        self.send_to_blender(from_external_loading=True)

class Isocahedron(Mesh):
    
    def __init__(self, radius=1, refine=0, **kwargs):
        self.radius=radius
        self.initialize(self.radius)
        for i in range(refine):
            self.refine()
        super().__init__(cells=self.cells, 
                         points=self.points,
                         **kwargs)
        
    def initialize(self, radius):
        C0 = (1 + np.sqrt(5)) / 4
        norm = np.sqrt(0.5**2+C0**2)
        self.points=list(radius/norm*np.array([[0.5,  0.0,   C0],
                                        [0.5,  0.0,  -C0],
                                        [-0.5,  0.0,   C0],
                                        [-0.5,  0.0,  -C0],
                                        [C0,  0.5,  0.0],
                                        [C0, -0.5,  0.0],
                                        [-C0,  0.5,  0.0],
                                        [-C0, -0.5,  0.0],
                                        [0.0,   C0,  0.5],
                                        [0.0,   C0, -0.5],
                                        [0.0,  -C0,  0.5],
                                        [0.0,  -C0, -0.5]]))

        self.cells=[[  0,  2, 10 ],
                    [  0, 10,  5 ],
                    [  0,  5,  4 ],
                    [  0,  4,  8 ],
                    [  0,  8,  2 ],
                    [  3,  1, 11 ],
                    [  3, 11,  7 ],
                    [  3,  7,  6 ],
                    [  3,  6,  9 ],
                    [  3,  9,  1 ],
                    [  2,  6,  7 ],
                    [  2,  7, 10 ],
                    [ 10,  7, 11 ],
                    [ 10, 11,  5 ],
                    [  5, 11,  1 ],
                    [  5,  1,  4 ],
                    [  4,  1,  9 ],
                    [  4,  9,  8 ],
                    [  8,  9,  6 ],
                    [  8,  6,  2 ]]
    
    def refine(self):
        edges=dict()
        for i, f in enumerate(self.cells):
            for pair in [[0,1], [1,2], [0,2]]:
                ordered=(np.min([f[pair[0]], f[pair[1]]]),
                         np.max([f[pair[0]], f[pair[1]]]))
                if not ordered in edges.keys():
                    edges[ordered]=[i]
                else:
                    edges[ordered].append(i)

        faces_to_edges=dict()
        for i, f in enumerate(self.cells):
            for pair in [[0,1], [1,2], [0,2]]:
                ordered=(np.min([f[pair[0]], f[pair[1]]]),
                         np.max([f[pair[0]], f[pair[1]]]))
                if not i in faces_to_edges.keys():
                    faces_to_edges[i]=[ordered]
                else:
                    faces_to_edges[i].append(ordered)   
        
        middle_points=dict()
        i=len(self.points)
        for v in edges.keys():
            self.points.append(self.get_middle_point(self.points[v[0]],
                                                     self.points[v[1]]))
            middle_points[v]=i
            i+=1
            
        new_faces=[]
        for f, edges in faces_to_edges.items():
            if edges[0][0] in edges[1]:
                new_faces.append([edges[0][0], middle_points[edges[0]],
                                  middle_points[edges[1]]])
                new_faces.append([edges[0][1], middle_points[edges[0]],
                                  middle_points[edges[2]]])
            else:
                new_faces.append([edges[0][0], middle_points[edges[0]],
                                  middle_points[edges[2]]])
                new_faces.append([edges[0][1], middle_points[edges[0]],
                                  middle_points[edges[1]]])
            for point in self.cells[f]:
                if point not in edges[0]:
                    break
            new_faces.append([point, middle_points[edges[1]],
                              middle_points[edges[2]]])
            new_faces.append([middle_points[edges[0]],
                              middle_points[edges[1]],
                              middle_points[edges[2]]])
        self.cells=new_faces

    def get_middle_point(self, p1, p2):
        middle=0.5*(Vector(p1)+Vector(p2))
        middle=middle.normalize()*self.radius
        return [middle.x, middle.y, middle.z]

        
if __name__=='__main__':
        
    pass