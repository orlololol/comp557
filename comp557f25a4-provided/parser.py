from PIL import Image
import json5 as json
from helperclasses import Material, Light
from camera import Camera
import geometry as geom
from scene import Scene
import trimesh
import numpy as np
import taichi.math as tm
from pyglm import glm

meshes_total_nb_verts = 0  # global counter of total number of mesh vertices in the scene
meshes_total_nb_faces = 0  # global counter of total number of mesh faces in the scene
scene_meshes_verts = np.empty((0, 3), dtype=np.float32)
scene_meshes_faces = np.empty((0, 3), dtype=np.int32)

def load_scene(infile: str, image_scale_factor: float, scene: Scene):
    ''' Load a scene from a json file 
    Args:
        infile (str): path to the scene json file
        image_scale_factor (float): scale factor for image resolution
        scene (scene.Scene): the scene object to load the scene into
    Returns:
        scene.Scene: the loaded scene object

        The json file can define a hierarchy of nodes, but they will be flattend into a list of geometries in the returned scene
        by accumulating the transformation matrices down the hierarchy.  Instances are provided as a convenience for
    '''
    print("Parsing file:", infile)
    f = open(infile)
    data = json.load(f)

    # Loading resolution
    default_resolution = [1280, 720]    
    width = int(image_scale_factor * data.get("resolution", default_resolution)[0])
    height = int(image_scale_factor * data.get("resolution", default_resolution)[1])

    # Loading Anti-Aliasing options    
    jitter = data.get( "AA_jitter", False ) # default to no jitter
    samples = data.get( "AA_samples", 1 ) # default to no supersampling

    # Loading camera
    cam_pos = glm.vec3(data["camera"]["position"])
    cam_lookat = glm.vec3(data["camera"]["lookAt"])
    cam_up = glm.vec3(data["camera"]["up"])
    cam_fovy = data["camera"]["fovy"]
    camera = Camera(width, height, cam_pos, cam_lookat, cam_up, cam_fovy, jitter, samples)

    # Loading ambient light
    ambient = tm.vec3(data.get("ambient", [0.1, 0.1, 0.1])) # set a reasonable default ambient light
    
    # Loading scene lights
    lights = []
    for light in data.get("lights", []):
        l_type = light["type"]
        l_name = light["name"]
        l_colour = tm.vec3(light["colour"])
        l_power = light.get( "power", 1.0 ) # The power scales the specified light colour
        if l_type == "point":
            l_vector = tm.vec3(light["position"])
            l_attenuation = tm.vec3(0,0,1) if "attenuation" not in light else tm.vec3( light["attenuation"] )
            l_type = 1
        elif l_type == "directional":
            l_vector = tm.normalize(tm.vec3(light["direction"]))
            l_attenuation = tm.vec3(0,0,0)
            l_type = 0
            if "attenuation" in light:
                print("Directional light", l_name, "has attenuation, ignoring")
        else:
            print("Unkown light type", l_type, ", skipping initialization")
            continue
        lights.append(Light(l_type, l_colour * l_power, l_vector, l_attenuation))

    # Loading textures
    textures = []
    texture_id_by_name = {}
    texture_max_width = 256 # Set minima here
    texture_max_height = 256
    for i,texture_info in enumerate(data.get("textures", [])):
        tex_name = texture_info["name"]
        tex_filepath = texture_info["filepath"]
        texture_id_by_name[tex_name] = i
        img = Image.open(tex_filepath)
        img = img.convert("RGB")  # ensure image is in RGB format, float data 0 to 1
        img = np.array(img).astype(np.float32) / 255.0
        textures.append( img )
        texture_max_width = max( texture_max_width, img.shape[1] )
        texture_max_height = max( texture_max_height, img.shape[0] )
    # put the textures into a single ndarray with padding to max width and height
    texture_array = np.zeros( (max(1,len(textures)), texture_max_height, texture_max_width, 3), dtype=np.float32 )
    texture_sizes = np.zeros( (max(1,len(textures)), 2), dtype=np.int32 )  # width, height
    for i in range(len(textures)):
        img = textures[i]
        h = img.shape[0]
        w = img.shape[1]
        texture_array[i, 0:h, 0:w, :] = img
        texture_sizes[i, 0] = w
        texture_sizes[i, 1] = h

        

    # Loading materials
    materials = []
    material_id_by_name = {}
    for material in data["materials"]:
        mat_name = material["name"]
        mat_texture_id = -1 if "texture" not in material else texture_id_by_name[ material["texture"] ]
        mat_diffuse = tm.vec3(1,1,1) if "diffuse" not in material else tm.vec3(material["diffuse"])
        mat_specular = tm.vec3(0,0,0) if "specular" not in material else tm.vec3(material["specular"])
        mat_shininess = 0 if "shininess" not in material else material["shininess"]
        mat_reflectivity = 0 if "reflectivity" not in material else material["reflectivity"]
        mat_transparency = 0 if "transparency" not in material else material["transparency"]
        mat_ior = 1.0 if "ior" not in material else material["ior"]
        material_id_by_name[mat_name] = len(materials)  

        materials.append(Material(mat_texture_id, mat_diffuse, mat_specular, mat_shininess, mat_reflectivity, mat_transparency, mat_ior))

    # load geometires
    objects = {"sphere": [],
               "plane": [],
               "box": [],
               "mesh": []}  # lists of loaded object geometries and hierarchy roots
    node_by_name = {}  # dictionary of geometries by name (for instances)

    M_parent = tm.mat4(np.eye(4))  # identity matrix as the initial parent transformation

    for geometry in data["objects"]:
        if geometry["type"] == "node":
            g = load_node(geometry, material_id_by_name, node_by_name, M_parent)
            for obj_type, obj in g:
                objects[obj_type].append(obj)
        elif geometry["type"] == "instance":
            g = load_instance(geometry, node_by_name)
            for obj_type, obj in g:
                objects[obj_type].append(obj)
        else:
            g = load_geometry(geometry, material_id_by_name, M_parent)
            if g is not None:
                objects[geometry["type"]].append(g)
                # check if "name" field exists
                if "name" in geometry:
                    node_by_name[geometry["name"]] = g

    scene.load( camera,  
                ambient, 
                texture_array,
                texture_sizes,
                materials,
                objects,
                lights, 
                scene_meshes_verts, 
                scene_meshes_faces )  

