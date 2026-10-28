import numpy as np
import moderngl as mgl
    
QUAD_VS = """
#version 330
in vec2 in_position;
in vec2 in_uv;
out vec2 v_uv;
void main() {
    v_uv = in_uv;
    gl_Position = vec4(in_position, 0.0, 1.0);
}
"""

QUAD_FS = """
#version 330
in vec2 v_uv;
uniform sampler2D u_texture;
uniform float u_weight;
out vec4 fragColor;
void main() {
    fragColor = texture(u_texture, v_uv) * u_weight;
}
"""

DISPLAY_FS = """
#version 330
in vec2 v_uv;
uniform sampler2D u_texture;
out vec4 fragColor;
void main() {
    fragColor = texture(u_texture, v_uv);
}
"""

class AccumulationBuffer:
    """Software emulation of glAccum: additive-blend a fullscreen quad into an f4 FBO, no read-back needed."""

    def __init__(self, ctx: mgl.Context):
        self.ctx = ctx
        # weighted copy (for accumulating) and plain display (for resolving) share one quad VAO
        self.quad_prog = self.ctx.program(vertex_shader=QUAD_VS, fragment_shader=QUAD_FS)
        self.display_prog = self.ctx.program(vertex_shader=QUAD_VS, fragment_shader=DISPLAY_FS)
        # Quad VBO (pos2f, uv2f)
        quad_data = np.array([
            [-1.0, -1.0, 0.0, 0.0],
            [ 1.0, -1.0, 1.0, 0.0],
            [-1.0,  1.0, 0.0, 1.0],
            [ 1.0,  1.0, 1.0, 1.0],
        ], dtype='f4')
        self.quad_vbo = self.ctx.buffer(quad_data.tobytes())
        self.quad_vao = self.ctx.vertex_array(
            self.quad_prog,
            [(self.quad_vbo, '2f 2f', 'in_position', 'in_uv')]
        )
        self.display_vao = self.ctx.vertex_array(
            self.display_prog,
            [(self.quad_vbo, '2f 2f', 'in_position', 'in_uv')]
        )
        self.acc_fbo = None
        self.acc_texture = None
        self.scene_fbo = None
        self.scene_texture = None
        self.scene_depth = None
        self.size = (0, 0)

    def _release(self):
        for res in (self.acc_texture, self.acc_fbo, self.scene_texture, self.scene_depth, self.scene_fbo):
            if res: res.release()

    def begin(self):
        w = self.ctx.viewport[2]
        h = self.ctx.viewport[3]	
        if (w, h) != self.size:
            self._release()
            # render to texture, 4 channels, 32-bit float each, for high-precision accumulation
            self.acc_texture = self.ctx.texture((w, h), 4, dtype='f4')
            self.acc_fbo = self.ctx.framebuffer(color_attachments=[self.acc_texture])
            # per-sample scene target: normal depth-tested render, overwritten each sample
            self.scene_texture = self.ctx.texture((w, h), 4, dtype='f4')
            self.scene_depth = self.ctx.depth_renderbuffer((w, h))
            self.scene_fbo = self.ctx.framebuffer(
                color_attachments=[self.scene_texture],
                depth_attachment=self.scene_depth,
            )
            self.size = (w, h)
        self.acc_fbo.use()
        self.acc_fbo.clear()

    def begin_sample(self):
        """Bind and clear the per-sample scene target; caller renders geometry after this."""
        self.scene_fbo.use()
        self.scene_fbo.clear()

    def accumulate(self, weight):
        # blend ONE+ONE lets the raster pipeline do the "read old + add new" for us
        self.acc_fbo.use()
        self.ctx.enable(mgl.BLEND)
        self.ctx.blend_func = (mgl.ONE, mgl.ONE)
        self.scene_texture.use(location=0)
        self.quad_prog['u_texture'].value = 0
        self.quad_prog['u_weight'].value = weight
        self.quad_vao.render(mgl.TRIANGLE_STRIP)
        self.ctx.disable(mgl.BLEND)

    def resolve_to_screen(self):
        self.ctx.screen.use()
        self.ctx.screen.clear()
        self.acc_texture.use(location=0)
        self.display_prog['u_texture'].value = 0
        self.display_vao.render(mgl.TRIANGLE_STRIP)