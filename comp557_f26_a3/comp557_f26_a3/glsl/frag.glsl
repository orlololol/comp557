#version 330

in vec3 v_eye_position;
in vec3 v_eye_normal;
in vec3 v_grad_weight;      // passed to fragment program for debug visualization
in float v_weight;          // passed to fragment program for debug vizualizaiton

uniform vec3 u_light_direction;  // Direction TOWARD the light, normalized
uniform vec3 u_base_color;       // Default mesh color (e.g., vec3(0.8, 0.8, 0.8))

uniform int u_draw_mode;         // 0 lighting, 1 normals, 2 weights, 3 weight gradients
uniform float u_grad_viz_scale;

out vec4 frag_color;

void main() {
    vec3 N = normalize(v_eye_normal); // Re-normalize interpolated normal

    vec4 color;
    if (u_draw_mode == 0) {
        vec3 L = normalize(u_light_direction);
        vec3 V = normalize( - v_eye_position);
        vec3 H = normalize(L + V); // Halfway vector for Blinn-Phong
        vec3 ambient = 0.15 * u_base_color;
        float NdotL = max(dot(N, L), 0.0);
        vec3 diffuse = NdotL * u_base_color;
        float NdotH = max(dot(N, H), 0.0);
        float spec_power = 32.0;
        vec3 specular = pow(NdotH, spec_power) * vec3(0.4); // Subtle white highlight
        color = vec4( ambient + diffuse + specular, 1.0);
    } else if (u_draw_mode == 1) {
        color = vec4(N * 0.5 + 0.5, 1.0); // magenta for unimplemented mode
    } else if (u_draw_mode == 2) {
        color = vec4( v_weight, 0, 0, 1.0 );
    } else if (u_draw_mode == 3) {
        color = vec4( v_grad_weight * u_grad_viz_scale + 0.5, 1.0 );
    } else {
        color = vec4(1.0, 0.0, 1.0, 1.0); // Magenta for error
    }
    frag_color = color;
}