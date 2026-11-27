from helperclasses import Ray, Intersection, Material, changeRayFrame, getRayPoint, changeIntersectFrame

import taichi as ti
import taichi.math as tm

EPSILON = 10 ** (-5)

@ti.dataclass
class Sphere:
    material_id: int
    radius: float
    M: tm.mat4
    M_inv: tm.mat4

@ti.func
def intersectSphere(sphere: Sphere, ray: Ray, t_min: float, t_max: float) -> Intersection:
    ''' Ray-sphere intersection  
    Args:
        sphere (Sphere): sphere to intersect with
        ray (Ray): ray in world space
        t_min (float): minimum t value for valid intersection
        t_max (float): maximum t value for valid intersection
    Returns:
        Intersection: intersection data (is_hit, t, normal, point, material)
        
        Note, nominally the intersection will be computed with the sphere
        at the origin with the specified radius.  For a sphere away from 
        the origin, the M and M_inv members of the Sphere class must be used to 
        transform the ray into the sphere's local frame for intersection, and
        likewise used to transform the resulting intersection data back to world space
        (TODO: See Objective ?).
    '''

    hit = Intersection() # default is no intersection (is_hit = False)
    ray = changeRayFrame(ray, sphere.M_inv) # transform ray to local space of sphere

    # Objective 2: Implement ray-sphere intersection

    a = tm.dot(ray.direction, ray.direction)
    b = 2 * tm.dot(ray.direction, ray.origin)
    c = tm.dot(ray.origin, ray.origin) - sphere.radius * sphere.radius
    discriminant = b * b - 4 * a * c
    if discriminant >= 0:
        
        t1 = (-b - ti.sqrt(discriminant)) / (2 * a)
        t2 = (-b + ti.sqrt(discriminant)) / (2 * a)
        if t1 >= t_min and t1 <= t_max:
            hit.is_hit = True
            hit.t = t1
        elif t2 >= t_min and t2 <= t_max:
            hit.is_hit = True
            hit.t = t2

        if hit.is_hit:
            hit.position = getRayPoint(ray, hit.t)
            hit.normal = tm.normalize(hit.position)
            hit.mat = sphere.material_id

    if hit.is_hit:
        hit = changeIntersectFrame(hit, sphere.M, sphere.M_inv) # transform intersection back to world space

    return hit



@ti.dataclass
class Plane:
    material_id: int    
    normal: tm.vec3         # only plane normal (goes through origin in local space)
    M: tm.mat4              # transformation matrix to world space  
    M_inv: tm.mat4          # inverse transformation matrix to local space  

@ti.func
def intersectPlane(plane: Plane, ray: Ray, t_min: float, t_max: float) -> Intersection:
    ''' Ray-plane intersection
    Args:
        plane (Plane): plane to intersect with
        ray (Ray): ray in world space
        t_min (float): minimum t value for valid intersection
        t_max (float): maximum t value for valid intersection
    Returns:
        Intersection: intersection data (is_hit, t, normal, point, material)
        
        Note, nominally the intersection will be computed with the plane
        at the origin with the specified normal.  For a plane away from 
        the origin, the M and M_inv members of the Plane class must be used to 
        transform the ray into the plane's local frame for intersection, and
        likewise used to transform the resulting intersection data back to world space.

        Note, the plane can have two materials (when two_materials is true) which
        are applied in a checkerboard pattern in the plane's local XZ plane.
    '''

    hit = Intersection() # default is no intersection (is_hit = False)

    # Objective 5: Implement ray-plane intersection
    ray = changeRayFrame(ray, plane.M_inv) # transform ray to local space of plane

    n = plane.normal
    denom = tm.dot(n, ray.direction)

    if abs(denom) > EPSILON:  # Check if the ray is not parallel to the plane
        t = -tm.dot(n, ray.origin) / denom
        if t >= t_min and t <= t_max:
            hit.is_hit = True
            hit.t = t
            hit.position = getRayPoint(ray, hit.t)
            hit.normal = n
            hit.mat = plane.material_id
            hit.texture_coords = tm.vec3(hit.position.x, hit.position.z, 0.0)  # local x, z -> (u,v) 

    if hit.is_hit:
        hit = changeIntersectFrame(hit, plane.M, plane.M_inv) # transform intersection back to world space

    return hit


@ti.dataclass
class AABox:
    material_id: int
    minpos: tm.vec3     # lower left corner
    maxpos: tm.vec3     # upper right corner
    M: tm.mat4
    M_inv: tm.mat4

