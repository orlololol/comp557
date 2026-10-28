import moderngl as mgl
import glm
import numpy as np

LINE_VS = """
#version 330
uniform mat4 u_proj;
uniform mat4 u_view;
uniform mat4 u_model;
in vec3 in_position;
void main() {
    gl_Position = u_proj * u_view * u_model * vec4(in_position, 1.0);
}
"""

LINE_FS = """
#version 330
uniform vec4 u_color;
out vec4 fragColor;
void main() {
    fragColor = u_color;
}
"""

# 8 unique corners of the -1..1 cube, shared by pairs of edges via the index buffer below.
_CUBE_VERTICES = np.array([
    [-1, -1, -1], [ 1, -1, -1], [ 1,  1, -1], [-1,  1, -1],
    [-1, -1,  1], [ 1, -1,  1], [ 1,  1,  1], [-1,  1,  1],
], dtype='f4')

_CUBE_EDGE_INDICES = np.array([
    0, 1, 1, 2, 2, 3, 3, 0,  # near/bottom loop
    4, 5, 5, 6, 6, 7, 7, 4,  # far/top loop
    0, 4, 1, 5, 2, 6, 3, 7,  # connecting edges
], dtype='i4')

_XY_QUAD_VERTICES = np.array([
    [-1, -1, 0], [ 1, -1, 0], [ 1,  1, 0], [-1,  1, 0],
], dtype='f4')

_XY_QUAD_EDGE_INDICES = np.array([
    0, 1, 2, 3
], dtype='i4')


class LineHelper:
    def __init__(self, ctx: mgl.Context):
        # compile line shader, create VAO/VBO for lines
        self.ctx = ctx
        self.prog = self.ctx.program(vertex_shader=LINE_VS, fragment_shader=LINE_FS)

        self.wire_cube_vbo = self.ctx.buffer(_CUBE_VERTICES.tobytes())
        self.wire_cube_ibo = self.ctx.buffer(_CUBE_EDGE_INDICES.tobytes())
        self.wire_cube_vao = self.ctx.vertex_array(
            self.prog, [(self.wire_cube_vbo, '3f', 'in_position')], self.wire_cube_ibo
        )

        self.wire_rect_vbo = self.ctx.buffer(_XY_QUAD_VERTICES.tobytes())
        self.wire_rect_ibo = self.ctx.buffer(_XY_QUAD_EDGE_INDICES.tobytes())
        self.wire_rect_vao = self.ctx.vertex_array(
            self.prog, [(self.wire_rect_vbo, '3f', 'in_position')], self.wire_rect_ibo
        )

        x_axis = np.array([[0, 0, 0], [1, 0, 0]], dtype='f4')
        x_vbo = self.ctx.buffer(x_axis.tobytes())
        self.x_vao = self.ctx.vertex_array(self.prog, [(x_vbo, '3f', 'in_position')])
        y_axis = np.array([[0, 0, 0], [0, 1, 0]], dtype='f4')
        y_vbo = self.ctx.buffer(y_axis.tobytes())
        self.y_vao = self.ctx.vertex_array(self.prog, [(y_vbo, '3f', 'in_position')])
        z_axis = np.array([[0, 0, 0], [0, 0, 1]], dtype='f4')
        z_vbo = self.ctx.buffer(z_axis.tobytes())
        self.z_vao = self.ctx.vertex_array(self.prog, [(z_vbo, '3f', 'in_position')])


    def draw_wire_cube(self, P: glm.mat4, V: glm.mat4, M: glm.mat4, color: glm.vec4):
        self.ctx.enable(mgl.BLEND)
        self.ctx.blend_func = (mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA)
        self.prog['u_proj'].write(P)
        self.prog['u_view'].write(V)
        self.prog['u_model'].write(M)
        self.prog['u_color'].value = tuple(color)
        self.wire_cube_vao.render(mgl.LINES)
        self.ctx.disable(mgl.BLEND)

        
    def draw_wire_rect(self, P: glm.mat4, V: glm.mat4, M: glm.mat4, color: glm.vec4):
        self.ctx.enable(mgl.BLEND)
        self.ctx.blend_func = (mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA)
        self.prog['u_proj'].write(P)
        self.prog['u_view'].write(V)
        self.prog['u_model'].write(M)
        self.prog['u_color'].value = tuple(color)
        self.wire_rect_vao.render(mgl.LINE_LOOP)
        self.ctx.disable(mgl.BLEND)


    def draw_axis( self, P: glm.mat4, V: glm.mat4, M: glm.mat4, scale=1.0):
        """Draws a simple XYZ axis at the origin of the model matrix."""
        self.ctx.enable(mgl.BLEND)
        self.ctx.blend_func = (mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA)
        self.prog['u_proj'].write(P)
        self.prog['u_view'].write(V)
        self.prog['u_model'].write(M * glm.scale(glm.mat4(1.0), glm.vec3(scale, scale, scale)))
        self.prog['u_color'].value = (1.0, 0.0, 0.0, 1.0)
        self.x_vao.render(mgl.LINES)
        self.prog['u_color'].value = (0.0, 1.0, 0.0, 1.0)
        self.y_vao.render(mgl.LINES)
        self.prog['u_color'].value = (0.0, 0.0, 1.0, 1.0)
        self.z_vao.render(mgl.LINES)
        self.ctx.disable(mgl.BLEND)