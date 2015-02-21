"""Module to plot all the elements in 3d space.

"""
from numpy import max, mean, min, ones, tile
from pyqtgraph import Vector
from pyqtgraph.opengl import GLViewWidget, GLMeshItem, MeshData
from pyqtgraph.opengl.shaders import (Shaders, ShaderProgram, VertexShader,
                                      FragmentShader)

from .base import Viz, Colormap

CHAN_COLOR = (20 / 255., 20 / 255., 20 / 255., 1)
SKIN_COLOR = (239 / 255., 208 / 255., 207 / 255., 0.7)


shader = ShaderProgram('brain', [
            VertexShader("""
                varying vec3 normal;
                void main() {
                    // compute here for use in fragment shader
                    normal = normalize(gl_NormalMatrix * gl_Normal);
                    gl_FrontColor = gl_Color;
                    gl_BackColor = gl_Color;
                    gl_Position = ftransform();
                }
            """),
            FragmentShader("""
                varying vec3 normal;
                void main() {
                    float p = dot(normal, normalize(vec3(0.0, -2.0, -10.0)));
                    p = p < 0. ? 0. : p * 0.8;
                    vec4 color = gl_Color;
                    color.x = color.x * (0.2 + p);
                    color.y = color.y * (0.2 + p);
                    color.z = color.z * (0.2 + p);
                    gl_FragColor = color;
                }
            """)
        ])
Shaders.append(shader)


class Viz3(Viz):
    """The 3d visualization, ordinarily it should hold a surface and electrodes

    """
    def __init__(self, projection='ortho'):
        self._widget = GLViewWidget()
        self._widget.setCameraPosition(elevation=10)

        if projection == 'ortho':
            # not really ortho, but pretty good
            self._widget.opts['fov'] = 0.5
            self._widget.opts['distance'] = 22000
        else:
            self._widget.opts['distance'] = 250

    def add_surf(self, surf, color=SKIN_COLOR, values=None, limits_c=None,
                 colormap='jet'):
        """Add surfaces to the visualization.

        Parameters
        ----------
        surf : instance of phypno.attr.anat.Surf
            surface to be plotted
        color : tuple, optional
            4-element tuple, representing RGB and alpha, between 0 and 1
        values : ndarray, optional
            vector with values for each vertex
        limits_c : tuple of 2 floats, optional
            min and max values to normalize the color
        colormap : str
            one of the colormaps in vispy

        Notes
        -----
        'color' vs 'xyz' and 'values' are mutally exclusive. You need to
        specify 'xyz' and 'values' if you use those.

        If you specify 'values', then you'll need a matrix called 'xyz2surf'
        that converts from the channel values to the electrodes.
        It takes a few seconds to compute but once it's done, plotting is
        really fast.
        You can pre-compute it (using arbitrary values) and pass it as
        attribute to this class.
        """
        if values is not None:
            if limits_c is None:
                limits_c = min(values), max(values)

            print(colormap)
            colormap = Colormap(name=colormap, limits=limits_c)
            vertexColors = colormap.map(values)

        else:
            vertexColors = tile(color, (surf.tri.shape[0], 1))

        mesh = MeshData(vertexes=surf.vert, faces=surf.tri,
                        vertexColors=vertexColors)

        mesh._vertexNormals = -1 * mesh.vertexNormals()
        self._mesh = GLMeshItem(meshdata=mesh, smooth=True, shader='brain',
                                glOptions='additive')
        self._widget.addItem(self._mesh)

        surf_center = mean(surf.vert, axis=0)
        if surf_center[0] < 0:
            azimuth = 180
        else:
            azimuth = 0

        self._widget.setCameraPosition(azimuth=azimuth)
        self._widget.opts['center'] = Vector(surf_center)
        self._widget.show()

    def add_chan(self, chan, color=(0, 1, 0, 1), values=None):

        # larger if colors are meaningful
        if values is not None:
            radius = 3
        else:
            radius = 1.5

        sphere = MeshData.sphere(10, 10, radius=radius)
        sphere.setVertexColors(tile(color, (sphere._vertexes.shape[0], 1)))

        for one_chan in chan.chan:
            mesh = GLMeshItem(meshdata=sphere, smooth=True,
                              shader='shaded', glOptions='translucent')
            mesh.translate(*one_chan.xyz)

            self._widget.addItem(mesh)
        self._widget.show()

    def add_chan_old(self, chan, color=(0, 1, 0, 1), values=None, limits_c=None,
                 colormap='jet'):
        """
        Parameters
        ----------
        chan : instance of phypno.attr.Channels
            channels to plot.
        color : tuple, optional
            4-element tuple, representing RGB and alpha, between 0 and 1
        values : ndarray, optional
            vector with values for each electrode
        limits_c : tuple of 2 floats, optional
            min and max values to normalize the color
        colormap : str
            one of the colormaps in vispy

        """


        if toolkit == 'vispy':
            sphere = create_sphere(10, 10, radius=radius)

        if self._viewbox is not None:
            viewbox = self._viewbox
        else:
            viewbox = self._canvas.central_widget.add_view()
            viewbox.set_camera('turntable', mode=CAMERA, azimuth=90,
                               distance=DISTANCE)
            self._viewbox = viewbox

        if values is not None:
            if limits_c is None:
                min_c = min(values)  # maybe NaN here
                max_c = max(values)
            else:
                min_c, max_c = limits_c

            values = (values - min_c) / (max_c - min_c)
            if toolkit == 'visvis':
                colors = values
            elif toolkit == 'vispy':
                colors = convert_color(values, colormap)
        else:
            colors = [color] * chan.n_chan

        for one_chan, one_color in zip(chan.chan, colors):
            if toolkit == 'visvis':
                mesh = solidSphere(list(one_chan.xyz), scaling=radius)
                if values is not None:
                    n_vert = mesh._vertices.shape[0]
                    mesh.SetValues(one_color * ones((n_vert, 1)))
                    mesh.colormap = visvis_colormap(colormap)
                    mesh.clim = (0, 1)

                else:
                    mesh.faceColor = one_color

            elif toolkit == 'vispy':
                mesh = Mesh(meshdata=sphere, color=one_color, shading='smooth')
                mesh.transform = STTransform(translate=one_chan.xyz)
                viewbox.add(mesh)
