"""Module with helper functions for plotting
"""
from numpy import array, clip, float32, r_
from vispy.scene.visuals import create_visual_node
from vispy.gloo import VertexBuffer
from vispy.io.image import _make_png
from vispy.visuals import Visual


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


class Viz():

    def _repr_png_(self):
        """This is used by ipython to plot inline.
        """
        try:
            region = (10, 10,  # TODO: how to get these values
                      int(self._canvas.view.bounds(0)[1]),
                      int(self._canvas.view.bounds(1)[1]))
        except AttributeError:
            region = None

        self._fig.show(False)
        return bytes(_make_png(self._fig.render(region=region), ))

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
    """Normalize value between min and max values.
    It also clips the values, so that you cannot have values higher or lower
    than the range."""
    x = (x - min_value) / (max_value - min_value)
    return clip(x, min_value, max_value)


class SimpleMeshVisual(Visual):
    """Simple Visual for Mesh, with light coming from left and right.

    Parameters
    ----------
    meshdata : instance of vispy.geometry.MeshData
        the meshdata, with or without colors for each vertex
    color : 3- or 4-element tuple
        color for the whole mesh (color for each vertex should be in meshdata)
    light_vec : 3-element tuple
        light direction, only the axis, because light comes from both directions

    Notes
    -----
    I decided not to use the mesh visual that comes with vispy because I don't
    like the mirror reflection, which is really strong. Also, here I can
    control the parameters. The hard part is that it relies on glsl above.
    """
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

SimpleMesh = create_visual_node(SimpleMeshVisual)
