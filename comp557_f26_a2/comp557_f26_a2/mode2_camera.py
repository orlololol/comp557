from render_context import RenderContext, METERS_PER_PIXEL
import glm

class Mode2Camera:
	def __init__(self):
		self.name = "2: Camera"

	def paint( self, render_ctx: RenderContext ):
		render_ctx.ctx.clear()
		P, V = (glm.mat4(), glm.mat4()) # TODO: compute the correct matricies
		render_ctx.scene.paintGL( P, V )
		