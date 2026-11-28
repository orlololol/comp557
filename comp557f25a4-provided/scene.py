import geometry as geom
from helperclasses import Ray, Intersection, Light, Material
from camera import Camera

import numpy as np

import taichi as ti
import taichi.math as tm

shadow_epsilon = 10**(-2)
MAX_BOUNCES = 5

@ti.data_oriented
class Scene:
    def __init__( self ):
        ## Allocate empty fields with default sizes    
        # Taichi does not accept a zero-length field, so we create a field of size at least one if the list is empty.
        # Moreover, different sized fields will cause recompilation when used in kernels, so minimums are set to try
        # to ensure kernel reuse.  Finally, the count fields to track the number of objects must be put into fields
        # to hide the value from the hash used for compilation caching. 
        
        self.nb_spheres = ti.field(dtype=int, shape=())        
        self.spheres = geom.Sphere.field(shape=(10))
        self.nb_planes = ti.field(dtype=int, shape=())
        self.planes = geom.Plane.field(shape=(1))
        self.nb_aaboxes = ti.field(dtype=float, shape=())
        self.aaboxes = geom.AABox.field(shape=(30))
        self.nb_meshes = ti.field(dtype=int, shape=())
        self.meshes = geom.Mesh.field(shape=(5))
        self.nb_lights = ti.field(dtype=int, shape=())
        self.lights = Light.field(shape=(5))
        self.meshes_verts = ti.Vector.field(3, shape=(10000), dtype=float)
        self.meshes_faces = ti.Vector.field(3, shape=(10000), dtype=int)

        self.iter_counter = ti.field(dtype=float, shape=())

        # Sizes ideally should match exactly the numpy stuff we plan to load in.
        self.texture_data = ti.Vector.field(3, dtype=ti.f32, shape=(1,256,256))
        self.texture_sizes = ti.field(ti.i32, shape=(1,2)) # could be a vector field instead

        self.material_field = Material.field(shape=(20))

        self.image = ti.Vector.field( n=3, dtype=float, shape=(512, 700) )


    def load(
            self,
            camera: Camera,
            ambient: tm.vec3,
            texture_data: np.array, # NxWxHx3
            texture_sizes: np.array,
            materials,
            objects,
            lights,
            meshes_verts: np.array,
            meshes_faces: np.array,
    ):
        self.camera = camera
        self.ambient = ambient  # ambient lighting
        
        print("Texture data shape:", texture_data.shape, "field shape:", self.texture_data.shape)

        if self.texture_data.shape[2] != texture_data.shape[2] or self.texture_data.shape[1] != texture_data.shape[1] or self.texture_data.shape[0] < texture_data.shape[0]:
            print("Warning: reallocating texture_data field to match loaded textures")
            # fix from template
            self.texture_data = ti.Vector.field(3, dtype=ti.f32, shape=(texture_data.shape[0], texture_data.shape[1], texture_data.shape[2]))
        print("Texture data shape:", texture_data.shape, "field shape:", self.texture_data.shape)
        self.texture_data.from_numpy(texture_data)

        print("now doing texture sizes")
        if self.texture_sizes.shape[0] != texture_sizes.shape[0]:
            print("Warning: reallocating texture_sizes field to match loaded number of textures")
            self.texture_sizes = ti.field(ti.i32, shape=texture_sizes.shape)
        self.texture_sizes.from_numpy(texture_sizes)

        print("Doing materials")
        if len(materials) > self.material_field.shape[0]:
            print("Warning: reallocating material_field to larger size")
            self.material_field = Material.field(shape=(len(materials)))
        for i,m in enumerate(materials): self.material_field[i] = m

        self.nb_spheres[None] = len(objects["sphere"])        
        if self.nb_spheres[None] > self.spheres.shape[0]:
            print("Warning: reallocating spheres field to larger size")
            self.spheres = geom.Sphere.field(shape=(self.nb_spheres[None]))
        for i,s in enumerate(objects["sphere"]): self.spheres[i] = s
        
        self.nb_planes[None] = len(objects["plane"])
        if self.nb_planes[None] > self.planes.shape[0]:
            print("Warning: reallocating planes field to larger size")
            self.planes = geom.Plane.field(shape=(self.nb_planes[None]))
        for i,p in enumerate(objects["plane"]): self.planes[i] = p

        self.nb_aaboxes[None] = len(objects["box"])
        if self.nb_aaboxes[None] > self.aaboxes.shape[0]:
            print("Warning: reallocating aaboxes field to larger size")
            self.aaboxes = geom.AABox.field(shape=(self.nb_aaboxes[None]))
        for i,a in enumerate(objects["box"]): self.aaboxes[i] = a

        self.nb_meshes[None] = len(objects["mesh"])
        if self.nb_meshes[None] > self.meshes.shape[0]:
            print("Warning: reallocating meshes field to larger size")
            self.meshes = geom.Mesh.field(shape=(self.nb_meshes[None]))
        for i,m in enumerate(objects["mesh"]): self.meshes[i] = m

        print("done with geometry")     

        self.nb_lights[None] = len(lights)
        self.lights = Light.field(shape=max(5, self.nb_lights[None]))
        if self.nb_lights[None] > self.lights.shape[0]:
            print("Warning: reallocating lights field to larger size")
            self.lights = Light.field(shape=(self.nb_lights[None]))
        # TODO: Does this work?  it seems preferable to the for enumerate loop
        #self.lights.copy_from(lights)
        for i,l in enumerate(lights): self.lights[i] = l

        print("done with lights")

        # TODO: should check that the fields are actually big enough!
        # fix from template
        if self.meshes_verts.shape[0] != meshes_verts.shape[0] and meshes_verts.shape[0] > 0:
            print("Warning: reallocating meshes_verts field to larger size")
            self.meshes_verts = ti.Vector.field(3, shape=(meshes_verts.shape[0]), dtype=float)
        # fix from template
        if self.meshes_faces.shape[0] != meshes_faces.shape[0] and meshes_faces.shape[0] > 0:
            print("Warning: reallocating meshes_faces field to larger size")
            self.meshes_faces = ti.Vector.field(3, shape=(meshes_faces.shape[0]), dtype=int)
        if meshes_verts.shape[0] > 0: # only copy if there actually are meshes!
            self.meshes_verts.from_numpy(meshes_verts)
            self.meshes_faces.from_numpy(meshes_faces)

        if self.image.shape[0] != self.camera.width or self.image.shape[1] != self.camera.height:
            print("Warning: reallocating image field to match camera dimensions")
            self.image = ti.Vector.field( n=3, dtype=float, shape=(self.camera.width, self.camera.height) )

        self.iter_counter[None] = 0.0

        print("Scene loaded into Scene object.")

    @ti.kernel
    def render( self ):
        self.iter_counter[None] += 1.0
        for x,y in ti.ndrange(self.camera.width, self.camera.height):
            if (y == x) and x%10 == 0: print(".",end='')
            ray = self.camera.create_ray( x, y )
            sample_colour = tm.vec3(0, 0, 0) # background colour
            throughput = 1.0
            t_min = 0.0 # 0 from the camera ray from step4
            for bounce in range(MAX_BOUNCES): # max bounces
                hit = self.intersect_scene(ray, t_min, float('inf'))
                if not hit.is_hit: break # no more intersections, so break out of the loop
                sample_colour += throughput * self.compute_shading(hit, ray)
                mat = self.material_field[hit.mat]
                new_dir = tm.vec3(0.0, 0.0, 0.0)
                keep_going = False
                if mat.transparency > 0: # refraction
                    throughput *= mat.transparency
                    n = hit.normal
                    eta = 1.0 / mat.ior # entering: air -> material
                    if tm.dot(ray.direction, n) > 0: # exiting: material -> air
                        n = -n
                        eta = mat.ior
                    new_dir = tm.refract(ray.direction, n, eta)
                    if tm.length(new_dir) < 1e-6: # total internal reflection
                        new_dir = tm.reflect(ray.direction, n)
                    keep_going = True
                elif mat.reflectivity > 0: # mirror reflection
                    throughput *= mat.reflectivity
                    new_dir = tm.reflect(ray.direction, hit.normal) # reflect the ray direction
                    keep_going = True
                if not keep_going or throughput < 0.01: break # terminate if not reflective or refractive or throughput is too low
                ray.origin = hit.position
                ray.direction = tm.normalize(new_dir)
                t_min = shadow_epsilon # set t_min for the next intersection test

            self.image[x,y] += (sample_colour - self.image[x,y]) / self.iter_counter[None] 
        print() # end of line after one dot per 10 rows


    @ti.func
    def intersect_scene(self, ray: Ray, t_min: float, t_max: float) -> Intersection:
        best = Intersection() # default is no intersection (is_hit = False)        
        ti.loop_config(serialize=True) 
        for i in range(self.nb_spheres[None]):
            hit = geom.intersectSphere(self.spheres[i], ray, t_min, t_max )
            if hit.is_hit: best = hit; t_max = hit.t # keep best hit only
        ti.loop_config(serialize=True) 
        for i in range(self.nb_planes[None]):
            hit = geom.intersectPlane(self.planes[i], ray, t_min, t_max )
            if hit.is_hit: best = hit; t_max = hit.t                
        ti.loop_config(serialize=True) 
        for i in range(self.nb_aaboxes[None]):
            hit = geom.intersectAABox(self.aaboxes[i], ray, t_min, t_max )
            if hit.is_hit: best = hit; t_max = hit.t
        ti.loop_config(serialize=True) 
        for i in range(self.nb_meshes[None]):
            hit = geom.intersectMesh(self.meshes[i], self.meshes_verts, self.meshes_faces, ray, t_min, t_max)
            if hit.is_hit: best = hit; t_max = hit.t
        return best


    @ti.func
    def compute_shading(self, intersect: Intersection, ray: Ray) -> tm.vec3:
        sample_colour = tm.vec3(0, 0, 0)

        material = self.material_field[intersect.mat]

        kd = material.diffuse
        if material.texture_id != -1:
            u = intersect.texture_coords.x
            v = intersect.texture_coords.y
            kd *= self.getTextureColour( material.texture_id, u, v )

        # Ambient shading
        sample_colour += self.ambient * kd

        intersect.normal = tm.normalize(intersect.normal)

        ti.loop_config(serialize=True) 
        for l in range(self.nb_lights[None]):
            
            # Objective 3: Implement diffuse and specular shading
            light = self.lights[l]
            light_dir = tm.vec3(0,0,0)
            dist = 0.0
            attenuation = 1.0
            t_max = float('inf')
            # compute the direction from the intersection point to the light source
            if light.ltype == 1: # point light
                # for area light aim at a random point on the light's sphere (radius 0 = the centre)
                z = 2.0 * ti.random() - 1.0
                phi = 2.0 * tm.pi * ti.random()
                rxy = ti.sqrt(1.0 - z * z)
                light_pos = light.vector + light.radius * tm.vec3(rxy * ti.cos(phi), rxy * ti.sin(phi), z)
                to_light = light_pos - intersect.position
                dist = tm.length(to_light)
                light_dir = tm.normalize(to_light)
                q = light.attenuation.x # quadratic term
                lin = light.attenuation.y # linear term
                c = light.attenuation.z # constant term
                attenuation = 1.0 / (q * dist * dist + lin * dist + c) # quadratic attenuation
                t_max = dist

            else: # directional light
                light_dir = light.vector
                attenuation = 1.0
                t_max = float('inf')

            # Objective 6: Implement shadow rays
            shadow_ray = Ray(intersect.position, light_dir)
            shadow_hit = self.intersect_scene(shadow_ray, shadow_epsilon, t_max)

            if not shadow_hit.is_hit:
                # if shadow ray dont hit anything, compute diffuse and specular shading
                n_dot_l = tm.dot(intersect.normal, light_dir)
                h = tm.normalize(light_dir - ray.direction)
                n_dot_h = max(0.0, tm.dot(intersect.normal, h))
                ks = material.specular
                alpha = material.shininess

                if n_dot_l > 0:
                    diffuse = kd * n_dot_l * light.colour
                    specular = ks * (n_dot_h ** alpha) * light.colour
                    sample_colour += attenuation * (diffuse + specular)

        return sample_colour
    
    @ti.func
    def getTextureColour( self, texture_id: int, u: float, v: float ) -> tm.vec3:
        tex_width = self.texture_sizes[texture_id, 0]
        tex_height = self.texture_sizes[texture_id, 1]
        u = u - tm.floor(u) # wrap!
        v = v - tm.floor(v)
        x = ti.cast(u * tex_width, ti.i32) % tex_width
        y = ti.cast(v * tex_height, ti.i32) % tex_height
        return self.texture_data[texture_id,y,x] # or is it x,y?  
    