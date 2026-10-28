import numpy as np
from pygltflib import GLTF2
from scipy.spatial.transform import Rotation as R
from scipy.spatial.transform import Slerp

class SkinningEngine:
    def __init__(self, gltf: GLTF2):
        # 1. Load the glTF model structure
        self.gltf = gltf
        self.binary_blob = self.gltf.binary_blob()
        
        # Assume the file contains at least one skin
        self.skin = self.gltf.skins[0]
        self.joints = self.skin.joints  # Map: Joint index -> glTF Node ID
        
        # 2. Extract Inverse Bind Matrices
        self.inverse_bind_matrices = self._load_inverse_bind_matrices()
        
        # Cache local node transformations so we can fall back on them if unanimated
        self.local_nodes = {}
        self._cache_default_node_transforms()
        self._sampler_cache = {}

    def _load_inverse_bind_matrices(self):
        """Extracts the 4x4 matrix array from binary glTF accessors."""
        accessor = self.gltf.accessors[self.skin.inverseBindMatrices]
        bv = self.gltf.bufferViews[accessor.bufferView]
        
        # Extract slices directly out of the GLB byte stream
        start = (bv.byteOffset or 0) + (accessor.byteOffset or 0)
        length = accessor.count * 16 * 4  # 16 floats per mat4 * 4 bytes per float
        raw_bytes = self.binary_blob[start:start + length]
        
        # glTF is column-major, so transpose each matrix into the usual M[row, col] layout
        return np.frombuffer(raw_bytes, dtype='f4').reshape(accessor.count, 4, 4).transpose(0, 2, 1)

    def _cache_default_node_transforms(self):
        """Caches default Translation, Rotation (Quaternion), and Scale per node."""
        for i, node in enumerate(self.gltf.nodes):
            if node.matrix:
                m = np.array(node.matrix, dtype='f4').reshape(4, 4).T  # column-major -> M[row, col]
                t = m[:3, 3].copy()
                s = np.linalg.norm(m[:3, :3], axis=0)
                r = R.from_matrix(m[:3, :3] / s).as_quat()
            else:
                t = np.array(node.translation if node.translation else [0.0, 0.0, 0.0], dtype='f4')
                r = np.array(node.rotation if node.rotation else [0.0, 0.0, 0.0, 1.0], dtype='f4') # xyzw
                s = np.array(node.scale if node.scale else [1.0, 1.0, 1.0], dtype='f4')
            self.local_nodes[i] = {'t': t, 'r': r, 's': s}

    def _read_accessor_data(self, accessor_idx):
        """Helper to unpack an individual channel data array (timestamps or vector states)."""
        accessor = self.gltf.accessors[accessor_idx]
        bv = self.gltf.bufferViews[accessor.bufferView]
        start = (bv.byteOffset or 0) + (accessor.byteOffset or 0)
        
        # Determine shapes based on data types
        elements = 1 if accessor.type == "SCALAR" else (3 if accessor.type == "VEC3" else 4)
        length = accessor.count * elements * 4
        
        data = np.frombuffer(self.binary_blob[start:start+length], dtype='f4')
        return data.reshape(accessor.count, elements)

    def sample_animation(self, animation_idx, time):
        """Samples the animation tracks and overwrites node states."""
        if not self.gltf.animations:
            return
            
        anim = self.gltf.animations[animation_idx]
        
        for channel in anim.channels:
            target_node = channel.target.node
            path = channel.target.path  # "translation", "rotation", or "scale"
            sampler = anim.samplers[channel.sampler]
            
            key = (animation_idx, channel.sampler)
            if key not in self._sampler_cache:
                timestamps = self._read_accessor_data(sampler.input).flatten()
                keyframes = self._read_accessor_data(sampler.output)
                if sampler.interpolation == "CUBICSPLINE":
                    keyframes = keyframes[1::3]  # keep values only; tangents are ignored (linear approximation)
                self._sampler_cache[key] = (timestamps, keyframes)
            timestamps, keyframes = self._sampler_cache[key]
            
            # Wrap around the loop, allowing a non-zero first timestamp
            t_start, t_end = timestamps[0], timestamps[-1]
            lookup_time = t_start + (time - t_start) % (t_end - t_start) if t_end > t_start else t_start

            # Locate time index mapping positions
            idx = np.searchsorted(timestamps, lookup_time) - 1
            idx = max(0, min(idx, len(timestamps) - 2))
            
            # Compute interpolation factor (STEP holds the previous keyframe)
            t0, t1 = timestamps[idx], timestamps[idx+1]
            factor = np.clip((lookup_time - t0) / (t1 - t0), 0.0, 1.0)
            if sampler.interpolation == "STEP":
                factor = 0.0
            
            # Blend current properties linearly or via spherical quaternions
            if path == "translation":
                self.local_nodes[target_node]['t'] = (1 - factor) * keyframes[idx] + factor * keyframes[idx+1]
            elif path == "scale":
                self.local_nodes[target_node]['s'] = (1 - factor) * keyframes[idx] + factor * keyframes[idx+1]
            elif path == "rotation":
                slerp = Slerp([0, 1], R.from_quat(keyframes[idx:idx+2]))
                self.local_nodes[target_node]['r'] = slerp([factor])[0].as_quat()

    def get_joint_matrices(self):
        """
        Traverses the graph downward to build global space transformations,
        then offsets them via Inverse Bind Matrices.
        """
        global_transforms = {}

        def compute_global(node_idx, parent_matrix):
            # 1. Build local matrix from TRS state
            node_data = self.local_nodes[node_idx]
            local_mat = np.identity(4, dtype='f4')
            
            # Apply Scale, Rotation (via scipy matrix), and Translation
            mat_rot = R.from_quat(node_data['r']).as_matrix()
            local_mat[:3, :3] = mat_rot * node_data['s']
            local_mat[:3, 3] = node_data['t']
            
            # 2. Global Transform = Parent Transform x Local Transform
            global_mat = parent_matrix @ local_mat
            global_transforms[node_idx] = global_mat
            
            # 3. Recursively propagate transformation downstream to children
            node_obj = self.gltf.nodes[node_idx]
            if node_obj.children:
                for child_idx in node_obj.children:
                    compute_global(child_idx, global_mat)

        # Start traversal from scene roots (identity parents)
        root_nodes = self.gltf.scenes[self.gltf.scene or 0].nodes
        for root in root_nodes:
            compute_global(root, np.identity(4, dtype='f4'))

        # Combine calculated states with static IBM bounds
        final_matrices = []
        for i, joint_node_idx in enumerate(self.joints):
            current_global = global_transforms[joint_node_idx]
            inv_bind = self.inverse_bind_matrices[i]
            
            # FinalBoneTransform = JointGlobal x InverseBindMatrix (mesh node transform is ignored for skinned meshes)
            bone_matrix = current_global @ inv_bind
            final_matrices.append(bone_matrix)
            
        return np.array(final_matrices, dtype='f4')
