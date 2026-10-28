import glm
import moderngl as mgl
import numpy as np
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QSurfaceFormat, QWheelEvent, QKeyEvent
from PyQt5 import QtOpenGL, QtWidgets
from PyQt5.QtWidgets import QApplication
from pygltflib import GLTF2
from pathlib import Path
from asset import Asset
from control_panel import ControlPanel
from skeleton import SkinningEngine
import time
import argparse


class ViewManager(QtOpenGL.QGLWidget):

    def __init__(self, filename):
        super().__init__()
        # Mouse-drag orbit state for the third-person view and scene orientation.
        self.world_view_yaw = 0.0
        self.world_view_pitch = 0.0
        self.last_mouse_pos = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.filename = filename

        self.world_viewing_distance = 5.0 # distance from the 3rd person world camera to the origin of the world
        self.world_view_orientation = glm.mat4(1.0)
        self.fovy = 27.0 # field of view in degrees for the camera

        self.animate = True
        self.elapsed = 0
        self.last_t = time.time()


    def initializeGL(self):
        self.ctx = mgl.create_context()
        self.ctx.enable(mgl.DEPTH_TEST | mgl.CULL_FACE)
        self.ctx.front_face = 'ccw' 
        self.ctx.cull_face = 'back'

        self.gltf = GLTF2.load(str(self.filename))
        self.asset = Asset(self.gltf, self.ctx)
        self.skin = SkinningEngine(self.gltf)  

        self.timer.start(16)
        QTimer.singleShot(0, self.update)


    def resizeGL(self, width, height):
        ratio = self.devicePixelRatioF()
        w = max(1, round(width * ratio))
        h = max(1, round(height * ratio))
        self.ctx.viewport = (0, 0, w, h)


    def paintGL(self):
        self.ctx.clear(1,1,1)
        w = self.ctx.viewport[2]
        h = self.ctx.viewport[3]		
        aspect = w / h
        P = glm.perspective(glm.radians(self.fovy), aspect, 0.1, 200.0)
        look_at = glm.lookAt(glm.vec3(0,0,self.world_viewing_distance), glm.vec3(0, 0, 0), glm.vec3(0, 1, 0))
        V = look_at * self.world_view_orientation 

        if self.animate:
            t = time.time()
            self.elapsed = self.elapsed + t - self.last_t
            self.last_t = t
        else:
            self.last_t = time.time()

        self.skin.sample_animation( 0, self.elapsed )  # Sample the first animation at the current time
        bones = self.skin.get_joint_matrices()

        self.asset.paint(self.ctx, P, V, bones)


    def set_scene_distance(self, value):
        value = float(np.clip(value, 0.1, 2.0))
        self.render_ctx.scene_distance = value
        self.sceneDistanceChanged.emit(value)


    def mousePressEvent(self, event):
        self.setFocus() # so that we can receive key events
        self.last_mouse_pos = event.pos()


    def mouseMoveEvent(self, event):
        delta = event.pos() - self.last_mouse_pos
        self.world_view_yaw += delta.x() * 0.01
        self.world_view_pitch += delta.y() * 0.01
        My = glm.rotate(glm.mat4(1.0), self.world_view_yaw, glm.vec3(0, 1, 0))
        Mp = glm.rotate(glm.mat4(1.0), self.world_view_pitch, glm.vec3(1, 0, 0))
        self.world_view_orientation = Mp * My
        self.last_mouse_pos = event.pos()


    def wheelEvent(self, event: QWheelEvent):
        self.world_viewing_distance *= 2**(-event.angleDelta().y() * 0.001)
        self.world_viewing_distance = np.clip(self.world_viewing_distance, 0.1, 150.0)


fmt = QSurfaceFormat()
fmt.setVersion(3, 3)
fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
QSurfaceFormat.setDefaultFormat(fmt)
app = QApplication([])

default_file = "Rectangle.glb"
#default_file = "RumbaDancing.glb" 

arg_parser = argparse.ArgumentParser(description="Run the 3D model viewer.")
arg_parser.add_argument('--file', type=str, default=default_file, help="GLB file to load from ../data/.")
args = arg_parser.parse_args()
GLB_FILE = args.file
current_dir = Path(__file__).parent # data folder in same directory as this code
file = current_dir / '../data' / GLB_FILE

vm = ViewManager(file)
vm.resize(1000, 700)
vm.show() # needed to have a valid OpenGL context and so we can use render_ctx below

win = QtWidgets.QMainWindow()
win.setWindowTitle("COMP557 Assignment 3 - YOUR NAME AND ID HERE") # TODO Add your name and ID !
central = QtWidgets.QWidget()
layout = QtWidgets.QHBoxLayout(central)
layout.addWidget(vm, stretch=3)

panel = ControlPanel()
panel.setMinimumWidth(320)
layout.addWidget(panel, stretch=1)

panel.add_bool("Animate", vm, "animate")
panel.add_bool("T-Pose", vm.asset, "t_pose")
panel.add_bool("Use Dual Quaternions", vm.asset, "dual_quaternion_skinning")
panel.add_bool("Correct Normals", vm.asset, "correct_normals")

panel.add_choice("Draw Mode", vm.asset, "draw_mode",
                 ["Lighting", "Normals", "Weights", "Weight Gradients"])
panel.add_int("Which Bone", vm.asset, "which_bone", 0, 90)
panel.add_double("Grad Viz Scale Exp.", vm.asset, "grad_viz_scale_exp", -2, 2)

win.setCentralWidget(central)
win.resize(1280, 720)
win.show()
vm.setFocus()
app.exec()