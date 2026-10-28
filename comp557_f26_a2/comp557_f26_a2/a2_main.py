
import glm
import moderngl as mgl
import numpy as np
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSignalBlocker
from PyQt5.QtGui import QSurfaceFormat, QWheelEvent, QKeyEvent
from PyQt5 import QtOpenGL, QtWidgets
from PyQt5.QtWidgets import QApplication
from usd_scene import USDScene
from pathlib import Path

from mode1_world import Mode1World
from mode2_camera import Mode2Camera
from mode3_depth_of_field import Mode3DepthOfField
from mode4_left_eye import Mode4LeftEye
from mode5_right_eye import Mode5RightEye
from mode6_anaglyph import Mode6Anaglyph
from mode7_anaglyph_dof import Mode7AnaglyphDOF
from render_context import RenderContext
from control_panel import ControlPanel

class ViewManager(QtOpenGL.QGLWidget):

    modeChanged = pyqtSignal(int)  # 1-based mode number
    focalDistanceChanged = pyqtSignal(float)
    sceneDistanceChanged = pyqtSignal(float)

    def __init__(self, filename):
        super().__init__()
        self.modes = [
                Mode1World(), 
                Mode2Camera(),
                Mode3DepthOfField(),
                Mode4LeftEye(),
                Mode5RightEye(),
                Mode6Anaglyph(),
                Mode7AnaglyphDOF(),

            ]
        self.current = 1
        # Mouse-drag orbit state for the third-person view and scene orientation.
        self.world_view_yaw = 0.0
        self.world_view_pitch = 0.0
        # Mouse-drag orbit state for the scene orientation in the camera view modes.
        self.scene_yaw = 0.0
        self.scene_pitch = 0.0
        self.last_mouse_pos = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.scene = USDScene(filename)


    def initializeGL(self):
        self.ctx = mgl.create_context()
        self.ctx.enable(mgl.DEPTH_TEST)
        self.scene.initializeGL(self.ctx)
        self.render_ctx = RenderContext(self.ctx, self.scene)
        self.timer.start(16)
        QTimer.singleShot(0, self.update)


    def resizeGL(self, width, height):
        ratio = self.devicePixelRatioF()
        w = max(1, round(width * ratio))
        h = max(1, round(height * ratio))
        self.ctx.viewport = (0, 0, w, h)


    def paintGL(self):
        self.modes[self.current-1].paint(self.render_ctx)


    def set_mode(self, mode_number):
        mode_number = int(np.clip(mode_number, 1, len(self.modes)))
        self.current = mode_number
        self.modeChanged.emit(mode_number)


    def set_focal_distance(self, value):
        value = float(np.clip(value, 0.1, 2.0))
        self.render_ctx.focal_distance = value
        self.focalDistanceChanged.emit(value)


    def set_scene_distance(self, value):
        value = float(np.clip(value, 0.1, 2.0))
        self.render_ctx.scene_distance = value
        self.sceneDistanceChanged.emit(value)


    def mousePressEvent(self, event):
        self.setFocus() # so that we can receive key events
        self.last_mouse_pos = event.pos()


    def mouseMoveEvent(self, event):
        if self.last_mouse_pos is not None and event.buttons() & Qt.LeftButton:
            delta = event.pos() - self.last_mouse_pos
            if self.current == 1:
                self.world_view_yaw += delta.x() * 0.01
                self.world_view_pitch += delta.y() * 0.01
                My = glm.rotate(glm.mat4(1.0), self.world_view_yaw, glm.vec3(0, 1, 0))
                Mp = glm.rotate(glm.mat4(1.0), self.world_view_pitch, glm.vec3(1, 0, 0))
                self.modes[0].world_view_orientation = Mp * My
            else:
                self.scene_yaw += delta.x() * 0.01
                self.scene_pitch += delta.y() * 0.01
                My = glm.rotate(glm.mat4(1.0), self.scene_yaw, glm.vec3(0, 1, 0))
                Mp = glm.rotate(glm.mat4(1.0), self.scene_pitch, glm.vec3(1, 0, 0))
                self.scene.scene_orientation = Mp * My
            self.last_mouse_pos = event.pos()


    def wheelEvent(self, event: QWheelEvent):
        if (event.modifiers() & Qt.ControlModifier) or (event.modifiers() & Qt.ShiftModifier):
            self.set_focal_distance(self.render_ctx.focal_distance * 2**(-event.angleDelta().y() * 0.001))
        elif self.current == 1:
            self.modes[0].world_viewing_distance *= 2**(-event.angleDelta().y() * 0.001)
            self.modes[0].world_viewing_distance = np.clip(self.modes[0].world_viewing_distance, 0.1, 15.0)
        else:
            self.set_scene_distance(self.render_ctx.scene_distance * 2**(-event.angleDelta().y() * 0.001))


    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if Qt.Key.Key_1 <= key <= Qt.Key.Key_8:
            self.set_mode(key - Qt.Key.Key_1 + 1)
        else:
            super().keyPressEvent(event)


