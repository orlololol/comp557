import colorsys
import random
import time
import glm
import moderngl as mgl
import numpy as np
from pxr import Usd, UsdGeom, Gf

VERTEX_SHADER = """
#version 330
uniform mat4 vp;
uniform mat4 model;
in vec3 in_pos;
in vec3 in_normal;
out vec3 world_normal;
void main() {
    world_normal = mat3(model) * in_normal;
    gl_Position = vp * model * vec4(in_pos, 1.0);
}
"""

FRAGMENT_SHADER = """
#version 330
in vec3 world_normal;
uniform vec3 object_color;
out vec4 frag_color;
void main() {
    vec3 n = normalize(world_normal);
    vec3 light_dir = normalize(vec3(0.4, 0.6, 1.0));
    float lambert = max(dot(n, light_dir), 0.0);
    float brightness = 0.25 + 0.75 * lambert;
    frag_color = vec4(object_color * brightness, 1.0);
}
"""


def usd_matrix_to_glm(matrix: Gf.Matrix4d) -> glm.mat4:
    return glm.mat4(np.array(matrix, dtype="f4").T)


class USDScene:
    def __init__(self, filename):        
        self.stage = Usd.Stage.Open(filename)
        if not self.stage:
            raise RuntimeError(f"Could not open USD file: {filename}")
        self.start_frame = self.stage.GetStartTimeCode()
        self.end_frame = self.stage.GetEndTimeCode()
        self.frames_per_second = self.stage.GetTimeCodesPerSecond() or 24.0
        self.started_at = time.perf_counter()
        self.objects = []
        self.scene_orientation = glm.mat4() # turn-table style pose of scene in camera view
        self.scene_matrix = glm.mat4() # scale and pose the scene to fit in the camera view with y up
        

    def initializeGL(self, ctx: mgl.Context ):
        self.ctx = ctx
        self.program = self.ctx.program( vertex_shader=VERTEX_SHADER, fragment_shader=FRAGMENT_SHADER )

        start_time = Usd.TimeCode(self.start_frame)

        for prim in self.stage.Traverse():
            if not prim.IsA(UsdGeom.Mesh): continue

            mesh = UsdGeom.Mesh(prim)
            points_value = mesh.GetPointsAttr().Get(start_time)
            if points_value is None: continue

            point_indices = np.asarray(mesh.GetFaceVertexIndicesAttr().Get(start_time), dtype="i4")
            normals = np.array(mesh.GetNormalsAttr().Get(start_time), dtype="f4")
            positions = np.array(list(points_value), dtype="f4")[point_indices]
            triangles = np.arange(len(point_indices), dtype="u4")

            if len(positions) == 0 or len(triangles) == 0: continue

            vertex_data = np.hstack((positions, normals)).astype("f4")

            vbo = self.ctx.buffer(vertex_data.tobytes())
            ibo = self.ctx.buffer(triangles.tobytes())

            vao = self.ctx.vertex_array(
                self.program,
                [(vbo, "3f 3f", "in_pos", "in_normal")],
                index_buffer=ibo,
                index_element_size=4,
            )

            rng = random.Random(str(prim.GetPath()))
            pastel = colorsys.hsv_to_rgb(rng.random(), 0.45, 0.95)

            self.objects.append({
                "prim": prim,
                "vao": vao,
                "color": pastel,
            })

        self.fit_scene_to_initial_bounds()


    def fit_scene_to_initial_bounds(self):
        """Center and uniformly scale the initial USD world-space bounds."""
        cache = UsdGeom.BBoxCache(
            Usd.TimeCode(self.start_frame),
            [UsdGeom.Tokens.default_, UsdGeom.Tokens.render],
        )
        low = np.array([np.inf, np.inf, np.inf], dtype="f4")
        high = np.array([-np.inf, -np.inf, -np.inf], dtype="f4")
        for obj in self.objects:
            bounds = cache.ComputeWorldBound(obj["prim"]).ComputeAlignedRange()
            if bounds.IsEmpty(): continue
            low = np.minimum(low, np.array(bounds.GetMin(), dtype="f4"))
            high = np.maximum(high, np.array(bounds.GetMax(), dtype="f4"))

        if not np.all(np.isfinite(low)): return

        high[2] = 0
        low[2] = 0
        center = (low + high) * 0.5
        radius = max(np.max(high - low) * 0.5, 1e-5)
        scale = 2.5 / radius # this scales to -1 to 1 roughly
        scale *= 0.1 # additional scale to put int desired size in meters

        # z is up, floor is xy, Want to make y up, so rotate around x by -90 degrees.
        self.scene_matrix = glm.mat4() # identity
        self.scene_matrix = glm.rotate(self.scene_matrix, -np.pi/2, glm.vec3(1,0,0)) # make y up
        self.scene_matrix = glm.scale(self.scene_matrix, glm.vec3(scale, scale, scale))
        self.scene_matrix = glm.translate(self.scene_matrix, -glm.vec3(center[0], center[1], center[2]))


    def current_frame(self):
        span = max(self.end_frame - self.start_frame, 1.0)
        elapsed = time.perf_counter() - self.started_at
        return self.start_frame + (elapsed * self.frames_per_second) % span


    def paintGL(self, P: glm.mat4, V: glm.mat4):        
        self.program["vp"].write( P * V )
        xforms = UsdGeom.XformCache(Usd.TimeCode(self.current_frame()))
        for obj in self.objects:
            T = usd_matrix_to_glm( xforms.GetLocalToWorldTransform(obj["prim"]) )
            model = self.scene_orientation * self.scene_matrix * T            
            self.program["model"].write( model)
            self.program["object_color"].value = obj["color"]
            obj["vao"].render()