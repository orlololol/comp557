#version 330

in vec3 in_position;
in vec3 in_normal;
in uvec4 in_joints_0;           // Bone indices, influences 0-3
in uvec4 in_joints_1;           // Bone indices, influences 4-7
in vec4 in_weights_0;           // Bone weights, influences 0-3
in vec4 in_weights_1;           // Bone weights, influences 4-7
in mat3x4 in_grad_weights_0;    // Gradient of bone weights, influences 0-3
in mat3x4 in_grad_weights_1;    // Gradient of bone weights, influences 4-7

const int MAX_BONES = 128;
uniform vec4 u_bone_q_r[MAX_BONES]; // Rotation part of the dual quaternion for each bone
uniform vec4 u_bone_q_d[MAX_BONES]; // Displacement (dual) part of the dual quaternion for each bone

uniform mat4 u_model;
uniform mat4 u_view;
uniform mat4 u_projection;

uniform bool u_correct_normals;     // correct the normals when true
uniform int u_which_bone;           // bone selection for weight and weight gradient visualization

out vec3 v_eye_position;
out vec3 v_eye_normal;
out vec3 v_grad_weight;
out float v_weight;

// Converts a normalized dual quaternion (q_r, q_d) into a 4x4 rigid transformation matrix
mat4 dualQuaternionToMat4(vec4 q_r, vec4 q_d) {
    // Rotation matrix from the q_r part
    float x2 = q_r.x + q_r.x;  
    float y2 = q_r.y + q_r.y;  
    float z2 = q_r.z + q_r.z;
    float xx = q_r.x * x2,   xy = q_r.x * y2,   xz = q_r.x * z2;
    float yy = q_r.y * y2,   yz = q_r.y * z2,   zz = q_r.z * z2;
    float wx = q_r.w * x2,   wy = q_r.w * y2,   wz = q_r.w * z2;
    mat4 m = mat4(
        1.0 - (yy + zz), xy + wz,          xz - wy,          0.0,
        xy - wz,          1.0 - (xx + zz), yz + wx,          0.0,
        xz + wy,          yz - wx,          1.0 - (xx + yy), 0.0,
        0.0,              0.0,              0.0,             1.0
    );
    // Translation vector from the dual part, t = 2.0 * q_d * conjugate(q_r)
    m[3].xyz = 2.0 * (q_r.w * q_d.xyz - q_d.w * q_r.xyz + cross(q_r.xyz, q_d.xyz));
    return m;
}

void main() {

    // TODO Compute the blended dual quaternion for skinning
    // You may convert that dual quaternion into a 4x4 matrix with the provided dualQuaternionToMat4 function, 
    // Or otherwise, make the code below more efficienty by use the method for transforming points and vectors seen in class.

    mat4 skin_matrix = dualQuaternionToMat4(u_bone_q_r[0],u_bone_q_d[0]); // Arbitrary matrix, replace with your computed skinning matrix;   

    // 2. Transform Vertex Position (4D homogeneous point, w = 1.0)
    vec4 local_skinned_pos = skin_matrix * vec4(in_position, 1.0);
    vec4 world_pos = u_model * local_skinned_pos;
    v_eye_position = (u_view * world_pos).xyz;

    if (u_correct_normals) {
        // TODO: Compute correct normals!

        v_eye_normal = vec3(0.0, 0.0, 1.0); // Replace with your computed normal
    } else {
        mat3 normal_matrix = mat3(u_model) * mat3(skin_matrix);
        v_eye_normal = normalize(mat3(u_view) * normal_matrix * in_normal);
    }

    // copy the weight and weight gradient for the selected bone to the fragment shader for visualization 
    // (only used when the draw mode is set to visualize weights or weight gradients)
    v_grad_weight = vec3(0.0);
    v_weight = 0.0;
    for (int i = 0; i < 4; ++i) {
        if (int(in_joints_0[i]) == u_which_bone) {
            v_grad_weight += vec3(in_grad_weights_0[0][i], in_grad_weights_0[1][i], in_grad_weights_0[2][i]);
            v_weight += in_weights_0[i];
        }
        if (int(in_joints_1[i]) == u_which_bone) {
            v_grad_weight += vec3(in_grad_weights_1[0][i], in_grad_weights_1[1][i], in_grad_weights_1[2][i]);
            v_weight += in_weights_1[i];
        }
    }

    gl_Position = u_projection * u_view * world_pos;
}