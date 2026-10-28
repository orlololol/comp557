import moderngl as mgl
import glm
import math
from lines_helper import LineHelper
from accum_buffer import AccumulationBuffer
from usd_scene import USDScene

# Settings for the physical screen, used to compute the correct viewing and projection matrices.
# Computing this automatically can be tricky (e.g., EDID missing, high DPI scaling, etc.), 
# so we just hard-code it here for now.
SCREEN_WIDTH_PIXELS = 1366.0  # could query with QScreen.size().width()
SCREEN_WIDTH_METERS = 0.275   # could query with QScreen.physicalSize()
METERS_PER_PIXEL = SCREEN_WIDTH_METERS / SCREEN_WIDTH_PIXELS

GOLDEN_ANGLE = math.pi * (3.0 - math.sqrt(5.0))  # ≈ 2.39996 rad (137.508°)

def fibonacci_disc_point(i: int, N: int, radius: float = 1.0) -> tuple[float, float]:
    """ (x, y) coordinates for point i of N on a disc using a Fibonacci spiral. """
    # Radius mapped for equal-area distribution
    r = radius * math.sqrt((i + 0.5) / N)
    theta = i * GOLDEN_ANGLE
    x = r * math.cos(theta)
    y = r * math.sin(theta)
    return x, y


class RenderContext():

    def __init__(self, ctx: mgl.Context, scene: USDScene):
        """ Hold render state, and information necessary to set up
        projeciton and view matrices for rendering. """
        self.ctx = ctx
        self.scene = scene
        self.line_helper = LineHelper(ctx)
        self.accum_buffer = AccumulationBuffer(ctx)

        # Viewing parameters for the primary camera and variants, all units in meters.
        self.scene_distance = 0.5
        self.screen_distance = 0.5
        self.focal_distance = 0.6
        self.interocular_distance = 0.063
        self.aperture_radius = 0.003

        self.near_distance = 0.25
        self.far_distance = 1.0

        self.num_samples = 16

    # TODO: add helper methods here for making frustum and view matrices