@ti.func
def intersectAABox(aabox: AABox, ray: Ray, t_min: float, t_max: float) -> Intersection:
    hit = Intersection() # default is no intersection (is_hit = False)

    # Objective 7: Implement ray-box intersection
    ray = changeRayFrame(ray, aabox.M_inv) # transform ray to local space of box

    # Calculate intersection with the box
    t0 = (aabox.minpos - ray.origin) / ray.direction
    t1 = (aabox.maxpos - ray.origin) / ray.direction

    # Ensure t0 is the smaller value and t1 is the larger value
    t0, t1 = ti.min(t0, t1), ti.max(t0, t1)

    # Find the intersection with the box
    t_near = ti.max(t0.x, t0.y, t0.z)
    t_far = ti.min(t1.x, t1.y, t1.z)

    if t_near <= t_far:
        if t_min <= t_near <= t_max:
            hit.t = max(t_near, t_min)
            hit.is_hit = True
        elif t_min <= t_far <= t_max:
            hit.t = max(t_far, t_min)
            hit.is_hit = True

    if hit.is_hit:
        hit.position = getRayPoint(ray, hit.t)
        p = hit.position
        # determine which face was hit to compute the normal
        epsilon = 1e-5
        n = tm.vec3(0, 0, 0)
        for i in range(3): # i = 0(x), 1(y), 2(z)
            if abs(p[i] - aabox.minpos[i]) < epsilon:
                n[i] = -1.0 # on the min face
            elif abs(p[i] - aabox.maxpos[i]) < epsilon:
                n[i] = 1.0 # on the max face
        hit.normal = n
        hit.mat = aabox.material_id
        hit = changeIntersectFrame(hit, aabox.M, aabox.M_inv) # transform intersection back to world space

    return hit


@ti.dataclass
class Mesh:
    material_id: int
    faces_ids_start: ti.i32  # index of the first face in the global face array
    faces_ids_count: ti.i32  # number of faces in this mesh
    M: tm.mat4
    M_inv: tm.mat4
    minpos_bbox: tm.vec3 # lower left corner
    maxpos_bbox: tm.vec3 # upper right corner

@ti.func
def intersectMesh(mesh: Mesh,                  # data for this mesh (start face and number of faces, etc.)
                  meshes_verts: ti.template(), # all vertices (for all meshes)
                  meshes_faces: ti.template(), # all faces (for all meshes)
                  ray: Ray,
                  t_min: float,
                  t_max: float
) -> Intersection:
    
    out_intersect = Intersection() # default is no intersection (is_hit = False)

    mesh_bbox = AABox(mesh.material_id, mesh.minpos_bbox, mesh.maxpos_bbox, mesh.M, mesh.M_inv)
    bbox_intersect = intersectAABox(mesh_bbox, ray, t_min, t_max)
    if bbox_intersect.is_hit:
        # Objective 8: Implement ray-mesh intersection
        ray = changeRayFrame(ray, mesh.M_inv) # transform ray to local space of mesh
        # for each face in mesh's range
        for i in range(mesh.faces_ids_start, mesh.faces_ids_start + mesh.faces_ids_count):
            face = meshes_faces[i]
            v0 = meshes_verts[face.x]
            v1 = meshes_verts[face.y]
            v2 = meshes_verts[face.z]

            # Cramer's rule
            col1 = v0 - v1
            col2 = v0 - v2
            col3 = ray.direction
            rhs = v0 - ray.origin

            detA = tm.dot(col1, tm.cross(col2, col3))
            if abs(detA) < EPSILON:
                continue  # Ray is parallel to the triangle

            beta = (tm.dot(rhs, tm.cross(col2, col3)) / detA)
            gamma = (tm.dot(col1, tm.cross(rhs, col3)) / detA)
            t = (tm.dot(col1, tm.cross(col2, rhs)) / detA)

            # reject if the hit is outside the triangle or range
            if beta < 0 or beta > 1 - gamma:
                continue
            if gamma < 0 or gamma > 1:
                continue
            if t < t_min or t > t_max:
                continue

            if t_min <= t <= t_max and (not out_intersect.is_hit or t < out_intersect.t):
                out_intersect.is_hit = True
                out_intersect.t = t
                out_intersect.position = getRayPoint(ray, t)
                out_intersect.normal = tm.normalize(tm.cross(col1, col2))
                out_intersect.mat = mesh.material_id
                out_intersect.texture_coords = tm.vec3(beta, gamma, 0.0)  # barycentric coordinates as texture coords

    if out_intersect.is_hit:
        out_intersect = changeIntersectFrame(out_intersect, mesh.M, mesh.M_inv) # transform intersection back to world space
    return out_intersect
