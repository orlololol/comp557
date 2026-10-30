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
uniform mat4 u_bone_matrices[MAX_BONES];

uniform mat4 u_model;
uniform mat4 u_view;
uniform mat4 u_projection;

uniform bool u_correct_normals;     // correct the normals when true
uniform int u_which_bone;           // bone selection for weight and weight gradient visualization

out vec3 v_eye_position;
out vec3 v_eye_normal;
out vec3 v_grad_weight;
out float v_weight;

void main() {

    // Compute the blended skinning matrix for LBS
    mat4 skin_matrix = mat4(0.0);
    for (int i = 0; i < 4; ++i) {
        skin_matrix += in_weights_0[i] * u_bone_matrices[ int(in_joints_0[i]) ];
        skin_matrix += in_weights_1[i] * u_bone_matrices[ int(in_joints_1[i]) ];
    }


    // Transform Vertex Position (4D homogeneous point, w = 1.0)
    vec4 local_skinned_pos = skin_matrix * vec4(in_position, 1.0);
    vec4 world_pos = u_model * local_skinned_pos;
    v_eye_position = (u_view * world_pos).xyz;

    if (u_correct_normals) {
        // TODO: Compute correct normals!

        v_eye_normal = vec3(0.0, 0.0, 1.0); // Replace with your computed normal
    } else {
        mat3 normal_matrix = mat3(u_model) * transpose(inverse(mat3(skin_matrix)));
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