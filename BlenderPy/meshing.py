# -*- coding: utf-8 -*-
"""
Created on Wed Oct 20 10:50:42 2021

@author: Thibault
"""

from shapely import geometry
import triangle
import numpy as np
from BlenderPy.sending_data import (Mesh, GeometricEntity)
from abc import abstractmethod

class Vector:
    '''Class representing a Vector, of 2 or 3 dimensions.'''
    
    def __init__(self, *args):
        '''
        Parameters:
            args: the coordinates. Can be x,y,z, or x,y or (x,y), or [x,y],
            or np.array([x,y]), or x+i*y, or (x1,y1), (x2,y2), 
            which in that last case would give a vector (x2-x1, y2-y1)
        '''
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
        '''return the norm of the vector'''
        return np.sqrt(self.x**2+self.y**2+self.z**2)
    
    def normalize(self):
        '''return this vector divided by his norm'''
        return self/self.norm()
    
    def compl(self):
        '''return x+i*y'''
        return self.x+1j*self.y
    
    def cross3(self, other):
        '''return the 3d cross product of this Vector with the Vector other'''
        assert isinstance(other, Vector)
        return Vector(self.y*other.z-self.z*other.y,
                      self.z*other.x-self.x*other.z,
                      self.x*other.y-self.y*other.x)
    
    def cross(self, other):
        '''return the 2d cross product of this Vector with the Vector other'''
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
    '''class representing a Transformation for a Polygon. Only one method,
    which is update'''
    def __init__(self):
        pass
    
    @abstractmethod
    def update(self, points):
        '''apply the transformation'''
        pass

class Mirror(Transformation):
    '''a Mirror transformation along an axis'''
    
    def __init__(self, point, ax):
        '''
        Parameters:
            point: a point on the mirror axis. Should be compatible with Vector
            initializer
            ax: the direction of the mirror axis. should be a list
        '''
        assert isinstance(ax, list)
        self.point=Vector(point)
        self.ax=Vector(ax)
        self.up=Vector(0,0,1)
        self.norm=self.up.cross3(self.ax)
    
    def update(self, points):
        '''return the mirrored points'''
        
        for i, point in enumerate(points):
            p=Vector(point)
            p0=self.point
            res=p0+((p-p0)*self.ax)*self.ax-((p-p0)*self.norm)*self.norm
            points[i]=res
        return points
    
class MultiPolygon():
    '''
    Class representing a list of Polygons
    '''
    
    def __init__(self, polygons=[]):
        '''
        Parameters:
            polygons: a list of Polygon
        '''
        self.polygons=polygons
    
    def translate(self, val):
        '''
        Apply a translation of amount val to all the Polygons
        
        Parameters:
            val: the translation value. See Polygon.translate
        '''
        for p in self.polygons:
            p.translate(val)
    
    def append(self, val):
        '''
        Add a Polygon
        
        Parameters:
            val: Polygon to add
        '''
        if isinstance(val, Polygon):
            self.polygons.append(val)
        elif isinstance(val, MultiPolygon):
            for p in val.polygons:
                self.polygons.append(p)
    
    def to_shapely(self):
        '''
        convert to shapely MultiPolygon
        '''
        return geometry.MultiPolygon(polygons=[p.to_shapely()
                                               for p in self.polygons])
    
    def from_shapely(self, poly):
        '''
        Load a Shapely MultiPolygon
        
        Parameters:
            poly: the shapely MultiPolygon to load
        '''
        
        self.polygons=[]
        for p in list(poly):
            polygon=Polygon()
            polygon.from_shapely(p)
            self.polygons.append(polygon)
    
    @property
    def left(self):
        '''The minimum x value of all the Polygons as a group
        '''
        return np.min([p.left for p in self.polygons])
    
    @left.setter
    def left(self, val):
        self.translate([val-self.left,
                        0.])
    
    @property
    def right(self):
        '''The maximum x value of all the Polygons as a group
        '''
        return np.max([p.right for p in self.polygons])
    
    @right.setter
    def right(self, val):
        self.translate([val-self.right,
                        0.])
    
    @property
    def bottom(self):
        '''The minimum y value of all the Polygons as a group
        '''
        return np.min([p.bottom for p in self.polygons])
    
    @bottom.setter
    def bottom(self, val):
        self.translate([0.,
                        val-self.bottom])
    
    @property
    def top(self):
        '''The maximum x value of all the Polygons as a group
        '''
        return np.max([p.top for p in self.polygons])
    
    @top.setter
    def top(self, val):
        self.translate([0.,
                        val-self.top])
    
    @property
    def center(self):
        '''The center of all the Polygons as a group
        '''
        return [0.5*(self.left+self.right),
                0.5*(self.bottom+self.top)]
        
    @center.setter
    def center(self, val):
        previous_center=self.center
        self.translate([val[0]-previous_center[0],
                        val[1]-previous_center[1]])
    
    @property
    def width(self):
        '''The width of all the Polygons as a group
        '''
        return self.right-self.left
    
    @property
    def height(self):
        '''The height of all the Polygons as a group
        '''
        return self.top-self.bottom



