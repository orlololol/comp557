Orlando Qiu 261175512

Do you wish you use your late penalty waiver for this submission?

- [YES / NO]

Did you discuss the assignment with other students, the TAs, or the prof? If yes, write a sentence to say who you talked to and what discussion was helpful. If no, leave as "No discussion".

- No discussion

If you used any LLM tools, give a short description of how you used them. If you did not use any LLM tools, leave as "No LLM tools used".

- No LLM tools used

Explain decisions you made in writing the code.

- Rays are always moved into each object's local frame with M_inv and never renormalized, so t stays valid in world space, normals use the inverse transpose.
- Shadow rays use t_min = 0.01 and t_max = distance to the light.
- Box normals come from the face the local hit point lies on, triangles use Cramer's rule.
- Jitter, lens and area-light sampling use one random sample per pass and rely on accumulation over AA_samples.

For the adventure part:

- Mesh bounding box: the parser computes each mesh's local min/max vertex once and then intersectMesh tests the ray against that box before looping over triangles. TwoMeshes went from about 160s to 60s at full resolution.
- Mirror reflection: render() follows the ray through an iterative bounce loop, then each bounce adds throughput \* local shading, multiplies throughput by the reflectivity and continues along reflect(d, n). Bounce rays use t_min = 0.01 to avoid self-intersection.
- Refraction: used Snell's law (tm.refract), flipping the normal and using eta = ior when the ray exits the object, and falls back to reflection on total internal reflection.
- Depth of field: the image plane is placed at the focus distance and the ray origin is a uniform random point on the lens disk, so objects out of focus blurs as samples accumulate.
- Area lights: each pass, the lighting direction and shadow ray aim at a uniform random point on the light's sphere, which gives soft shadow after accumulation.
- Quadrics: new object cylinder (x^2+z^2=1) and cone (x^2+z^2=(1-y)^2). Both roots are checked against the height restriction 0<=y<=1, and normals are the gradient of the implicit function.