def mat4_glm_to_ti( M_glm: glm.mat4 ) -> tm.mat4:
    return tm.mat4( glm.transpose(M_glm).to_list() )

def load_geometry_transformation_matrix(geometry, M_parent: tm.mat4) -> (tm.mat4, tm.mat4):
    g_pos = glm.vec3(geometry.get("position", [0, 0, 0]))
    g_r = glm.vec3(geometry.get("rotation", [0, 0, 0]))  # not really useful for a sphere...
    g_s = geometry.get("scale", [1, 1, 1])
    if type(g_s) == float or type(g_s) == int:
        g_s = [g_s, g_s, g_s]
    g_s = glm.vec3(g_s)
    scale = glm.scale( g_s )
    rot_x = glm.rotate( glm.radians(g_r.x), glm.vec3(1,0,0) )
    rot_y = glm.rotate( glm.radians(g_r.y), glm.vec3(0,1,0) )
    rot_z = glm.rotate( glm.radians(g_r.z), glm.vec3(0,0,1) )
    translate = glm.translate( g_pos )
    M_parent_glm = glm.mat4( M_parent.to_numpy() )
    M = M_parent_glm * translate * rot_x * rot_y * rot_z * scale
    M_inv = glm.inverse(M)
    return mat4_glm_to_ti(M), mat4_glm_to_ti(M_inv)