class Polygon():
    ''' 
    Class representing a 2D Polygon
    '''
    
    def __init__(self, points=[], holes=[]):
        '''
        Parameters:
            points: a list of 2D points representing the exterior of the Polygon
            holes: a list of lists of 2D points. Each list represents a hole
        '''
        self.points=points
        self.holes=holes
    
    def to_shapely(self):
        '''convert to shapely.geometry.Polygon
        
        Parameters:
            None
            
        Returns:
            the shapely.geometry.Polygon representing this Polygon
        '''
        return geometry.Polygon(self.points, holes=self.holes)
    
    def from_shapely(self, poly):
        '''Load a shapely.geometry.Polygon
        
        Parameters:
            poly: the shapely.geometry.Polygon to load
        
        Returns:
            None
        '''
        self.points, self.holes=self._polygon_to_points(poly)
    
    def subtract(self, other):
        '''Performs a boolean subtraction between this Polygon and another
        
        Parameters:
            other: a Polygon or a MultiPolygon to subtract
        
        Returns:
            a Polygon or a MultiPolygon, resulting from the subtraction
        '''
        if isinstance(other, Polygon) or isinstance(other, MultiPolygon):
            diff=self.to_shapely().difference(other.to_shapely())
        if isinstance(diff, geometry.multipolygon.MultiPolygon):
            res=MultiPolygon()
            res.from_shapely(diff)
            return res
        elif isinstance(diff, geometry.polygon.Polygon):
            self.from_shapely(diff)
            return self
    
    def intersect(self, other):
        '''Performs a boolean intersection between this Polygon and another
        
        Parameters:
            other: a Polygon or a MultiPolygon to subtract
        
        Returns:
            a Polygon, resulting from the intersection
        '''
        if isinstance(other, Polygon):
            inter=self.to_shapely().intersection(other.to_shapely())
            self.from_shapely(inter)
        elif isinstance(other, MultiPolygon):
            inter=self.to_shapely()
            for poly in other.polygons:
                inter=inter.difference(poly.to_shapely())
            self.from_shapely(inter)
    
    def duplicate(self):
        '''duplicate the Polygon
        
        Parameters:
            None
            
        Return:
            The duplicated Polygon
        '''
        return Polygon(points=self.points.copy(),
                       holes=self.holes.copy())
        
    def _xy_to_points(self, line):
        xs, ys=(np.array(line.xy[0]),
                np.array(line.xy[1]))
        return [[x,y] for x,y in zip(xs, ys)]
    
    def _polygon_to_points(self, polygon):
        points_ext=self._xy_to_points(polygon.exterior)
        points_int=[]
        for i, interior in enumerate(polygon.interiors):
            points_int.append(self._xy_to_points(interior))
        return points_ext, points_int

    
    def translate(self, vect):
        '''Translate the Polygon
        
        Parameters:
            vect: a list or tuple representing the displacement in 2D
        
        Returns:
            None
        '''
        for i, p in enumerate(self.points):
            self.points[i]=[p[0]+vect[0],
                            p[1]+vect[1]]
        for i, hole in enumerate(self.holes):
            for j, p in enumerate(hole):
                self.holes[i][j]=[p[0]+vect[0],
                                  p[1]+vect[1]]
    
    def mirror(self, point, ax):
        '''Mirror the Polygon
        
        Parameters:
            point, ax: see Mirror
        
        Returns:
            self, after mirroring
        '''
        mir=Mirror(point, ax)
        self.points=[[p.x, p.y] for p in mir.update(self.points)]
        return self
            
    @property
    def left(self):
        '''The minimum x value of the Polygon
        '''
        return np.min([p[0] for p in self.points])
    
    @left.setter
    def left(self, val):
        self.translate([val-self.left,
                        0.])
    
    @property
    def right(self):
        '''The maximum x value of the Polygon
        '''
        return np.max([p[0] for p in self.points])
    
    @right.setter
    def right(self, val):
        self.translate([val-self.right,
                        0.])
    
    @property
    def bottom(self):
        '''The minimum y value of the Polygon
        '''
        return np.min([p[1] for p in self.points])
    
    @bottom.setter
    def bottom(self, val):
        self.translate([0.,
                        val-self.bottom])
    
    @property
    def top(self):
        '''The maximum y value of the Polygon
        '''
        return np.max([p[1] for p in self.points])
    
    @top.setter
    def top(self, val):
        self.translate([0.,
                        val-self.top])
    
    @property
    def center(self):
        '''The center of the Polygon
        '''
        return [0.5*(self.left+self.right),
                0.5*(self.bottom+self.top)]
        
    @center.setter
    def center(self, val):
        previous_center=self.center
        self.translate([val[0]-previous_center[0],
                        val[1]-previous_center[1]])
    
    @property
    def width(self):
        '''The width (xmax-xmin) value of the Polygon
        '''
        return self.right-self.left
    
    @property
    def height(self):
        '''The height (ymax-ymin) value of the Polygon
        '''
        return self.top-self.bottom
    
