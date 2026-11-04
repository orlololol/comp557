Orlando Qiu and 261175512

Do you wish you use your late penalty waiver for this submission?

- NO

Did you discuss the assignment with other students, the TAs, or the prof? If yes, write a sentence to say who you talked to and what discussion was helpful. If no, leave as "No discussion".

- No discussion

If you used any LLM tools, give a short description of how you used them. If you did not use any LLM tools, leave as "No LLM tools used".

- No LLM tools used

Explain decisions you made in writing the code.

- Weight gradients: computed per triangle (barycentric gradients n\*e/2A combined with each bone's vertex weights), then average area onto vertices, giving bigger triangles more say.
- A vertex can have a nonzero gradient for a bone it isn't weighted by (influence from a neighbour). Those bones go into free slots with weight 0, which keeps the vertex gradient sum near zero.
- DQS: if a bone's rotation points the opposite way from the first bone's, flip both of its parts, q_r and q_d, then all 8 components are divided by |q_r|.
- Corrected normals: inverse transpose of the full Jacobian, mat3(skin) + sum( (T_i p − p') gradient(w_i^T)). Subtracting p' changes nothing since the gradients sum to zero, but it reduces error and gives J = I in T pose.
- DQS normals: same form, using the blended rotation and each bone's rigid transform. This is a close approximation, not exact.
