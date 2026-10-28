Orlando Qiu 261175512

Do you wish you use your late penalty waiver for this submission?

- NO

Did you discuss the assignment with other students, the TAs, or the prof? If yes, write a sentence to say who you talked to and what discussion was helpful. If no, leave as "No discussion".

- No discussion

If you used any LLM tools, give a short description of how you used them. If you did not use any LLM tools, leave as "No LLM tools used".

- No LLM tools used

Explain decisions you made in writing the code, creating your character or the animation.

- pose_update builds a 4x4 matrix per DOF, then computes world_from_parent @ parent_from_local @ local_pose and recurses, so moving a parent carries all its descendants.
- Colour DOFs (cr cg cb ca) skip the matrix and only call set_color/set_transparency.
- Character: a stick person rooted at the pelvis (the only node with translation DOFs), with spine, head, shoulder bar, two segment arms and legs (elbows, knees) and ankles. Each joint sits at the start of its limb, and geometry_transform shifts the capsule so it extends from the joint, so rotating a joint swings the whole limb about it. The head is an icosphere with colour sliders and the feet are boxes.
- Animation: the stick person walks in a loop.