class Circle(Polygon):
    '''2D Circle
    '''
    
    def __init__(self, x0=0, y0=0, radius=1., N=32):
        '''
        Parameters:
            x0, y0: the center of the circle
            radius: the radius of the circle
            N: the number of points
        '''
        points=[[x0+radius*np.cos(theta),
                 y0+radius*np.sin(theta)] 
                 for theta in np.linspace(0, 2*np.pi, N)]
        super().__init__(points=points)

class AngularSector(Polygon):
    '''Angular section of a circle '''
    
    def __init__(self, x0=0, y0=0, radius=1., N=32,
                 theta_1=0, theta_2=np.pi/2):
        '''
        Parameters:
            x0, y0: the center of the circle
            radius: the radius of the circle
            N: the number of points
            theta_1: the starting angle of the sector
            theta_2: the end angle of the sector
        '''
        points=[[x0+radius*np.cos(theta),
                 y0+radius*np.sin(theta)] 
                 for theta in np.linspace(theta_1, theta_2, N)]+[[0.,0.]]
        super().__init__(points=points)

class RoundCorner(Polygon):
    '''Rounded path, i.e. AnularSector define by R>radius-width/2 and 
    R<radius+width/2
    '''
    
    def __init__(self, x0=0, y0=0, radius=1., N=32,
                 theta_1=0, theta_2=np.pi/2, width=0.1):
        '''
        Parameters:
            x0, y0: the center of the circle
            radius: the radius of the circle
            N: the number of points
            theta_1: the starting angle of the sector
            theta_2: the end angle of the sector
            width: the width of the path
        '''
        points=[[x0+(radius+width/2)*np.cos(theta),
                 y0+(radius+width/2)*np.sin(theta)] 
                 for theta in np.linspace(theta_1, theta_2, N)]
        points+=[[x0+(radius-width/2)*np.cos(theta),
                 y0+(radius-width/2)*np.sin(theta)] 
                 for theta in np.linspace(theta_2, theta_1, N)]
        super().__init__(points=points)
        
class Rectangle(Polygon):
    '''A Rectangle (2D)'''
    
    def __init__(self, x0=0, y0=0, Lx=1, Ly=1):
        '''
        Parameters:
            x0, y0: the center of the Rectangle
            Lx, Ly: the width and height of the Rectangle
        '''
        points=[[x0-Lx/2, x0-Ly/2],
                [x0-Lx/2, x0+Ly/2],
                [x0+Lx/2, x0+Ly/2],
                [x0+Lx/2, x0-Ly/2]]
        super().__init__(points=points)

