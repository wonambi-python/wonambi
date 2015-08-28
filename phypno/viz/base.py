"""Module with helper functions for plotting
"""
from numpy import (arange,
                   array,
                   clip,
                   c_,
                   float32,
                   linspace,
                   ones,
                   r_,
                   zeros)
from vispy.scene.visuals import create_visual_node
from vispy.gloo import VertexBuffer
from vispy.io.image import _make_png
from vispy.visuals import Visual

from pyqtgraph import ColorMap


vertex_shader = """
varying vec3 normal_vec;
varying vec4 color_vec;

void main() {
    normal_vec = $normal;
    color_vec = $color;
    gl_Position = $transform(vec4($position, 1));
}
"""

fragment_shader = """
varying vec3 normal_vec;
varying vec4 color_vec;

void main() {
    float p = dot(normal_vec, normalize(vec3($light_vec)));
    p = p < 0. ? 0. : p * 0.8;

    float op = dot(normal_vec, normalize(-1 * vec3($light_vec)));
    op = op < 0. ? 0. : op * 0.8;

    vec4 color = color_vec;
    color.rgb = color.rgb * (0.2 + p + op);

    gl_FragColor = color;
}
"""

coolwarm = array([[59, 76, 192],
                  [68, 90, 204],
                  [77, 104, 215],
                  [87, 117, 225],
                  [98, 130, 234],
                  [108, 142, 241],
                  [119, 154, 247],
                  [130, 165, 251],
                  [141, 176, 254],
                  [152, 185, 255],
                  [163, 194, 255],
                  [174, 201, 253],
                  [184, 208, 249],
                  [194, 213, 244],
                  [204, 217, 238],
                  [213, 219, 230],
                  [221, 221, 221],
                  [229, 216, 209],
                  [236, 211, 197],
                  [241, 204, 185],
                  [245, 196, 173],
                  [247, 187, 160],
                  [247, 177, 148],
                  [247, 166, 135],
                  [244, 154, 123],
                  [241, 141, 111],
                  [236, 127, 99],
                  [229, 112, 88],
                  [222, 96, 77],
                  [213, 80, 66],
                  [203, 62, 56],
                  [192, 40, 47],
                  [180, 4, 38]])


class Viz():

    def _repr_png_(self):
        """This is used by ipython to plot inline.
        """
        self._fig.show(False)
        return bytes(_make_png(self._fig.render(), ))

    def save(self, png_file):
        """Save png to disk.

        Parameters
        ----------
        png_file : path to file
            file to write to

        Notes
        -----
        It relies on _repr_png_, so fix issues there.
        """
        with open(png_file, 'wb') as f:
            f.write(self._repr_png_())

def normalize(x, min_value, max_value):
    x = (x - min_value) / (max_value - min_value)
    return clip(x, min_value, max_value)


class Colormap(ColorMap):
    """Create colormap using predefined color scheme.

    Parameters
    ----------
    name : str
        name of the colormap
    limits : tuple of two floats
        min and max values of the colormap

    Notes
    -----
    bwr : blue-white-red diverging
    cool : blue-dominanted sequential
    coolwarm : continuous blue-white-red diverging
       http://www.sandia.gov/~kmorel/documents/ColorMaps/
    jet : old-school Matlab
    hot : red-dominated sequential
    """
    def __init__(self, name='coolwarm', limits=(0, 1)):
        if name == 'bwr':
            pos = linspace(limits[0], limits[1], 3)
            r = r_[0, 255, 255]
            g = r_[0, 255, 0]
            b = r_[255, 255, 0]
            color = array(c_[r, g, b])

        elif name == 'cool':
            pos = linspace(limits[0], limits[1], 2)
            r = r_[0, 255]
            g = r_[255, 0]
            b = r_[255, 255]
            color = array(c_[r, g, b])

        elif name == 'coolwarm':
            pos = linspace(limits[0], limits[1], coolwarm.shape[0])
            color = coolwarm

        elif name == 'jet':
            pos = linspace(limits[0], limits[1], 66)
            r = r_[zeros(24), arange(0, 255, 15), 255 * ones(17), arange(255, 135, -15)]
            g = r_[zeros(7), arange(0, 255, 15), 255 * ones(17), arange(255, 0, -15), zeros(8)]
            b = r_[arange( 150, 255, 15),  255 * ones(17), arange(255, 0, -15), zeros(25)]
            color = array(c_[r, g, b])

        elif name == 'hot':
            pos = linspace(limits[0], limits[1], 4)
            r = r_[10, 255, 255, 255]
            g = r_[0, 0, 255, 255]
            b = r_[0, 0, 0, 255]
            color = array(c_[r, g, b])

        # add alpha and it's necessary to pass it as int
        color = c_[color, 255 * ones((color.shape[0], 1))].astype(int)
        super().__init__(pos, color)


class BrainMeshVisual(Visual):

    def __init__(self, meshdata, color=None, light_vec=(1, 0, 0)):
        Visual.__init__(self, vertex_shader, fragment_shader)

        v = meshdata.get_vertices(indexed='faces').astype(float32)
        self._vertices = VertexBuffer(v)

        v_norm = meshdata.get_vertex_normals(indexed='faces').astype(float32)
        self._normals = VertexBuffer(v_norm)

        if color is not None:
            if len(color) == 3:
                color = r_[array(color), 1.]
            self._colors = color

        else:
            v_col = meshdata.get_vertex_colors(indexed='faces').astype(float32)
            self._colors = VertexBuffer(v_col)

        self._light_vec = light_vec

        self._draw_mode = 'triangles'
        self.set_gl_state('opaque', depth_test=True,  cull_face=True)

    def _prepare_transforms(self, view):
        view.view_program.vert['transform'] = view.get_transform()

    def _prepare_draw(self, view):
        self.shared_program.vert['position'] = self._vertices
        self.shared_program.vert['normal'] = self._normals
        self.shared_program.vert['color'] = self._colors
        self.shared_program.frag['light_vec'] = self._light_vec

BrainMesh = create_visual_node(BrainMeshVisual)
