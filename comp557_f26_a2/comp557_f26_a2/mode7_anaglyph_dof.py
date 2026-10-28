from render_context import RenderContext, fibonacci_disc_point, METERS_PER_PIXEL

class Mode7AnaglyphDOF:
	def __init__(self):
		self.name = "7: Anaglyph DoF"

	def paint( self, render_ctx: RenderContext ):
		render_ctx.accum_buffer.begin()
		N = render_ctx.num_samples
		weight = 1.0 / N
		for i in range(N):
			render_ctx.accum_buffer.begin_sample()
			fbo = render_ctx.accum_buffer.scene_fbo
			fbo.color_mask = (True, False, False, False)
			fbo.clear() # clear to have color mask take effect

			# TODO: compute correct matrices and draw

			fbo.color_mask = (False, True, True, False)
			fbo.clear() # clear to have color mask take effect

			# TODO: compute correct matrices and draw
	
			fbo.color_mask = (True, True, True, True)
			render_ctx.accum_buffer.accumulate( weight )
		
		render_ctx.accum_buffer.resolve_to_screen()