class Triangle:
    '''A Class for having the 2D triangulation, with the triangle library
    method isolated
    '''
    
    @staticmethod
    def triangulate(points, holes):
        '''static method for trangulating a group of 2D points with holes.
        
        Parameters:
            points: a list of 2D vertices representing the exterior of the 
            Polygon
            holes: a list of lists of 2D vertices representing for each list 
            a hole in the Polygon
        '''
        
        _to_triangle_vertices=points
        _to_triangle_segments=[(len(points)-1,0)]+\
                        [(i,i+1) for i in range(len(points)-1)]
        if len(holes)==0:
            tri=triangle.triangulate(dict({'vertices':_to_triangle_vertices,
                                           'segments':_to_triangle_segments}),
                                            'pqPz')
        else:
            holes_point=[]
            for hole in holes:
                holes_point.append([np.mean([p[0] for p in hole]),
                              np.mean([p[1] for p in hole])])
                N=len(_to_triangle_vertices)
                _to_triangle_segments+=[(N+len(hole)+-1,N)]+\
                        [(N+i,N+i+1) for i in range(len(hole)-1)]
                _to_triangle_vertices+=hole
            tri=triangle.triangulate(dict({'vertices':_to_triangle_vertices,
                                           'segments':_to_triangle_segments,
                                           'holes':holes_point}),
                                            'pqPz')
        return ([p+[0.] for p in tri['vertices'].tolist()],
                tri['triangles'].tolist())
    
class PlaneGeom(Mesh, GeometricEntity):
    '''class representing an eventually extruded 2D geometry'''
    
    def __init__(self, polygon=None, name='', 
                 refine=None, **kwargs):
        '''
        Parameters:
            polygon: eventually a Polygon to send to Blender
            name: the desired name
            refine: number of time to refine the mesh triangulation before 
            sending it to Blender
            kwargs: Mesh keyword arguments
        '''    
        
                
        self._refine=refine
        self.name=name
        self.kwargs=kwargs
        if polygon is not None:
            if isinstance(polygon, Polygon):
                if len(polygon.holes)==0:
                    self.cell_points=[[p[0], p[1], 0.] for p in polygon.points]
                    self.cells=[[i for i, p in enumerate(polygon.points)]]
                    self._send_to_blender(from_external_loading=True)
                else:
                    self.cell_points, self.cells = Triangle.triangulate(polygon.points,
                                                                 polygon.holes)
                    self._send_to_blender(from_external_loading=True)
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
                        res=Triangle.triangulate(poly.points, poly.holes)
                        points, cells=res
                        self.cell_points+=points
                        for cell in cells:
                            self.cells.append([offset+p for
                                               p in cell])
                    offset=len(self.cell_points)
                self._send_to_blender(from_external_loading=True)
                        
                            
    def _send_to_blender(self, use_triangle=False, from_external_loading=False):
        if use_triangle:
            self._generate_triangulation_from_shapely_linestring(self.line)
        super().__init__(cells=self.cells, points=self.cell_points,
                                 name=self.name,
                                **self.kwargs)
        
    def _format_line(self, line):
        x_s, y_s=line.xy
        res = [(x,y,0) for x,y in zip(x_s, y_s)]
        if res[-1]==res[0]:
            res=res[:-1]
        return res

    def _generate_triangulation_from_shapely_linestring(self, poly):
        if hasattr(poly, 'exterior'):
            self.xy=self._format_line(poly.exterior, gmsh=False)
        else:
            self.xy=self._format_line(poly, gmsh=False)
        self.holes=[]
        xy=[[p[0], p[1]] for p in self.xy]
        self._to_triangle_vertices=xy
        self._to_triangle_segments=[(len(xy)-1,0)]+\
                        [(i,i+1) for i in range(len(xy)-1)]
        if not hasattr(poly, 'interiors') or  hasattr(poly, 'interiors') and len(poly.interiors)==0:
            t=triangle.triangulate({'vertices': self._to_triangle_vertices,
                        'segments': self._to_triangle_segments},
                       opts="p")
            if self._refine is not None:
                t=triangle.triangulate(t, opts="pra{:}".format(self._refine))
            self.cell_points, self.cells = ([p+[0.] for p in t['vertices'].tolist()],
                                       [("triangle", t['triangles'].tolist())])
        else:
            holes=[]
            for interior in poly.interiors:
                xy=self._format_line(interior, gmsh=False)
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
    '''extruded Path'''
    
    def __init__(self, points, width, cap_style='flat',
                 join_style='round', resolution=16,
                 **kwargs):
        '''
        Parameters:
            points: the 2D points of the Path, should be a list
            width: the width of the Path
            cap_style, join_style, resolution: Shapely options, see shapely 
            manual for Path
            kwargs: PlaneGeom keyword arguments
        '''
        
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
        self._generate()
        self._send_to_blender(use_triangle=True)
    
    def _generate(self):
        self.line=geometry.LineString(self.points).buffer(self.width/2.,
                                cap_style=self.cap_style,
                                join_style=self.join_style,
                                resolution=self.resolution)
        self.generate_polygon_from_shapely_linestring(self.line)
        