def load_geometry(geometry, material_id_by_name, M_parent: tm.mat4 ):
    # NOTE: This is not the prettiest way to track the mesh data
    global meshes_total_nb_verts, meshes_total_nb_faces, scene_meshes_verts, scene_meshes_faces

    # Elements common to all objects: name, type, and material
    type = geometry["type"]
    material_name = geometry.get("material", None)
    if ( material_name is None ):
        print("using first material as default for geometry", geometry.get("name","unnamed") )
        material_id = 0 
    else:
        material_id = material_id_by_name[material_name]

    if type == "sphere":
        g_radius = geometry.get("radius",1)
        M, M_inv = load_geometry_transformation_matrix(geometry, M_parent)
        return geom.Sphere(material_id, g_radius, M, M_inv)
    elif type == "plane":
        g_normal = tm.vec3(geometry.get("normal",[0,1,0]))
        M, M_inv = load_geometry_transformation_matrix(geometry, M_parent)
        return geom.Plane(material_id, g_normal, M, M_inv)
    elif type == "box":
        minpos = tm.vec3(geometry.get("min",[-1,-1,-1]))
        maxpos = tm.vec3(geometry.get("max",[1,1,1]))
        M, M_inv = load_geometry_transformation_matrix(geometry, M_parent)
        return geom.AABox(material_id, minpos, maxpos, M, M_inv)
    elif type == "mesh":
        g_path = geometry["filepath"]
        M, M_inv = load_geometry_transformation_matrix(geometry, M_parent)
        mesh = trimesh.load_mesh(g_path)
        verts = mesh.vertices
        faces = mesh.faces

        scene_meshes_verts = np.resize(scene_meshes_verts, (meshes_total_nb_verts + len(verts), 3))
        scene_meshes_faces = np.resize(scene_meshes_faces, (meshes_total_nb_faces + len(faces), 3))
        # NOTE: These should really be vectorized!
        for i in range(len(verts)):
            scene_meshes_verts[meshes_total_nb_verts + i] = np.array((verts[i, 0], verts[i, 1], verts[i, 2]))
        for i in range(len(faces)):
            scene_meshes_faces[meshes_total_nb_faces + i] = np.array((faces[i, 0] + meshes_total_nb_verts,
                                                                      faces[i, 1] + meshes_total_nb_verts,
                                                                      faces[i, 2] + meshes_total_nb_verts))
        # NOTE: an opportunity to transform the verts of the mesh rather than transforming the ray later
        bmin = np.min(verts, axis=0)
        bmax = np.max(verts, axis=0)
        bbox_min = tm.vec3(bmin[0], bmin[1], bmin[2])
        bbox_max = tm.vec3(bmax[0], bmax[1], bmax[2])
        mesh = geom.Mesh(material_id, meshes_total_nb_faces, len(faces), M, M_inv, bbox_min, bbox_max)
        meshes_total_nb_verts += len(verts)
        meshes_total_nb_faces += len(faces)
        return mesh
    else:
        print("Unkown object type", type, ", skipping initialization")
        return None
    
def load_node(geometry, material_id_by_name, node_by_name, M_parent: tm.mat4 ):
    M, M_inv = load_geometry_transformation_matrix(geometry, M_parent)    
    # For this node, keep a list of all the childern objects
    objects = []
    node_by_name[geometry["name"]] = []
    
    for child in geometry["children"]:
        if child["type"] != "node" and child["type"] != "instance":
            g = load_geometry(child, material_id_by_name, M)
            objects.append((child["type"], g))  # each geometry is stored as a tuple (type, object)
            node_by_name[geometry["name"]] += objects
        elif child["type"] == "node":
            objects += load_node(child, material_id_by_name, node_by_name, M)
            node_by_name[geometry["name"]] += objects
        elif child["type"] == "instance":
            print("Instances are not allowed inside nodes, must be defined at root level")
        else:
            print("Unkown object type", child["type"], ", skipping initialization")

    return objects

def load_instance(geometry, node_by_name):
    # instances are loaded off the root, so will have an identiy matrix as parent
    M, M_inv = load_geometry_transformation_matrix(geometry, tm.mat4( np.eye(4) ) ) 
    objects = []
    node = node_by_name[geometry["ref"]]
    for obj_type, obj in node:
        if obj is not None:
            if obj_type == "sphere":
                new_obj = geom.Sphere(obj.material_id, obj.position, obj.radius, M @ obj.M, obj.M_inv @ M_inv )                                      
            elif obj_type == "plane":
                new_obj = geom.Plane(obj.material_id, obj.position, obj.normal, M @ obj.M, obj.M_inv @ M_inv )            
            elif obj_type == "box":
                new_obj = geom.AABox(obj.material_id, obj.minpos, obj.maxpos, M @ obj.M, obj.M_inv @ M_inv )  
            elif obj_type == "mesh":
                new_obj = geom.Mesh(obj.material_id, obj.vert_start, obj.nb_verts, obj.face_start, obj.nb_faces,  M @ obj.M, obj.M_inv @ M_inv )                          
            objects.append((obj_type, new_obj))

    return objects