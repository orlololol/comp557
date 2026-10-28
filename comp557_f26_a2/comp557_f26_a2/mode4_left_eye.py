from render_context import RenderContext, METERS_PER_PIXEL
import glm

class Mode4LeftEye:
	def __init__(self):
		self.name = "4: Left Eye"

	def paint( self, render_ctx: RenderContext ):
		render_ctx.ctx.screen.clear()
		render_ctx.ctx.screen.color_mask = (True, False, False, False)
		render_ctx.ctx.screen.clear() # clear to have color mask take effect

		P, V = (glm.mat4(), glm.mat4()) # TODO: compute the correct matricies
		render_ctx.scene.paintGL( P, V )

		render_ctx.ctx.screen.color_mask = (True, True, True, True)
