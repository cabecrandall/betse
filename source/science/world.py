#!/usr/bin/env python3
# Copyright 2015 by Alexis Pietak & Cecil Curry
# See "LICENSE" for further details.

# FIXME add in assertions for various methods
# FIXME redesign for non-equal x and y world dimensions
# FIXME method to create a hexagonal lattice base
# FIXME every once in a while the closed Voronoi cluster is f*c!&ed -- what's wrong with it?
# FIXME figure out how to scale each voronoi polygon to um instead of m dimensions when plotting
# FIXME figure out how to produce plot objects suitable for Qt GUIs...
# FIXME need nx,ny (normal) and tx,ty (tangent) to each cell edge
# FIXME need midpoints (cell_mids, ecm_mids) for line segments of ecm_verts and cell_verts
# FIXME need boundary flags for cell_mids and ecm_verts
# FIXME convex hull outer boundary detection not the best...

"""
The world module contains the class World, which holds
all data structures relating to the size of the environment,
the extent of the cell cluster, and the co-ordinates of cell
centre points.

The initialization method of the World class sets-up
and crops the cell cluster to an optional user-defined geometry input
as a set of points arranged in counter-clockwise order and
defining a closed polygon. Other methods define the cell centres of each
cell polygon, their area, and create nearest neighbour and edge matrices
for each cell.

"""

import numpy as np
import scipy.spatial as sps
from matplotlib.path import Path
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.collections import PolyCollection
import matplotlib.cm as cm