class Arrow(PlaneGeom):
    '''Extruded Arrow'''
    
    def __init__(self, head_width=0.1, head_length=0.2,
                 length=1, width=0.05, **kwargs):
        '''
        Parameters:
            head_width: width of the head of the arrow
            head_length: length of the head of the arrow
            length: length of the arrow
            width: width of the arrow
            kwargs: PlaneGeom keyword arguments
        '''
        
        super().__init__(**kwargs)
        self.head_width=head_width
        self.head_length=head_length
        self.length=length
        self.width=width
        self.cell_points=[[-width/2, -length, 0.],
                          [width/2, -length, 0.],
                          [width/2, 0., 0.],
                          [head_width/2, 0., 0.],
                          [0., head_length, 0.],
                          [-head_width/2, 0., 0.],
                          [-width/2, 0., 0.]]
        self.cells=[[i for i,p in enumerate(self.cell_points)]]
        super().__init__(**kwargs)
        self._send_to_blender(from_external_loading=True)

class Cylinder(PlaneGeom):

    def __init__(self, name='Cylinder', radius=1, height=1,
                 N_points=32, **kwargs):
        '''
        Parameters:
            name: desired name
            radius: radius of the Cylinder
            height: height of the cylinder
            N_points: number of points in the cylinder
            kwargs: PlaneGeom keyword arguments
        '''
        
        self.cell_points=[[radius*np.cos(theta), radius*np.sin(theta), -height/2] 
                        for theta in np.linspace(0, 2*np.pi, N_points)]
        self.cells=[[i for i in range(N_points)]]
        super().__init__(name=name, thickness=height, **kwargs)
        self._send_to_blender(from_external_loading=True)

class Box(PlaneGeom):
    
    def __init__(self, name='Box', Lx=1, Ly=1, Lz=1, **kwargs):
        '''
        Parameters:
            name: desired name
            Lx, Ly, Lz: x, y, and z extension of the box
        '''
        self.cell_points=[[-Lx/2, -Ly/2, -Lz/2],
                          [-Lx/2, Ly/2, -Lz/2],
                          [Lx/2, Ly/2, -Lz/2],
                          [Lx/2, -Ly/2, -Lz/2]]
        self.cells=[[0, 1, 2, 3]]
        super().__init__(name=name, thickness=Lz, **kwargs)
        self._send_to_blender(from_external_loading=True)
        
class Plane(Box):
    
    def __init__(self, name='plane', size=10, **kwargs):
        '''
        Parameters:
            name: desired name
            Lx, Ly: x and y extension of the plane
        '''
        super().__init__(Lx=size, Ly=size, Lz=0.,
                         name=name, **kwargs)
        
class Sphere(Mesh):
    '''Class representing an isocahedron sphere in 3D'''
    
    def __init__(self, radius=1, refine=0, **kwargs):
        '''
        Parameters:
            radius: radius of the sphere
            refine: number of desired refinements from a 20 faces
            sphere. Each refinement divide each face in four equilateral
            triangles
        '''
        
        self.radius=radius
        self.initialize(self.radius)
        for i in range(refine):
            self._refine()
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
    
    def _refine(self):
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
            self.points.append(self._get_middle_point(self.points[v[0]],
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

    def _get_middle_point(self, p1, p2):
        middle=0.5*(Vector(p1)+Vector(p2))
        middle=middle.normalize()*self.radius
        return [middle.x, middle.y, middle.z]

        
if __name__=='__main__':
    pass