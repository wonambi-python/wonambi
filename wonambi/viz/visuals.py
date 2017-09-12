from vispy.visuals import Visual
from vispy.scene.visuals import create_visual_node
from numpy import array, float32, r_
from vispy.gloo import VertexBuffer

VERT_SHADER = """
#version 120
varying vec3 v_position;
varying vec4 v_color;
varying vec3 v_normal;

void main() {
    v_position = $a_position;
    v_normal = $a_normal;
    v_color = $a_color;
    gl_Position = $transform(vec4($a_position, 1));
}
"""

FRAG_SHADER = """
#version 120
varying vec3 v_position;
varying vec4 v_color;
varying vec3 v_normal;

void main() {
    float p = dot(v_normal, normalize(vec3($u_light_position)));

    vec4 color = v_color;
    color.rgb = color.rgb * ($u_ambient + $u_diffuse * abs(p));

    gl_FragColor = color;
}
"""


class SurfaceMeshVisual(Visual):
    def __init__(self, meshdata):
        Visual.__init__(self, VERT_SHADER, FRAG_SHADER)

        v = meshdata.get_vertices(indexed='faces').astype(float32)
        self._vertices = VertexBuffer(v)

        v_norm = meshdata.get_vertex_normals(indexed='faces').astype(float32)
        self._normals = VertexBuffer(v_norm)

        v_col = meshdata.get_vertex_colors(indexed='faces').astype(float32)
        self._colors = VertexBuffer(v_col)

        self.set_light(position=(1., 0., 0.),
                       ambient=.2,
                       diffuse=.8,
                       )
        self._draw_mode = 'triangles'
        # self.set_gl_state('opaque', depth_test=True, cull_face=True)
        self.set_gl_state('translucent', depth_test=True, cull_face=False, blend=True, blend_func=('src_alpha', 'one_minus_src_alpha'))

    def _prepare_transforms(self, view):
        view.view_program.vert['transform'] = view.get_transform()

    def _prepare_draw(self, view):
        self.shared_program.vert['a_position'] = self._vertices
        self.shared_program.vert['a_normal'] = self._normals
        self.shared_program.vert['a_color'] = self._colors

    def set_light(self, position=None, ambient=None, diffuse=None):
        if position is not None:
            self.shared_program.frag['u_light_position'] = position
        if ambient is not None:
            self.shared_program.frag['u_ambient'] = ambient
        if diffuse is not None:
            self.shared_program.frag['u_diffuse'] = diffuse
        self.update()


SurfaceMesh = create_visual_node(SurfaceMeshVisual)