fmt = QSurfaceFormat()
fmt.setVersion(3, 3)
fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
QSurfaceFormat.setDefaultFormat(fmt)
USD_FILE = "LegoBricks.usdc"
current_dir = Path(__file__).parent # data folder in same directory as this code
filename = str( current_dir / '../data' / USD_FILE )
app = QApplication([])
vm = ViewManager(filename)
vm.resize(1000, 700)
vm.show() # needed to have a valid OpenGL context and so we can use render_ctx below

win = QtWidgets.QMainWindow()
# TODO: Set the window title to include your name and student number
win.setWindowTitle("COMP557 Assignment 2 - YOUR NAME AND STUDENT NUMBER HERE")
central = QtWidgets.QWidget()
layout = QtWidgets.QHBoxLayout(central)
layout.addWidget(vm, stretch=4)

panel = ControlPanel()
layout.addWidget(panel, stretch=1)

# Viewing Mode Selector
mode_combo = QtWidgets.QComboBox()
mode_combo.addItems( [m.name for m in vm.modes] )
mode_combo.currentIndexChanged.connect( lambda index: vm.set_mode(index + 1) )
panel._form.addRow("Viewing Mode:", mode_combo)
vm.modeChanged.connect( lambda mode_number: (QSignalBlocker(mode_combo), mode_combo.setCurrentIndex(mode_number - 1)) )
focal_distance_spin = panel.add_double( "Focal Distance", vm.render_ctx, "focal_distance", 0.1, 2, 0.01 )
scene_distance_spin = panel.add_double( "Scene Distance", vm.render_ctx, "scene_distance", 0.1, 2, 0.01 )
vm.focalDistanceChanged.connect( lambda value: (QSignalBlocker(focal_distance_spin), focal_distance_spin.setValue(value)) )
vm.sceneDistanceChanged.connect( lambda value: (QSignalBlocker(scene_distance_spin), scene_distance_spin.setValue(value)) )
panel.add_double("Near Distance", vm.render_ctx, "near_distance", 0.01, 1.0, 0.01)
panel.add_double("Far Distance", vm.render_ctx, "far_distance", 1.0, 20.0, 0.01)
panel.add_double("Screen Distance", vm.render_ctx, "screen_distance", 0.1, 2, 0.01)
panel.add_double("Interocular Distance", vm.render_ctx, "interocular_distance", -0.1, 0.1, 0.005)
panel.add_double("Aperture Radius", vm.render_ctx, "aperture_radius", 0.0, 0.05, 0.001)
panel.add_int("Samples", vm.render_ctx, "num_samples", 1, 100)
panel.add_bool("Draw Screen Plane", vm.modes[0], "draw_screen_plane")
panel.add_bool("Draw Focal Plane", vm.modes[0], "draw_focal_plane")

panel.add_radio_group(
    title="Frustum Visualization",
    target=vm.modes[0],
    attr="frustum_view_mode",
    options=[
        ("Central", "central"),
        ("Stereo Pair", "stereo_both")
    ],
)

panel.add_bool("Draw All Sample Frustums", vm.modes[0], "draw_all_sample_frustums")

win.setCentralWidget(central)
win.resize(1280, 720)
win.show()
vm.setFocus()

app.exec()