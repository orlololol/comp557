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

    # TODO: Objective 2: Implement ray-sphere intersection

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

    # TODO: Objective 5: Implement ray-plane intersection


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

    # TODO: Objective 7: Implement ray-box intersection


    return hit


@ti.dataclass
class Mesh:
    material_id: int
    faces_ids_start: ti.i32  # index of the first face in the global face array
    faces_ids_count: ti.i32  # number of faces in this mesh
    M: tm.mat4
    M_inv: tm.mat4

@ti.func
def intersectMesh(mesh: Mesh,                  # data for this mesh (start face and number of faces, etc.)
                  meshes_verts: ti.template(), # all vertices (for all meshes)
                  meshes_faces: ti.template(), # all faces (for all meshes)
                  ray: Ray,
                  t_min: float,
                  t_max: float
) -> Intersection:
    
    out_intersect = Intersection() # default is no intersection (is_hit = False)

    # TODO: Objective 8: Implement ray-mesh intersection


    return out_intersect
