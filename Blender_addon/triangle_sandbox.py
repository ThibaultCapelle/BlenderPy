# -*- coding: utf-8 -*-
"""
Created on Tue Oct 26 15:25:39 2021

@author: Thibault
"""

import triangle, meshio
from shapely import geometry
import numpy as np
points=[(0,0), (0,1), (1,1), (1,0), (0,0)]


width_antenna=0.1
thick_substrate=0.5
W_cell, H_cell = 10000, 7500
width_SMA, length_SMA, width_SMA_bis=1500, 2000,  2000
width_cut=100
width_circuit=120
distance_from_side=300
input_gap=735
W_loop, H_loop=1725,735
edge_loop_distance=200



#points=[(0,0), (0,1), (1,1)]

poly=geometry.LineString(points).buffer(width_antenna/2.)


x_s, y_s=poly.exterior.xy
new_points=[(x,y) for x,y in zip(x_s, y_s)][:-1]
segments_1=[(len(new_points)-1,0)]+\
                        [(i,i+1) for i in range(len(new_points)-1)]

x_s, y_s=poly.interiors[0].xy
interior_points=[(x,y) for x,y in zip(x_s, y_s)][:-1]
segments_2=list(np.array([(len(interior_points)-1,0)]+[(i, i+1) for i in range(len(interior_points))])+len(segments_1))
hole=[p[0] for p in poly.interiors[0].centroid.xy]
points=np.vstack([new_points, interior_points])
segments=np.vstack([segments_1, segments_2])
t=triangle.triangulate({'vertices': points,
                        'segments': segments,
                        'holes':[hole]},
                       opts="p")

points, cells = (t['vertices'].tolist(),
                 [("triangle", t['triangles'].tolist())])
meshio.write_points_cells("foo.vtk", points, cells)
