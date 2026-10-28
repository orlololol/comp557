# Orlando Qiu 261175512
import polyscope as ps
import polyscope.imgui as psim
import trimesh
import numpy as np
from scipy.spatial.transform import Rotation as R

class _Axis:
    def __init__(self, name: str):
        self.axis = ps.register_point_cloud(name, np.array([[0, 0, 0]]), color=(0,0,0), radius=0.05)
        self.axis.add_vector_quantity("x", np.array([[1, 0, 0]]), color=(1, 0, 0), radius = 0.05, enabled=True, vectortype='ambient')
        self.axis.add_vector_quantity("y", np.array([[0, 1, 0]]), color=(0, 1, 0), radius = 0.05, enabled=True, vectortype='ambient')
        self.axis.add_vector_quantity("z", np.array([[0, 0, 1]]), color=(0, 0, 1), radius = 0.05, enabled=True, vectortype='ambient')
    def set_transform(self, M: np.ndarray):
        self.axis.set_transform(M)
    def set_enabled(self, enabled: bool):
        self.axis.set_enabled(enabled)


_creation_functions = {
    "capsule": trimesh.creation.capsule,
    "icosphere": trimesh.creation.icosphere,
    "box": trimesh.creation.box,
}

def _create_mesh(geom_def: dict):
    params = dict(geom_def) # making a copy doesn't affect the original dictionary
    geom_type = params.pop("type")
    func = _creation_functions.get(geom_type, trimesh.creation.capsule)
    return func(**params)


class Node:
    def __init__(self, definition: dict):
        self.name = definition["name"]
        self.parent_from_local = np.array(definition.get("local_transform", np.identity(4)))        
        self.axis = _Axis(self.name + "_axis")
        self.axis.set_enabled(False) # TODO: Set to false once you're comfortable, or have finished your character design
        self.geometry = _create_mesh(definition.get("geometry"))
        geom_transform = np.array(definition.get("geometry_transform", np.identity(4)))
        self.geometry.apply_transform(geom_transform)
        V = self.geometry.vertices
        F = self.geometry.faces
        self.color = definition.get("color", [0.8, 0.8, 0.8])
        self.transparency = definition.get("transparency", 1.0)
        self.ps_mesh = ps.register_surface_mesh( self.name + "_mesh", V, F, color=self.color, transparency=self.transparency )
        self.children = [Node(child_def) for child_def in definition.get("children", [])]
        self.dofs = definition.get("dofs", ["z"])
        self.dof_values = {dof: 0.0 for dof in self.dofs}
        if "cr" in self.dof_values: self.dof_values["cr"] = self.color[0]
        if "cg" in self.dof_values: self.dof_values["cg"] = self.color[1]
        if "cb" in self.dof_values: self.dof_values["cb"] = self.color[2]
        if "ca" in self.dof_values: self.dof_values["ca"] = self.transparency


    def get_pose(self, pose: dict = None) -> dict:
        if pose is None:
            pose = {}
        pose[self.name] = {dof: float(val) for dof, val in self.dof_values.items()}
        for child in self.children:
            child.get_pose(pose)
        return pose


    def set_pose(self, pose: dict):
        if self.name in pose:
            for dof, val in pose[self.name].items():
                if dof in self.dof_values:
                    self.dof_values[dof] = float(val)
        for child in self.children:
            child.set_pose(pose)

    def set_axis_enabled(self, enabled: bool):
        self.axis.set_enabled(enabled)
        for child in self.children:
            child.set_axis_enabled(enabled)

    def pose_update(self, world_from_parent: np.ndarray):
        # use the self.dofs and the self.dof_values to update the local_pose matrix
        # then compute the transform for the geometry in this node 
        # update self.ps_mesh, self.axis with a call to set_transform()
        # recursively call pose_update on the children with the world_from_local transform
        # build the live joint transform from the slider values.
        local_pose = np.identity(4)
        for dof in self.dofs:
            v = self.dof_values[dof]
            if   dof == "tx": M = translation(v, 0, 0)
            elif dof == "ty": M = translation(0, v, 0)
            elif dof == "tz": M = translation(0, 0, v)
            elif dof == "rx": M = rotx(v)
            elif dof == "ry": M = roty(v)
            elif dof == "rz": M = rotz(v)
            else: continue          # cr cg cb ca arent matrices
            local_pose = local_pose @ M

        # parent frame -> fixed offset -> live joint motion
        world_from_local = world_from_parent @ self.parent_from_local @ local_pose

        self.ps_mesh.set_color((self.dof_values.get("cr", self.color[0]),
                                self.dof_values.get("cg", self.color[1]),
                                self.dof_values.get("cb", self.color[2])))
        self.ps_mesh.set_transparency(self.dof_values.get("ca", self.transparency))

        # tell polyscope where to draw this node
        self.ps_mesh.set_transform(world_from_local)
        self.axis.set_transform(world_from_local)

        # pass this node matrix down so children build on top of it
        for child in self.children:
            child.pose_update(world_from_local)

    def ui_update(self) -> bool:
        changed = False
        if psim.TreeNode(self.name):
            for dof in self.dofs:
                min_val, max_val = (-np.pi, np.pi) 
                if dof.startswith("t"): 
                    min_val, max_val = (-5, 5) 
                if dof.startswith("c"): 
                    min_val, max_val = (0, 1)
                psim.PushItemWidth(psim.GetContentRegionAvail()[0] * 0.5)
                dof_changed, self.dof_values[dof] = psim.SliderFloat(
                    f"{self.name}_{dof}", 
                    self.dof_values[dof], 
                    min_val, 
                    max_val
                )
                psim.PopItemWidth()
                changed |= dof_changed
            for child in self.children:
                changed |= child.ui_update()
            psim.TreePop()
        return changed

def translation(tx, ty, tz):
    tmatrix = np.identity(4)
    tmatrix[:3, 3] = [tx, ty, tz]
    return tmatrix

def rotx(a):
    c, s = np.cos(a), np.sin(a) # cos and sin
    return np.array([[1, 0, 0, 0],
                     [0, c, -s, 0],
                     [0, s, c, 0],
                     [0, 0, 0, 1]])

def roty(a):
    c, s = np.cos(a), np.sin(a) # cos and sin
    return np.array([[c, 0, s, 0],
                     [0, 1, 0, 0],
                     [-s, 0, c, 0],
                     [0, 0, 0, 1]])

def rotz(a):
    c, s = np.cos(a), np.sin(a) # cos and sin
    return np.array([[c, -s, 0, 0],
                     [s, c, 0, 0],
                     [0, 0, 1, 0],
                     [0, 0, 0, 1]])

    