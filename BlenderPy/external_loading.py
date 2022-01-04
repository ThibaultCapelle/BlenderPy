# -*- coding: utf-8 -*-
"""
Created on Sun Dec 26 15:54:46 2021

@author: Thibault
"""

import pya
import numpy as np
import struct
from BlenderPy.meshing import Plane_Geom
from BlenderPy.sending_data import Mesh

class VTULoader:
    
    def __init__(self, filename, **kwargs):
        self.kwargs=kwargs
        self.filename=filename
        with open(filename, 'r') as f:
            lines=f.readlines()
        reading_points=False
        reading_cells=False
        reading_data=False
        self.data, self.points, self.cells= [], [], []
        for line in lines:
            if line.startswith('<'):
                if line.startswith('<PointData>'):
                    reading_data=True
                elif line.startswith('</PointData>'):
                    reading_data=False
                if line.startswith('<Points>'):
                    reading_points=True
                elif line.startswith('</Points>'):
                    reading_points=False
                if line.startswith('<Cells>'):
                    reading_cells=True
                elif line.startswith('</DataArray>'):
                    reading_cells=False
            else:
                if reading_data:
                    self.data.append(float(line))
                if reading_points:
                    self.points.append([float(x) for x in line.split(' ')])
                if reading_cells:
                    self.cells.append([int(p) for p in line.split(' ')])
        for i in range(len(self.data)):
            self.points[i][2]=self.data[i]
            
    def load(self):
        return Mesh(mesh=None, cells=[['triangle',self.cells]],
                    points=list(self.points), **self.kwargs) 

class STLLoader:
    
    def __init__(self, filename, **kwargs):
        self.kwargs=kwargs
        self.filename=filename
        with open(self.filename, 'rb') as f:
            self.header=f.read(80).decode()
            self.N_triangles=struct.unpack('I', f.read(4))[0]
            vectors, Ps_s, attrs=[], [], []
            for i in range(self.N_triangles):
                vector=list(struct.unpack('fff', f.read(12)))
                for j in range(3):
                    Ps_s.append(f.read(12))
                attr=struct.unpack('H', f.read(2))[0]
                vectors.append(vector)
                attrs.append(attr)
        dict_points=dict()
        current_index=0
        self.cells=[]
        for i in range(self.N_triangles):
            for j in range(3):
                P=Ps_s[i*3+j]
                if P not in dict_points.keys():
                    dict_points[P]=current_index
                    current_index+=1
            self.cells.append([dict_points[Ps_s[3*i+j]] for j in range(3)])
        self.new_dict_points={v:struct.unpack('fff',k) for k, v in dict_points.items()}
    
    def load(self):
        return Mesh(mesh=None, cells=[['triangle',self.cells]],
          points=list(self.new_dict_points.values()), **self.kwargs) 


