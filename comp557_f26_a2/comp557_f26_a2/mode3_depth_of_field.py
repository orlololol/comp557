from render_context import RenderContext, fibonacci_disc_point, METERS_PER_PIXEL
import glm

class Mode3DepthOfField:
	def __init__(self):
		self.name = "3: Camera DoF"

	def paint( self, render_ctx: RenderContext ):
		render_ctx.ctx.clear()
		render_ctx.accum_buffer.begin()
		N = render_ctx.num_samples
		weight = 1.0 / N
		for i in range(N):
			render_ctx.accum_buffer.begin_sample()

			P, V = (glm.mat4(), glm.mat4()) # TODO: compute the correct matricies
			render_ctx.scene.paintGL( P, V )

			render_ctx.accum_buffer.accumulate( weight )
		render_ctx.accum_buffer.resolve_to_screen()