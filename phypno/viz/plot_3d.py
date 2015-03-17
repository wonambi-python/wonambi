"""Module to plot all the elements in 3d space.
"""
from numpy import array, isnan, max, mean, min, tile
from pyqtgraph import Vector
from pyqtgraph.opengl import GLViewWidget, GLMeshItem, MeshData
from pyqtgraph.opengl.shaders import (Shaders, ShaderProgram, VertexShader,
                                      FragmentShader)

from .base import Viz, Colormap

CHAN_COLOR = 0, 255, 0, 255
SKIN_COLOR = 239, 208, 207, 255


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
                 colormap='coolwarm'):
        """Add surfaces to the visualization.

        Parameters
        ----------
        surf : instance of phypno.attr.anat.Surf
            surface to be plotted
        color : tuple, optional
            4-element tuple, representing RGB and alpha, between 0 and 255
        values : ndarray, optional
            vector with values for each vertex
        limits_c : tuple of 2 floats, optional
            min and max values to normalize the color
        colormap : str
            one of the colormaps in vispy
        """
        color = array(color) / 255

        glOptions = 'opaque'

        if values is not None:
            if limits_c is None:
                limits_c = min(values), max(values)

            colormap = Colormap(name=colormap, limits=limits_c)
            vertexColors = colormap.mapToFloat(values)
            vertexColors[isnan(values)] = color

        else:
            vertexColors = tile(color, (surf.tri.shape[0], 1))
            if color[3] < 1:
                glOptions = 'translucent'  # use this when using transparency

        mesh = MeshData(vertexes=surf.vert, faces=surf.tri,
                        vertexColors=vertexColors)

        mesh._vertexNormals = -1 * mesh.vertexNormals()
        self._mesh = GLMeshItem(meshdata=mesh, smooth=True, shader='brain',
                                glOptions=glOptions)
        self._widget.addItem(self._mesh)

        surf_center = mean(surf.vert, axis=0)
        if surf_center[0] < 0:
            azimuth = 180
        else:
            azimuth = 0

        self._widget.setCameraPosition(azimuth=azimuth)
        self._widget.opts['center'] = Vector(surf_center)
        self._widget.show()

    def add_chan(self, chan, color=CHAN_COLOR, values=None):
        """Add channels to visualization

        Parameters
        ----------
        chan : instance of Channels
            channels to plot
        color : tuple
            4-element tuple, representing RGB and alpha, between 0 and 255
        values : ndarray
            array with values for each channel
        """
        color = array(color) / 255

        # larger if colors are meaningful
        if values is not None:
            radius = 3
        else:
            radius = 1.5

        sphere = MeshData.sphere(10, 10, radius=radius)
        sphere.setVertexColors(tile(color,
                                    (sphere._vertexes.shape[0], 1)))

        for one_chan in chan.chan:
            mesh = GLMeshItem(meshdata=sphere, smooth=True,
                              shader='shaded', glOptions='translucent')
            mesh.translate(*one_chan.xyz)

            self._widget.addItem(mesh)
        self._widget.show()
