# Orlando Qiu 261175512

import os
import polyscope as ps
import polyscope.imgui as psim
import numpy as np
import json5
import argparse
from Node import Node
from KeyframeManager import KeyframeManager


class Demo:
    def __init__(self, character_file, keyframes_file):            
        self.keyframes_file = keyframes_file
        self.character_file = character_file
        path = os.path.dirname(os.path.abspath(__file__)) + "/data/"
        with open(path + character_file, "r") as f:
            self.character_data = json5.load(f)
        self.anim_mgr = KeyframeManager(path + keyframes_file)
        self.root = Node(self.character_data["root"])

        self.is_playing = False
        self.current_frame = 0
        initial_pose = self.anim_mgr.evaluate(self.current_frame)
        if initial_pose:
            self.root.set_pose(initial_pose)
        self.root.pose_update(np.identity(4))    

    def update(self):
        frame_changed = False

        _, self.is_playing = psim.Checkbox("Play Animation", self.is_playing)

        if self.is_playing:
            self.current_frame = (self.current_frame + 1) % (self.anim_mgr.max_frames + 1)
            frame_changed = True

        changed_frame, new_frame = psim.SliderInt("Frame", self.current_frame, 0, self.anim_mgr.max_frames)
        if changed_frame:
            self.current_frame = new_frame
            frame_changed = True

        sorted_kfs = sorted(self.anim_mgr.keyframes.keys())
        prev_kfs = [k for k in sorted_kfs if k < self.current_frame]
        next_kfs = [k for k in sorted_kfs if k > self.current_frame]
        if psim.Button("Previous Key") and prev_kfs:
            self.current_frame = max(prev_kfs)
            frame_changed = True
        psim.SameLine()
        if psim.Button("Next Key") and next_kfs:
            self.current_frame = min(next_kfs)
            frame_changed = True
        is_on_kf = self.current_frame in self.anim_mgr.keyframes
        set_label = "Update Keyframe" if is_on_kf else "Set Keyframe"
        if psim.Button(set_label):
            self.anim_mgr.keyframes[self.current_frame] = self.root.get_pose()
        if is_on_kf:
            psim.SameLine()
            if psim.Button("Delete Keyframe"):
                del self.anim_mgr.keyframes[self.current_frame]
        if psim.Button("Save Keyframes to "+ self.keyframes_file):
            self.anim_mgr.save()

        if frame_changed:
            pose = self.anim_mgr.evaluate(self.current_frame)
            if pose:
                self.root.set_pose(pose)

        changed, enabled = psim.Checkbox("Show Axes", self.root.axis.axis.is_enabled())
        if changed:
            self.root.set_axis_enabled(enabled)

        changed = self.root.ui_update()  # Update the UI for the node hierarchy and sliders
                
        # Update node hierarchy and render joint sliders
        if changed or frame_changed:
            self.root.pose_update(np.identity(4))  # Update the pose of the entire hierarchy


argparser = argparse.ArgumentParser(description="COMP 557 A1 - Orlando Qiu")
argparser.add_argument('--file', type=str, default="character.json5", help='character file to load')
argparser.add_argument('--anim', type=str, default="keyframes.json5", help='keyframes file to load')
args = argparser.parse_args()

ps.init()
ps.set_automatically_compute_scene_extents(False)
ps.set_ground_plane_height(0.0)
ps.set_always_redraw(True)
demo = Demo( args.file, args.anim )
ps.set_user_callback(demo.update)
ps.show()