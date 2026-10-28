from pygltflib import GLTF2
import moderngl as mgl
from pathlib import Path
import glm
import numpy as np
from scipy.spatial.transform import Rotation as R


class Asset:
	def __init__(self, gltf: GLTF2, ctx):
		self.gltf = gltf
		self.ctx = ctx
		current_dir = Path(__file__).parent
		self.prog_LBS = ctx.program(
			vertex_shader=open(current_dir / 'glsl' / 'vertLBS.glsl').read(),
			fragment_shader=open(current_dir / 'glsl' / 'frag.glsl').read())

		self.prog_DQS = ctx.program(
			vertex_shader=open(current_dir / 'glsl' / 'vertDQS.glsl').read(),
			fragment_shader=open(current_dir / 'glsl' / 'frag.glsl').read())

		# --- Unpack the glTF data as both bytes for buffers and numpy arrays for processing ---

		# assuming the first mesh and first primitive for simplicity
		primitive = self.gltf.meshes[0].primitives[0]
		self.blob = self.gltf.binary_blob()

		# define maps from glTF component types to sizes, numpy dtypes, and ModernGL formats
		index_size_map = {
			5121: 1,  # UNSIGNED_BYTE
			5123: 2,  # UNSIGNED_SHORT
			5125: 4,  # UNSIGNED_INT
		}
		np_size_map = {
			5121: np.uint8,   # UNSIGNED_BYTE
			5123: np.uint16,  # UNSIGNED_SHORT
			5125: np.uint32,  # UNSIGNED_INT
		}	
		type_map = { 
			5121: '4u1', 	# glsl uvec4 attribute with buffer containing 4 unsigned bytes per vertex 
			5123: '4u2', 	# glsl uvec4 attribute with buffer containing 4 unsigned shorts per vertex
			5125: '4u4' 	# glsl uvec4 attribute with buffer containing 4 unsigned ints per vertex
		} 
		
		# Extract raw bytes for face indices, and convert to numpy array of shape (num_faces, 3) 
		index_accessor = self.gltf.accessors[primitive.indices]
		index_bytes = self.get_accessor_bytes(primitive.indices)		
		index_element_size = index_size_map[index_accessor.componentType]
		self.F = np.frombuffer(index_bytes, dtype=np_size_map[index_accessor.componentType]).reshape(-1, 3)

		# Extract raw bytes for vertex positions, and convert to numpy array of shape (num_vertices, 3)
		pos_bytes = self.get_accessor_bytes(primitive.attributes.POSITION)
		self.V = np.frombuffer(pos_bytes, dtype=np.float32).reshape(-1, 3)

		# Extract raw bytes for vertex normals 
		norm_bytes = self.get_accessor_bytes(primitive.attributes.NORMAL)

		# Extract raw bytes for vertex weights and joints, and convert to numpy arrays with space for 8 incluences
		max_influences = 8		
		joints_accessor = self.gltf.accessors[primitive.attributes.JOINTS_0]
		self.J = np.zeros((self.V.shape[0], max_influences), dtype=np_size_map[joints_accessor.componentType])
		self.W = np.zeros((self.V.shape[0], max_influences), dtype=np.float32)
		self.W_gradients = np.zeros((self.V.shape[0], max_influences, 3), dtype=np.float32)

		joint_bytes = self.get_accessor_bytes(primitive.attributes.JOINTS_0)
		self.J[:,:4] = np.frombuffer(joint_bytes, dtype=np_size_map[joints_accessor.componentType]).reshape(-1, 4)
		weight_bytes = self.get_accessor_bytes(primitive.attributes.WEIGHTS_0)
		self.W[:,:4] = np.frombuffer(weight_bytes, dtype=np.float32).reshape(-1, 4)

		has_extra_weights = ( hasattr(primitive.attributes, "JOINTS_1") and primitive.attributes.JOINTS_1 is not None )
		if has_extra_weights:
			# could copy these into the numpy array if they exist, but we're mainly reserving space for the gradients
			print("Warning/Info: Primitive uses more than 4 bone influences per vertex.")
		
		# --- Compute Weight gradients and setup buffers for rendering ---

		self.compute_weight_gradients()  
		self.check_weight_gradients()   # should be very close to zero!

		vbo_pos = ctx.buffer(pos_bytes)
		vbo_norm = ctx.buffer(norm_bytes)

		# joint, weight, and weight gradietn buffers are split across two different vec4 attributes
		joints_format = type_map[joints_accessor.componentType]
		vbo_joints_0 = ctx.buffer(np.ascontiguousarray(self.J[:, :4]).tobytes())
		vbo_joints_1 = ctx.buffer(np.ascontiguousarray(self.J[:, 4:]).tobytes())
		vbo_weights_0 = ctx.buffer(np.ascontiguousarray(self.W[:, :4]).tobytes())
		vbo_weights_1 = ctx.buffer(np.ascontiguousarray(self.W[:, 4:]).tobytes())
		vbo_grad_weights_0 = ctx.buffer(np.ascontiguousarray(self.W_gradients[:, :4, :].transpose(0, 2, 1), dtype=np.float32).tobytes())
		vbo_grad_weights_1 = ctx.buffer(np.ascontiguousarray(self.W_gradients[:, 4:, :].transpose(0, 2, 1), dtype=np.float32).tobytes())
		
		ibo = ctx.buffer(index_bytes)

		attributes = [
						(vbo_pos, '3f', 'in_position'),
						(vbo_norm, '3f', 'in_normal'),
						(vbo_grad_weights_0, '12f', 'in_grad_weights_0'),
						(vbo_grad_weights_1, '12f', 'in_grad_weights_1'),
						(vbo_joints_0, joints_format, 'in_joints_0'),
						(vbo_joints_1, joints_format, 'in_joints_1'),
						(vbo_weights_0, '4f', 'in_weights_0'),
						(vbo_weights_1, '4f', 'in_weights_1'),
					]

		# Build VAOs for LBS and DQS using the same attributes and index buffer, but different shader programs
		# (Note that the programs only differ by how they define uniform data for the bone transformations)
		self.vao_LBS = ctx.vertex_array( self.prog_LBS, attributes, ibo, index_element_size=index_element_size )
		self.vao_DQS = ctx.vertex_array( self.prog_DQS, attributes, ibo, index_element_size=index_element_size )

		# --- Set default visualization parameters --- 

		self.compute_model_matrix()	            # compute the model matrix to center and scale the asset to fit within a [-1, 1] cube	

		self.dual_quaternion_skinning = False	# use DQS (otherwise LBS)
		self.correct_normals = False			# use the normal correction
		self.which_bone = 0						# Bone selection for for weight and weight gradient visualization 
		self.draw_mode = 0  					# 0 lighting, 1 normals, 2 weights, 3 weight gradients
		self.t_pose = False  					# Force the charactger into the T-pose for debugging and visualization
		self.grad_viz_scale_exp = 0.0  			# 10**exp scale for weight gradient visualization 


	def get_accessor_bytes(self, accessor_idx):
		acc = self.gltf.accessors[accessor_idx]
		bv = self.gltf.bufferViews[acc.bufferView]
		start = (bv.byteOffset or 0) + (acc.byteOffset or 0)
		end = start + bv.byteLength
		return self.blob[start:end]


	def compute_model_matrix(self):
		''' compute the model matrix to center and scale the asset to fit within a [-1, 1] cube '''
		min_b = glm.vec3(*self.V.min(axis=0))
		max_b = glm.vec3(*self.V.max(axis=0))
		center = (min_b + max_b) * 0.5
		extents = max_b - min_b
		max_extent = max(extents.x, extents.y, extents.z)
		scale = 2.0 / max_extent if max_extent > 0 else 1.0
		translation_mat = glm.translate(glm.mat4(1.0), -center)
		self.model_matrix = glm.scale(translation_mat, glm.vec3(scale))


	def compute_weight_gradients(self):
		''' TODO: compute the gradient of the skinning weights for each vertex '''
		pass


	def check_weight_gradients(self):
		# Check the sum of gradients across all bones for each vertex
		gradient_sums = np.sum(self.W_gradients, axis=1) # shape: (num_vertices, 3)
		max_deviation = np.max(np.linalg.norm(gradient_sums, axis=1))
		print(f"Max gradient sum magnitude: {max_deviation}")


	def matrix_to_dual_quaternion(self, m4x4: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
		# Get rotation matrix (upper-left 3x3) and convert to unit quaternion
		rot_mat = m4x4[0:3, 0:3]
		q_p = R.from_matrix(rot_mat).as_quat() # Output format: [x, y, z, w]
		# Get translation vector (right column)
		t = m4x4[0:3, 3]
		# Compute the dual part: q_d = 0.5 * t * q_p, where t is pure imaginary quaternion (w=0)
		q_t = np.array([t[0], t[1], t[2], 0.0]) 
		# Quaternion multiplication local function helper
		def q_mul(q1, q2):
			# Multiplies two quaternions [x, y, z, w]
			x1, y1, z1, w1 = q1
			x2, y2, z2, w2 = q2
			return np.array([
				w1*x2 + x1*w2 + y1*z2 - z1*y2,
				w1*y2 - x1*z2 + y1*w2 + z1*x2,
				w1*z2 + x1*y2 - y1*x2 + z1*w2,
				w1*w2 - x1*x2 - y1*y2 - z1*z2
			])
		q_d = 0.5 * q_mul(q_t, q_p)
		# Return as two vec4 arrays ready for GLSL
		return q_p, q_d

	def paint(self, ctx, P: glm.mat4x4, V: glm.mat4x4, bones: list[np.ndarray]): 

		prog = self.prog_DQS if self.dual_quaternion_skinning else self.prog_LBS
		vao = self.vao_DQS if self.dual_quaternion_skinning else self.vao_LBS
		
		prog['u_model'].write(self.model_matrix)
		prog['u_view'].write(V)
		prog['u_projection'].write(P)
		prog['u_light_direction'].value = (0.0, 1.0, 1.0)
		prog['u_base_color'].value = (0.2, 0.8, 0.2)
		prog['u_correct_normals'].value = self.correct_normals
		prog['u_draw_mode'].value = self.draw_mode
		prog['u_which_bone'].value = self.which_bone
		prog['u_grad_viz_scale'].value = 10**self.grad_viz_scale_exp

		if self.dual_quaternion_skinning:
			# slow to loop and convert, but let's do it slow and easy for now...
			# 128 dual quaternions, each with 8 floats (4 for primal, 4 for dual)
			bone_p_palette = np.zeros((128, 4), dtype='f4')
			bone_p_palette[:,3] = 1 # identity quaternion for unused bones, real part is last!
			bone_d_palette = np.zeros((128, 4), dtype='f4')
			if not self.t_pose:
				for i in range(len(bones)):
					q_p, q_d = self.matrix_to_dual_quaternion(bones[i])			
					bone_p_palette[i] = q_p
					bone_d_palette[i] = q_d
			prog['u_bone_q_r'].write(bone_p_palette.tobytes())
			prog['u_bone_q_d'].write(bone_d_palette.tobytes())
		else:
			bone_palette = np.tile(np.eye(4, dtype='f4'), (128, 1, 1))
			if not self.t_pose:
				bone_palette[:len(bones)] = np.asarray(bones, dtype='f4').transpose(0, 2, 1)  # GL expects column-major
			prog['u_bone_matrices'].write(bone_palette.tobytes())
			
		vao.render(mode=mgl.TRIANGLES)	

