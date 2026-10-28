from render_context import RenderContext, METERS_PER_PIXEL

class Mode5RightEye:
	def __init__(self):
		self.name = "5: Right Eye"

	def paint( self, render_ctx: RenderContext ):
		render_ctx.ctx.screen.clear()
		render_ctx.ctx.screen.color_mask = (False, True, True, False)
		render_ctx.ctx.screen.clear() # clear to have color mask take effect

		# TODO: compute the correct matricies and draw

		render_ctx.ctx.screen.color_mask = (True, True, True, True)