class GDSLoader:
    
    def __init__(self, filename=None, xmin=None, 
                 xmax=None, ymin=None,
                 ymax=None, layer=None, scaling=1e-3,
                 cell_name='TOP', centering=[0.,0.,0.],
                 merged=True, **kwargs):
        self.scaling=scaling
        self.filename=filename
        self.centering=centering
        self.layout=pya.Layout()
        self.layout.read(self.filename)
        dbu=self.layout.dbu
        cell = self.layout.cell(self.layout.cell_by_name(cell_name))
        for i, layer_info in enumerate(self.layout.layer_infos()):
            if layer_info.layer==layer:
                layer_ind=i
                break
        shapes=cell.shapes(layer_ind)
        shapes_inside_box=[]
        for s in shapes.each():
            bbox=s.bbox()
            if bbox.left>xmin/dbu and bbox.right<xmax/dbu and bbox.top<ymax/dbu and bbox.bottom>ymin/dbu:
                shapes_inside_box.append(s)
        reg=pya.Region([b.polygon for b in shapes_inside_box])
        x_center, y_center=(0.5*(reg.bbox().left+reg.bbox().right),
                            0.5*(reg.bbox().top+reg.bbox().bottom))
        
        if centering is None:
            dx, dy, dz=0.,0.,0.
        else:
            dx, dy, dz=(centering[0]/dbu-x_center,
                        centering[1]/dbu-y_center,
                        centering[2]/dbu)
        res=[]
        if merged:
            iterator=reg.each_merged()
        else:
            iterator=reg.each()
        for s in iterator:
            shape=[[],[]]
            for p in s.each_point_hull():
                shape[0].append([(p.x+dx)*dbu*self.scaling,
                                 (p.y+dy)*dbu*self.scaling,
                                 dz*dbu])
            holes=[[] for i in range(s.holes())]
            for i in range(s.holes()):
                for p in s.each_point_hole(i):
                    holes[i].append([p.x*dbu*self.scaling,
                                     p.y*dbu*self.scaling,
                                     0.])
            shape[1]=holes
            res.append(shape)
        self.polygons=res    
        self.kwargs=kwargs
        
    def polygon_area(self, xs, ys):
        """https://en.wikipedia.org/wiki/Centroid#Of_a_polygon"""
        # https://stackoverflow.com/a/30408825/7128154
        return 0.5 * (np.dot(xs, np.roll(ys, 1)) - np.dot(ys, np.roll(xs, 1)))

    def polygon_centroid(self, points):
        """https://en.wikipedia.org/wiki/Centroid#Of_a_polygon"""
        xs, ys=[p[0] for p in points], [p[1] for p in points]
        xy = np.array([xs, ys])
        c = np.dot(xy + np.roll(xy, 1, axis=1),
                   xs * np.roll(ys, 1) - np.roll(xs, 1) * ys
                   ) / (6 * self.polygon_area(xs, ys))
        return c
        
    def load(self):
        res=[]
        for shape in self.polygons:
            plane_geom=Plane_Geom(**self.kwargs)
            plane_geom.generate_triangulation_from_shapely_LineString\
            (plane_geom.generate_shapely_polygon_from_points(shape))
            plane_geom.send_to_blender(from_external_loading=True)
            '''plane_geom.generate_triangulation_from_point_list(shape)
            plane_geom.send_to_blender(from_external_loading=True)'''
            res.append(plane_geom)
            #time.sleep(0.2)
        return res

if __name__=='__main__':
    from BlenderPy.meshing import Box
    from BlenderPy.sending_data import delete_all
    import numpy as np
    delete_all()
    loader=GDSLoader(filename=r'C:\Users\Thibault\Documents\postdoc\Masks\trenches.gds',
                     layer=3,xmin=-1000, xmax=3500,
                     ymin=-2000, ymax=2000,
                     cell_name='TOP', thickness=0.15)
    trenches=loader.load()
    silicon=Box(Lx=10, Ly=10, Lz=0.1)
    for trench in trenches:
        trench.z-=0.025
        silicon.subtract(trench)
    loader=GDSLoader(filename=r'C:\Users\Thibault\Documents\postdoc\Masks\trenches.gds',
                     layer=9,xmin=-1000, xmax=3500,
                     ymin=-2000, ymax=2000,
                     cell_name='TOP', thickness=0.1)
    recesses=loader.load()
    for recess in recesses:
        recess.zmin=silicon.zmax
    loader=GDSLoader(filename=r'C:\Users\Thibault\Documents\postdoc\Masks\trenches.gds',
                     layer=8,xmin=-1000, xmax=3500,
                     ymin=-2000, ymax=2000,
                     cell_name='TOP', thickness=0.02)
    circuits=loader.load()
    for circuit in circuits:
        circuit.zmin=recess.zmax
    '''verts=silicon.vertices
    xmin, xmax, ymin, ymax=(np.min([trench.xmin for trench in trenches]),
                            np.max([trench.xmax for trench in trenches]),
                            np.min([trench.ymin for trench in trenches]),
                            np.max([trench.ymax for trench in trenches]))
                            
    for i, p in enumerate(verts):
        if p[0]<xmax and p[0]>xmin and p[1]>ymin and p[1]<ymax:
            verts[i][2]+=xmax-p[0]
    silicon.vertices=verts'''

        