# Orlando Qiu 261175512

from numpy import tan

from helperclasses import Ray
import taichi as ti
from pyglm import glm
import taichi.math as tm

@ti.data_oriented
class Camera:
	def __init__(self, width, height, eye_position:glm.vec3, lookat:glm.vec3, up:glm.vec3, fovy, jitter:bool=False, samples:int=1, aperture:float=0.0, focus_distance=None) -> None:
		'''	Initialize the camera with given parameters.
		Args:
			width (int): width of the image in pixels
			height (int): height of the image in pixels
			eye_position (glm.vec3): position of the camera in world space
			lookat (glm.vec3): point the camera is looking at
			up (glm.vec3): up direction for the camera
			fovy (float): vertical field of view in degrees
			jitter (bool): whether to apply jittering within the pixel for anti-aliasing
			samples (int): number of samples per pixel for anti-aliasing
		Returns:
			None

			Note that while glm types are provided to construct the class, the 
			member variables must be of taich tm.vec3 types so that they used 
			in the create_ray Taichi function.  
		'''
		self.width = width
		self.height = height		
		self.distance_to_plane = 1.0
		self.jitter = jitter
		self.samples = samples
		self.aperture = aperture # lens radius for depth of field, 0 = pinhole
		if focus_distance is None: focus_distance = glm.length(lookat - eye_position) # default focus on the lookAt point
		self.focus_distance = focus_distance

		# Objective 1: Compute camera frame basis vectors, and top bottom left right for ray generation
		# NOTE: glm vectors are passed in to permit the work to be done here in python, but stored vectors must be tm.vec3


		# Compute proper values below!
		self.top = tan(glm.radians(fovy)/2.0) * self.distance_to_plane
		self.bottom = -tan(glm.radians(fovy)/2.0) * self.distance_to_plane
		self.left = -self.top * (width/height)
		self.right = -self.left
		w = glm.normalize(eye_position - lookat)
		u = glm.normalize(glm.cross(up, w))
		v = glm.normalize(glm.cross(w, u))
		self.w = tm.vec3(w)
		self.u = tm.vec3(u)
		self.v = tm.vec3(v)
		self.eye_position = tm.vec3(eye_position.x, eye_position.y, eye_position.z)



	@ti.func
	def create_ray(self, x, y) -> Ray:
		''' Create a ray going through pixel (x,y) in image space 
		Args:
			x (int): pixel x coordinate
			y (int): pixel y coordinate
		Returns:
			Ray: generated ray from camera through pixel

			If jitter is True, the ray should not go through the exact center of the
			pixel, but instead be through a random point (uniform) inthe pixel area.
		'''

		
		# Objective 1: Generate ray from camera through pixel (col, row) with jittering
		# s = e + uu + vv - dw
		# p = e
		# d = s - e
		# ray = p+td

		# jitter
		offset_x = 0.5
		offset_y = 0.5
		if self.jitter:
			offset_x = ti.random()
			offset_y = ti.random()
			

		s = self.left + (self.right - self.left) * (x + offset_x) / self.width
		t = self.bottom + (self.top - self.bottom) * (y + offset_y) / self.height
		# image plane scaled to the focus distance, so all lens samples meet there
		point = self.eye_position + self.focus_distance * (s * self.u + t * self.v - self.w * self.distance_to_plane)
		origin = self.eye_position
		if self.aperture > 0: # random point on the lens disk (polar, sqrt for uniform density)
			r = self.aperture * ti.sqrt(ti.random())
			theta = 2.0 * tm.pi * ti.random()
			origin = self.eye_position + r * ti.cos(theta) * self.u + r * ti.sin(theta) * self.v
		d = tm.normalize(point - origin)

		return Ray( origin, d )  # temporary ray
