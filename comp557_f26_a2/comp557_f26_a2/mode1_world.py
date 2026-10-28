import glm
from render_context import RenderContext, fibonacci_disc_point, METERS_PER_PIXEL

WHITE = glm.vec4(1,1,1,1)       # for primary camera frustum
GREEN = glm.vec4(0.5,1,0.5,1)   # for screen plane
RED = glm.vec4(1,0,0,1)         # for left eye frustum
CYAN = glm.vec4(0,1,1,1)        # for right eye frustum
BLUE = glm.vec4(0.5,0.5,1,1)    # for focal plane


class Mode1World:
    def __init__(self):
        self.name = "1: World"
        self.draw_screen_plane = True
        self.draw_focal_plane = True
        self.draw_all_sample_frustums = False
        self.frustum_view_mode = "central" # or "stereo pair"

        # VIEWING PARAMETERS FOR THE THIRD-PERSON WORLD VIEW
        self.world_viewing_distance = 5.0 # distance from the 3rd person world camera to the origin of the world
        self.world_view_orientation = glm.mat4(1.0)
        self.fovy = 27.0 # field of view in degrees, for the 3rd person view


    def paint( self, render_ctx: RenderContext ):
        render_ctx.ctx.clear()

        w = render_ctx.ctx.viewport[2]
        h = render_ctx.ctx.viewport[3]		
        aspect = w / h
        P = glm.perspective(glm.radians(self.fovy), aspect, 0.1, 20.0)
        look_at = glm.lookAt(glm.vec3(0,0,self.world_viewing_distance), glm.vec3(0, 0, 0), glm.vec3(0, 1, 0))
        V = look_at * self.world_view_orientation 
        render_ctx.scene.paintGL( P, V )
        
        if self.draw_screen_plane:
            M = glm.mat4()
            # TODO: finish this!
            render_ctx.line_helper.draw_wire_rect(P, V, M, GREEN)

        if self.draw_focal_plane:
            if self.frustum_view_mode == "central":
                # draw focal plane rectangle
                ...
            else:
                # draw left and right focal plane rectangles
                ...

        if self.frustum_view_mode == "central":
            if self.draw_all_sample_frustums:
                ...
            else:
                ...
        else:
            # draw left and right frustums
            if self.draw_all_sample_frustums:
                ...
            else:
                ...
