from render_context import RenderContext, METERS_PER_PIXEL

class Mode6Anaglyph:
	def __init__(self):
		self.name = "6: Anaglyph"

	def paint( self, render_ctx: RenderContext ):

		fbo = render_ctx.ctx.screen
		fbo.clear()
		fbo.color_mask = (True, False, False, False)
		fbo.clear() # clear to have color mask take effect

		# TODO: compute correct matrices and draw

		fbo.color_mask = (False, True, True, False)
		fbo.clear() # clear to have color mask take effect

		# TODO: compute correct matrices and draw

		fbo.color_mask = (True, True, True, True)