class World(object):
    """
    The WorldSeeds object stores data structures relating to
    the geometric properties of the environmental grid and cell
    centre points.

    Parameters
    ----------
    WorldSeeds requires an instance of NumVars, see the Parameters module.
    Optional: crop_mask (default = None) a set of counter-clockwise
    arranged points defining a closed polygon to clip the cluster of
    cell seed points

    Fields
    -------
    self.x_v        linear numpy vectors as 'tick marks' of x and y
    self.y_v        axes

    self.x_2d       numpy 2d arrays of x or y gridded points
    self.y_2d       (irregular lattice)

    self.xmin, self.xmax      dimensions of world grid (after noise, before cropping)
    self.ymin, self.ymax

    self.centre     [x,y] coordinate of world lattice co-ords (after noise, before cropping)

    self.xypts      numpy array holding [x,y] points of irregular world grid

    self.clust_xy   numpy array of [x,y] points corresponding to only those of
                    the cropped cell cluster

    self.cluster_axis       maximum breadth and centre (as [x,y] point) of cropped cell cluster
    self.cluster_center

    self.ecm_verts     a nested python list containing Voronoi cell regions which specify [x,y] points of region
                        vertices for a clipped Voronoi diagram (arranged to cell index)

    self.cell_area     a list of areas of each Voronoi polygon (arranged to cell index)

    self.cell_centres    a list of [x,y] points defining the cell centre (arranged to cell index)

    self.cell_nn         a nested array of integer indices of each nearest neighbour for a particular cell (arranged
                        to cell index)

    self.bound_flags    a numpy array flagging cells on the envirnomental boundary with 1

    self.cell_edges     a python nested listing of two point line segments of each membrane domain for each cell


    Methods
    -------
    makeSeeds(nx,ny,dc,ac,nl,wsx,wsy)           Create an irregular lattice of seed points in 2d space
    cropSeeds(crop_mask)                        Crop the points cluster to a polygonal shape (circle)
    makeVoronoi(clust_xy, vorclose = None)      Make and clip/close a Voronoi diagram from the seed points
    clip(subjectPolygon, clipPolygon)           The Sutherland-Hodgman polygon clipping algorithm
    area(p)                                     Find the area of a polygon defined by a list of [x,y] points
    vor_area(ecm_verts)                         Returns the area of each polygon in the closed Voronoi diagram
    cell_index(ecm_verts)                       Returns a list of [x,y] points defining the cell centres in order
    near_neigh(cell_centres,search_d,d_cell)    Calculate the nearest neighbour (nn) array for each cell
    cellEdges(reg_verts)                   List of membrane domains as two-point line segments for each cell
    plotPolyData(vor_verts,zdata = None,clrmap = None)  Plot cell polygons with data attached

    Notes
    -------
    Uses Numpy
    Uses Scipy spatial

    """

    def __init__(self,constants,crop_mask=None, vorclose=None, simpleWorld=False):
        d_cell = constants.dc  # diameter of single cell
        nx = constants.nx   # number of lattice sites in world x index
        ny = constants.ny   # number of lattice sites in world y index
        ac = constants.ac  # cell-cell separation
        nl = constants.nl  # noise level for the lattice
        wsx = constants.wsx  # World size
        wsy = constants.wsy # World size
        search_d = constants.search_d  # distance to search for nearest neighbours (relative to d_cell)
        sf = constants.sf              # scale factor to take cell vertices in from extracellular space

        if simpleWorld==False:

            self.makeSeeds(nx,ny,d_cell,ac,nl,wsx,wsy)    # Create the grid for the system (irregular)
            self.cropSeeds(crop_mask)                   # Crop the grid to a geometric shape to define the cell cluster
            self.makeVoronoi(self.clust_xy,vorclose)    # Make, close, and clip the Voronoi diagram
            self.vor_area(self.ecm_verts)              # Calculate the area of each Voronoi polygon (cell)
            self.cell_index(self.ecm_verts)            # Calculate the correct centre and index for each cell
            self.near_neigh(self.cell_centres,search_d,d_cell)    # Calculate the nn array for each cell
            self.boundTag(self.cell_centres)   # flag cells laying on the environmental boundary
            self.cellEdges(self.ecm_verts)    # create a nested list of all membrane domains for each cell
            self.cellVerts(self.cell_centres,self.ecm_verts,sf)   # create individual cell polygon vertices

        elif simpleWorld==True:

            self.makeSeeds(nx,ny,d_cell,ac,nl,wsx,wsy)    # Create the grid for the system (irregular)
            self.cropSeeds(crop_mask)                   # Crop the grid to a geometric shape to define the cell cluster
            self.near_neigh(self.clust_xy,search_d,d_cell)    # Calculate the nn array for each cell
            self.boundTag(self.clust_xy)   # flag cells laying on the environmental boundary


    def makeSeeds(self,nx,ny,dc,ac,nl,wsx,wsy):

        """
        makeSeeds returns an irregular scatter
        of points defined on a world space
        with dimensions wsx, wsy in [m].

        The amount of deviation from a square
        grid is specified by nl, defined from
        0 (perfect square grid) to 1 (full noise).

        Parameters
        ----------
        nx, ny          number of cells in x and y dimensions
        dc              average cell diameter  [m]
        ac              cell-cell separation   [m]
        nl              lattice noise level (0 none to 1 full)
        wsx, wsy        world dimensions in x and y directions

        Creates
        -------
        self.xypts      numpy array listing [x,y] of world seed points

        self.x_2d       numpy 2d arrays of x or y gridded points
        self.y_2d       (irregular lattice)

        self.x_v        linear numpy vectors as 'tick marks' of x and y
        self.y_v        axes

        self.xmin, self.xmax      dimensions of world grid (after noise, before cropping)
        self.ymin, self.ymax

        self.centre     [x,y] coordinate of world centre (after noise, before cropping)

        Notes
        -------
        Uses Numpy arrays

        """

        # first begin with linear vectors which are the "ticks" of the x and y dimensions
        self.x_v = np.linspace(0, (nx - 1) * (dc + ac), nx)  # create lattice vector x
        self.y_v = np.linspace(0, (ny - 1) * (dc + ac), ny)  # create lattice vector y

        # next define a 2d array of lattice points using the x- and y- vectors
        x_2d, y_2d = np.meshgrid(self.x_v, self.y_v)  # create 2D array of lattice points

        # now create a matrix of points that will add a +/- deviation to each point centre
        x_rnd = nl * dc * (np.random.rand(ny, nx) - 0.5)  # create a mix of random deltas x dir
        y_rnd = nl * dc * (np.random.rand(ny, nx) - 0.5)  # create a mix of random deltas x dir

        # add the noise effect to the world point matrices and redefine the results
        self.x_2d = x_2d + x_rnd
        self.y_2d = y_2d + y_rnd

        # define a data structure that holds [x,y] coordinate points of each 2d grid-matrix entry
        self.xypts = np.vstack((self.x_2d.ravel(), self.y_2d.ravel())).T

        # define geometric limits and centre for the cluster of points
        self.xmin = np.min(self.x_2d)
        self.xmax = np.max(self.x_2d)
        self.ymin = np.min(self.y_2d)
        self.ymax = np.max(self.y_2d)

        self.centre = self.xypts.mean(axis=0)

    def cropSeeds(self, crop_mask):

        """
        cropSeeds returns a geometrically
        cropped version of an irregular points scatter in 2D.

        The option crop_mask specifies the type of cropping where
        crop_mask=None gives no cropping and crop_mask='circle' crops
        to a circle with the diameter of the points scatter.

        Parameters
        ----------
        crop_mask          None = no cropping, 'circle'= crop to circle


        Creates
        -------
        self.clust_xy      an array listing [x,y] points of each cell seed
                            in the cropped cluster
        Notes
        -------
        Uses Numpy arrays

        """

        if crop_mask==None:  # if there's no crop-mask specified (default)
            self.clust_xy=self.xypts         # set cluster points to grid points

        elif crop_mask =='circle': # if 'circle' is specified:

            cres = 50  # how many points desired in polygon
            d_circ = self.xmax - self.xmin  # diameter of circle in x-direction  TODO try coding in an ellipse!
            r_circ = d_circ / 2  # radius of circle
            ind1 = np.linspace(0, 1, cres + 1)  # indices of angles defining circle points

            angs = ind1 * 360 * (np.pi / 180)  # angles in radians defining circle points
            circ_ptsx = r_circ * np.cos(angs) + self.centre[0]  # points of the circle
            circ_ptsy = r_circ * np.sin(angs) + self.centre[1]  # points of the circle

            crop_pts = np.vstack((circ_ptsx, circ_ptsy)).T  # reorganize points of the circle as [x,y] pairs

            crop_path = Path(crop_pts, closed=True)  # transform cropping points to a functional path
            # create a boolean matrix mask which is 1 for points inside the circle and 0 for points outside
            ws_mask_xy = crop_path.contains_points(self.xypts)  # create the mask for point inside the path
            ws_mask = ws_mask_xy.reshape(self.x_2d.shape)  # reshape the boolean mask to correspond to the data grid
            self.clust_x2d = np.ma.masked_array(self.x_2d, ~ws_mask)  # created a masked data structure of the x-grid
            self.clust_y2d = np.ma.masked_array(self.y_2d, ~ws_mask)  # create a masked data structure of the y-grid

            # finally, create a data structure of [x,y] points that only contains the points of the cluster

            self.clust_xy = np.array([0,0])  # initialize the x,y points array

            for new_edge in range(0, len(self.y_v)):  # indices to step through grid
                for j in range(0, len(self.x_v)):  # indices to step through grid
                    # if point is not masked (i.e. in the cell cluster)...
                     if self.clust_x2d[new_edge,j] is not np.ma.masked:
                          # get the value of the x,y point by accessing x-grid and y-grid
                            aa=[self.x_2d[new_edge,j],self.y_2d[new_edge, j]]
                           # augment the points list by adding in the new value
                            self.clust_xy = np.vstack((self.clust_xy,aa))

            self.clust_xy = np.delete(self.clust_xy, 0, 0)    # delete the initialization value.

    def makeVoronoi(self, clust_xy, vorclose = None):

        """
        makeVoronoi calculates the Voronoi diagram for an input
        of cell seed points.

        The option vorclose specifies the Voronoi diagram to be clipped (closed)
        to a polygon (circle) corresponding to the seed cluster maximum breadth.
        If vorclose=None, there is no cropping, while vorclose = 'circle' crops
        to a 15 point polygon (circle).

        Parameters
        ----------
        clust_xy            a numpy array listing [x,y] of seed points
        vorclose            None = no cropping, 'circle'= crop to circle

        Returns
        -------
        self.cells          a scipy spatial Voronoi diagram instance
        self.ecm_verts      nested python list specifying polygonal region
                            and vertices as [x,y] for each Voronoi cell in the
                            clipped/closed Voronoi diagram.

        Notes
        -------
        Uses Numpy arrays
        Uses Scipy spatial

        Uses clip(subjectPolygon, clipPolygon) a method defining
        the Sutherland-Hodgman polygon clipping algorithm -- courtesy of Rosetta Code:
        http://rosettacode.org/wiki/Sutherland-Hodgman_polygon_clipping#Python

        """

        vor = sps.Voronoi(clust_xy)

        self.cluster_axis = vor.points.ptp(axis=0)
        self.cluster_center = vor.points.mean(axis=0)

        # complete the Voronoi diagram by adding in undefined vertices to ridges and regions
        i = -1   # enumeration index

        for pnt_indx, vor_edge in zip(vor.ridge_points, vor.ridge_vertices):
            vor_edge = np.asarray(vor_edge)

            i = i+1 # update the count-through index

            if np.any(vor_edge < 0): # if either of the two ridge values are undefined (-1)

                # find the ridge vertice that's not equal to -1
                    new_edge = vor_edge[vor_edge >= 0][0]
                # calculate the tangent of two seed points sharing that ridge
                    tang = vor.points[pnt_indx[1]] - vor.points[pnt_indx[0]]
                    tang /= np.linalg.norm(tang)  # make the tangent a unit vector
                    norml = np.array([-tang[1], tang[0]])  # calculate the normal of the two points sharing the ridge

                    # calculate the midpoint between the two points of the ridge
                    midpoint = vor.points[pnt_indx].mean(axis=0)
                    # now there's enough information to calculate the missing direction and location of missing point
                    direction = np.sign(np.dot(midpoint - self.cluster_center, norml)) * norml
                    far_point = vor.vertices[new_edge] + direction * self.cluster_axis.max()

                    # get the current size of the voronoi vertices array, this will be the n+1 index after adding point
                    vor_ind = vor.vertices.shape[0]

                    vor.vertices = np.vstack((vor.vertices,far_point)) # add the new point to the vertices array
                    vor.ridge_vertices[i] = [new_edge,vor_ind]  # add the new index at the right spot

                    j=-1 # initialize another index for altering regions
                    for region in vor.regions:    # step through each polygon region
                        j = j+1  # update the index
                        if -1 in region and new_edge in region:  # if the region has edge of interest...
                            a = region.index(-1)              # find index in the region that is undefined (-1)
                            vor.regions[j][a] = vor_ind # add in the new vertex index to the appropriate region
                            verts = vor.vertices[region]   # get the vertices for this region
                            region = np.asarray(region)      # convert region to a numpy array so it can be sorted
                            cent = verts.mean(axis=0)     # calculate the centre point
                            angles = np.arctan2(verts[:,1]-cent[1], verts[:,0] - cent[0])  # calculate point angles
                            vor.regions[j] = region[np.argsort(angles)]   # sort indices counter-clockwise

        # finally, clip the Voronoi diagram to polygon, if user-specified by vorclose option
        if vorclose==None:
            self.ecm_verts = []

        elif vorclose=='circle':
            cluster_axis = vor.points.ptp(axis=0)    # calculate the extent of the cell points
            centx = vor.points.mean(axis=0)       # calculate the centre of the cell points

            cres = 15  # how many points desired in cropping polygon
            d_circ = cluster_axis.max()  # diameter of cropping polygon
            r_circ = 1.08*(d_circ / 2)  # radius of cropping polygon
            ind1 = np.linspace(0, 1, cres + 1)  # indices of angles defining polygon points
            angs = ind1 * 360 * (np.pi / 180)  # angles in radians defining polygon points
            circ_ptsx = r_circ * np.cos(angs) + centx[0]  # points of the polygon
            circ_ptsy = r_circ * np.sin(angs) + centx[1]  # points of the polygon

            crop_pts = np.vstack((circ_ptsx, circ_ptsy)).T  # reorganize polygon points as [x,y] pairs

            # Now clip the voronoi diagram to the cropping polygon
            self.ecm_verts = []

            i=-1 # counting index

            for poly_ind in vor.regions:  # step through each cell's polygonal regions...
                i = i+1                     # update the enumeration index
                cell_poly = vor.vertices[poly_ind]  # get the coordinates of the polygon vertices
                cell_polya = cell_poly.tolist()  # convert data structures to python lists for cropping algorithm...
                crop_ptsa = crop_pts.tolist()

                if len(cell_poly)>=3:                     # if the polygon region has at least 3 vertices
                    aa=self.clip(cell_polya,crop_ptsa)        # then send it to the clipping algorithm
                    self.ecm_verts.append(aa)     # append points to new region point list

    def clip(self, subjectPolygon, clipPolygon):  # This is the Sutherland-Hodgman polygon clipping algorithm

       def inside(p):
          return(cp2[0]-cp1[0])*(p[1]-cp1[1]) > (cp2[1]-cp1[1])*(p[0]-cp1[0])

       def computeIntersection():
          dc = [ cp1[0] - cp2[0], cp1[1] - cp2[1] ]
          dp = [ s[0] - e[0], s[1] - e[1] ]
          n1 = cp1[0] * cp2[1] - cp1[1] * cp2[0]
          n2 = s[0] * e[1] - s[1] * e[0]
          n3 = 1.0 / (dc[0] * dp[1] - dc[1] * dp[0])
          return [(n1*dp[0] - n2*dc[0]) * n3, (n1*dp[1] - n2*dc[1]) * n3]

       assert isinstance(subjectPolygon, list)
       assert isinstance(clipPolygon, list)
       assert len(subjectPolygon)
       assert len(clipPolygon)

       outputList = subjectPolygon
       cp1 = clipPolygon[-1]

       for clipVertex in clipPolygon:
          cp2 = clipVertex
          inputList = outputList
          outputList = []
          s = inputList[-1]

          for subjectVertex in inputList:
             e = subjectVertex
             if inside(e):
                if not inside(s):
                   outputList.append(computeIntersection())
                outputList.append(e)
             elif inside(s):
                outputList.append(computeIntersection())
             s = e
          cp1 = cp2
       return(outputList)

    def area(self, p):

        """
        Calculates the area of an arbitrary polygon defined by a
        set of counter-clockwise oriented points in 2D.

        Parameters
        ----------
        p               xy list of polygon points


        Returns
        -------
        area            area of a polygon in square meters

        Notes
        -------
        The algorithm is an application of Green's theorem for the functions -y and x,
        exactly in the way a planimeter works.

        """

        return 0.5 * abs(sum(x0*y1 - x1*y0 for ((x0, y0), (x1, y1)) in zip(p, p[1:] + [p[0]])))

    def vor_area(self,vor_verts):

        """
        Calculates the area of each cell in a closed 2D Voronoi diagram.

        Parameters
        ----------
        ecm_verts               nested list of [x,y] points defining each polygon


        Returns
        -------
        self.v_area            area of all polygons of the Voronoi diagram in square meters

        Notes
        -------
        Uses area(p) function. The Voronoi diagram must be closed (no outer edges extending to infinity!!!)

        """
        self.cell_area = []
        for poly in vor_verts:
            self.cell_area.append(self.area(poly))

    def cell_index(self,vor_verts):

        """
        Calculate the cell centre for each voronoi polygon and return a list
        with an index consistent with all other data lists for the cell cluster.

        Parameters
        ----------
        vor_verts               nested list of [x,y] points defining each closed polygon in the
                                Voronoi diagram

        Returns
        -------
        self.cell_centres      [x,y] coordinate of the centre of each cell as a numpy array

        Notes
        -------
        The Voronoi diagram must be closed (no outer edges extending to infinity!!!)

        """

        self.cell_centres = np.array([0,0])

        for poly in vor_verts:
            aa = np.asarray(poly)
            aa = np.mean(aa,axis=0)
            self.cell_centres = np.vstack((self.cell_centres,aa))

        self.cell_centres = np.delete(self.cell_centres, 0, 0)

    def near_neigh(self,cell_centres,search_d,cell_d):

        """
        Calculate the nearest neighbours for each cell centre in the cluster and return a numpy
        array of nn indices with an index consistent with all other data lists for the cluster.

        Parameters
        ----------
        cell_centres            A numpy array listing the [x,y] co-ordinates of each cell in the cluster
        search_d                Value defining the search distance to find nearest neighbours (search_d > cell_d)
        cell_d                  The average diameter of a cell


        Returns
        -------
        self.cell_nn            A nested list defining the indices of all nearest neighbours to each cell
        self.con_segs           A nested list defining the two [x,y] points for all cell-neighbour line connections

        Notes
        -------
        Uses numpy arrays
        Uses scipy spatial KDTree search algorithm

        """

        cell_tree = sps.KDTree(cell_centres)
        self.cell_nn=cell_tree.query_ball_point(cell_centres,search_d*cell_d)

        # define a listing of all cell-neighbour line segments
        self.con_segs = []
        for centre, indices in zip(cell_centres,self.cell_nn):
            for pt in indices:
                self.con_segs.append([centre,cell_centres[pt]])

    def boundTag(self,cell_centres):

        """

        Flag cells that are on the boundary to the environment by calculating the convex hull
        for the cell centre points cluster.

        Parameters
        ----------
        cell_centres            A numpy array listing the [x,y] co-ordinates of each cell in the cluster

        Returns
        -------
        self.bound_flag         A numpy array with 0 indicating cell not on boundary and 1 indicating boundary
                                cell
        Notes
        -------
        Uses numpy arrays

        """

        bcells = sps.ConvexHull(cell_centres)   # calculate the convex hull for the cell centre points
        self.bound_flag = np.zeros([cell_centres.shape[0]])  # initialize an array to flag cells on the boundary
        self.bound_flag[bcells.vertices] = 1      # each cell that's on the boundary the flag is set to 1

    def cellEdges(self,reg_verts):
        """

        Flag cells that are on the boundary to the environment by calculating the convex hull
        for the cell centre points cluster.

        Parameters
        ----------
        reg_verts            A nested python list of the [x,y] co-ordinates of each cell polygon in the cluster

        Returns
        -------
        self.cell_edges      A nested python list of the [x,y] point pairs defining line segments of each membrane
                            domain in a cell polygon. The list has segments arranged in a counterclockwise manner.

        """

        self.cell_edges = []
        for poly in reg_verts:
            edge =[]
            for i in range(0,len(poly)):
                edge.append([poly[i-1],poly[i]])

            self.cell_edges.append(edge)

    def cellVerts(self,cell_cent,reg_verts,sf):
        """
        Calculate the true vertices of each individual cell from the extracellular matrix (ecm) vertices
        of the closed & clipped Voronoi diagram.

        Parameters
        ----------
        reg_verts            A nested python list of the [x,y] co-ordinates of each Voronoi polygon in the cluster
        cell_cent            A list of cell centre point [x,y] co-ordinates
        sf                   The scale factor by which the vertices are dilated (must be less than 1.0!)

        Returns
        -------
        self.cell_verts      A nested python list of the [x,y] point pairs defining vertices of each individual cell
                            polygon. The points of each polygon are arranged in a counterclockwise manner.

        Notes
        -------


        """
        self.cell_verts = []

        for centre,poly in zip(cell_cent,reg_verts):
            pt_scale = []
            for vert in poly:
                pt_zero = vert - centre
                pt_scale.append(sf*pt_zero + centre)
            self.cell_verts.append(pt_scale)

    def plotPolyData(self,zdata = None,clrmap = None):
        """
        Assigns color-data to each polygon in a 2D Voronoi diagram and returns a plot instance (fig, axes)

        Parameters
        ----------
        vor_verts              Nested list of [x,y] points defining each polygon. May be ecm_verts or
                               cell_verts

        zdata                  A data array with each scalar entry corresponding to a polygon entry in
                               vor_verts. If not specified the default is z=1. If 'random'
                               is specified the method creates random vales from 0 to 1..

        clrmap                 The colormap to use for plotting. Must be specified as cm.mapname. A list of
                               available mapnames is supplied at
                               http://matplotlib.org/examples/color/colormaps_reference.html
                               Default is cm.rainbow. Good options are cm.coolwarm, cm.Blues, cm.jet


        Returns
        -------
        fig, ax                Matplotlib figure and axes instances for the plot.

        Notes
        -------
        Uses matplotlib.collections PolyCollection, matplotlib.cm, matplotlib.pyplot and numpy arrays
        Computationally slow -- not recommended for large collectives (500 x 500 um max)
        """
        if zdata == None:  # if user doesn't supply data
            z = np.ones(len(self.cell_verts)) # create flat data for plotting

        elif zdata == 'random':  # if user doesn't supply data
            z = np.random.random(len(self.cell_verts)) # create some random data for plotting

        else:
            z = zdata

        fig, ax = plt.subplots()    # define the figure and axes instances

        # Make the polygon collection and add it to the plot.
        if clrmap == None:
            clrmap = cm.rainbow

        coll = PolyCollection(self.cell_verts, array=z, cmap=clrmap, edgecolors='none')
        ax.add_collection(coll)

        # Add a colorbar for the PolyCollection
        if zdata != None:
            fig.colorbar(coll, ax=ax)

        ax.autoscale_view()
        ax.axis('equal')

        return fig,ax

    def plotCellData(self,zdata=None,clrmap=None,edgeOverlay = None,pointOverlay=None):
        """
        The work-horse of pre-defined plotting methods, this method assigns color-data to each node in cell_centres
        and interpolates data to generate a smooth surface plot. The method returns a plot instance (fig, axes)

        Parameters
        ----------
        zdata                  A data array with each scalar entry corresponding to a point in
                               cell_centres. If not specified the default is z=1. If 'random'
                               is specified the method creates random vales from 0 to 1..

        clrmap                 The colormap to use for plotting. Must be specified as cm.mapname. A list of
                               available mapnames is supplied at
                               http://matplotlib.org/examples/color/colormaps_reference.html
                               Default is cm.rainbow. Good options are cm.coolwarm, cm.Blues, cm.jet

        edgeOverlay             This option allows the user to specify whether or not they want cell edges overlayed.
                                Default is False, set to True to use.

        pointOverlay            This option allows user to specify whether or not they want cell_centre points plotted
                                Default is False, set to True to use.


        Returns
        -------
        fig, ax                Matplotlib figure and axes instances for the plot.

        Notes
        -------
        Uses matplotlib.pyplot and numpy arrays
        With edgeOverlay and pointOverlay == None, this is computationally fast and *is* recommended for plotting data
        on large collectives.


        """
        if zdata == None:  # if user doesn't supply data
            z = np.ones(len(self.cell_centres)) # create flat data for plotting

        elif zdata == 'random':  # if user doesn't supply data
            z = np.random.random(len(self.cell_centres)) # create some random data for plotting

        else:
            z = zdata

        if clrmap == None:
            clrmap = cm.rainbow

        fig, ax = plt.subplots()    # define the figure and axes instances

        sc = 1e6

        triplt = ax.tripcolor(self.cell_centres[:, 0], self.cell_centres[:, 1], z,shading='gouraud', cmap=clrmap)

        # Add a colorbar for the z-data
        if zdata != None:
            fig.colorbar(triplt, ax=ax)

        if pointOverlay == True:
            ax.plot(self.cell_centres[:,0],self.cell_centres[:,1],'k.',alpha=0.5)

        if edgeOverlay == True:
            for poly in self.cell_edges:
                for edge in poly:
                    edge = np.asarray(edge)
                    ax.plot(edge[:,0],edge[:,1],color='k',alpha=0.5)

        ax.axis('equal')
        ax.autoscale_view()

        return fig, ax

    def plotVertData(self,vor_verts,zdata=None,clrmap=None,edgeOverlay = None,pointOverlay=None):
        """
        The work-horse of pre-defined plotting methods, this method assigns color-data to each node in cell_verts,
        ecm_verts, cell_mids, or ecm_mids data structures and interpolates data to generate a smooth surface plot.
        The method returns a plot instance (fig, axes)

        Parameters
        ----------
        vor_verts              An instance of cell_verts, ecm_verts, cell_mids, or ecm_mids

        zdata                  A data array with each scalar entry corresponding to a point in
                               cell_centres. If not specified the default is z=1. If 'random'
                               is specified the method creates random vales from 0 to 1..

        clrmap                 The colormap to use for plotting. Must be specified as cm.mapname. A list of
                               available mapnames is supplied at
                               http://matplotlib.org/examples/color/colormaps_reference.html
                               Default is cm.rainbow. Good options are cm.coolwarm, cm.Blues, cm.jet

        edgeOverlay             This option allows the user to specify whether or not they want cell edges overlayed.
                                Default is False, set to True to use.

        pointOverlay            This option allows user to specify whether or not they want cell_centre points plotted
                                Default is False, set to True to use.


        Returns
        -------
        fig, ax                Matplotlib figure and axes instances for the plot.

        Notes
        -------
        Uses matplotlib.pyplot and numpy arrays
        With edgeOverlay and pointOverlay == None, this is computationally fast and *is* recommended for
        plotting data on large collectives
        """

        vor_verts_flat = [val for sublist in vor_verts for val in sublist]
        vor_verts_flat = np.asarray(vor_verts_flat)

        if zdata == None:  # if user doesn't supply data
            z = np.ones(len(vor_verts_flat)) # create flat data for plotting

        elif zdata == 'random':  # if user doesn't supply data
            z = np.random.random(len(vor_verts_flat)) # create some random data for plotting

        else:
            z = zdata

        if clrmap == None:
            clrmap = cm.rainbow

        fig, ax = plt.subplots()    # define the figure and axes instances

        sc = 1e6

        triplt = ax.tripcolor(vor_verts_flat[:, 0], vor_verts_flat[:, 1], z,shading='gouraud', cmap=clrmap)

        # Add a colorbar for the z-data
        if zdata != None:
            fig.colorbar(triplt, ax=ax)

        if pointOverlay == True:
            ax.plot(self.cell_centres[:,0],self.cell_centres[:,1],'k.',alpha=0.5)

        if edgeOverlay == True:
            for poly in self.cell_edges:
                for edge in poly:
                    edge = np.asarray(edge)
                    ax.plot(edge[:,0],edge[:,1],color='k',alpha=0.5)

        ax.axis('equal')
        ax.autoscale_view()
        return fig, ax


    def plotMemData(self,zdata=None,clrmap=None):
        """

        Assigns color-data to edges in a 2D Voronoi diagram and returns a plot instance (fig, axes)

        Parameters
        ----------
        zdata                  A data array with each scalar entry corresponding to a polygon entry in
                               vor_verts. If not specified the default is z=1. If 'random'
                               is specified the method creates random vales from 0 to 1..

        clrmap                 The colormap to use for plotting. Must be specified as cm.mapname. A list of
                               available mapnames is supplied at
                               http://matplotlib.org/examples/color/colormaps_reference.html
                               Default is cm.rainbow. Good options are cm.coolwarm, cm.Blues, cm.jet


        Returns
        -------
        fig, ax                Matplotlib figure and axes instances for the plot.

        Notes
        -------
        Uses matplotlib.collections LineCollection, matplotlib.cm, matplotlib.pyplot and numpy arrays
        Computationally slow -- not recommended for large collectives (500 x 500 um max)

        """
        fig, ax = plt.subplots()

        # Make a line collection for each cell and add it to the plot.
        for cell in self.cell_edges:
            if zdata == None:
                z = np.ones(len(cell))
            elif zdata == 'random':
                z = np.random.random(len(cell))
            else:
                z = zdata

            if clrmap == None:
                clrmap = cm.rainbow

            coll = LineCollection(cell, array=z, cmap=clrmap)
            ax.add_collection(coll)

        # Add a colorbar for the Line Collection
        if zdata != None:
            fig.colorbar(coll, ax=ax)

        ax.autoscale_view()
        ax.axis('equal')

        return fig, ax

    def plotConnectionData(self,zdata=None,clrmap=None):
        """
        Assigns color-data to connections between a cell and its nearest neighbours and returns plot instance

        Parameters
        ----------

        zdata                  A data array with each scalar entry corresponding to a polygon entry in
                               vor_verts. If not specified the default is z=1. If 'random'
                               is specified the method creates random vales from 0 to 1..

        clrmap                 The colormap to use for plotting. Must be specified as cm.mapname. A list of
                               available mapnames is supplied at
                               http://matplotlib.org/examples/color/colormaps_reference.html
                               Default is cm.rainbow. Good options are cm.coolwarm, cm.Blues, cm.jet


        Returns
        -------
        fig, ax                Matplotlib figure and axes instances for the plot.

        Notes
        -------
        Uses matplotlib.collections LineCollection, matplotlib.cm, matplotlib.pyplot and numpy arrays
        Computationally slow -- not recommended for large collectives (500 x 500 um max)

        """
        fig, ax = plt.subplots()

        if zdata == None:
            z = np.ones(len(self.con_segs))

        elif zdata == 'random':
            z = np.random.random(len(self.con_segs))

        else:
            z = zdata

        if clrmap == None:
            clrmap = cm.rainbow

         # Make a line collection for each cell and add it to the plot.

        coll = LineCollection(self.con_segs, array=z, cmap=clrmap)
        ax.add_collection(coll)

        # Plot the cell centres
        ax.plot(self.cell_centres[:,0],self.cell_centres[:,1],'ko')

        # Add a colorbar for the Line Collection
        if zdata != None:
            fig.colorbar(coll, ax=ax)

        ax.autoscale_view()
        ax.axis('equal')

        return fig, ax

    def plotBoundCells(self):
        """

        :param cell_verts:
        :param cdata:
        :return:
        """
        fig, ax = plt.subplots()

        for flag,cell in zip(self.bound_flag,self.cell_centres):
            if flag == 0:
                ax.plot(cell[0],cell[1],'ko')
            if flag == 1:
                ax.plot(cell[0],cell[1],'ro')

        ax.autoscale_view()
        ax.axis('equal')

        return fig, ax










