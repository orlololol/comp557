import json5
import os

class KeyframeManager:
    def __init__(self, keyframe_filepath: str, max_frames: int = 120):
        self.filepath = keyframe_filepath
        self.max_frames = max_frames
        self.keyframes = {}
        self.load()

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    data = json5.load(f)
                    if isinstance(data, dict):
                        self.keyframes = {int(k): v for k, v in data.items()}
            except Exception as e:
                print(f"Starting with empty keyframes ({e})")
                self.keyframes = {}

    def save(self):
        try:
            sorted_data = {str(k): self.keyframes[k] for k in sorted(self.keyframes.keys())}
            with open(self.filepath, "w") as f:
                json5.dump(sorted_data, f, indent=2)
            print(f"Saved keyframes to {self.filepath}")
        except Exception as e:
            print(f"Error saving keyframes to {self.filepath}: {e}")

    def evaluate(self, frame: int):
        if not self.keyframes:
            return None
        sorted_frames = sorted(self.keyframes.keys())
        if frame <= sorted_frames[0]:
            return self.keyframes[sorted_frames[0]]
        if frame >= sorted_frames[-1]:
            return self.keyframes[sorted_frames[-1]]

        f0 = max(f for f in sorted_frames if f <= frame)
        f1 = min(f for f in sorted_frames if f >= frame)
        if f0 == f1:
            return self.keyframes[f0]

        alpha = (frame - f0) / (f1 - f0)
        p0 = self.keyframes[f0]
        p1 = self.keyframes[f1]

        interp_pose = {}
        all_nodes = set(p0.keys()).union(p1.keys())
        for node in all_nodes:
            interp_pose[node] = {}
            node_p0 = p0.get(node, {})
            node_p1 = p1.get(node, {})
            all_dofs = set(node_p0.keys()).union(node_p1.keys())
            for dof in all_dofs:
                v0 = node_p0.get(dof, 0.0)
                v1 = node_p1.get(dof, v0)
                interp_pose[node][dof] = (1.0 - alpha) * v0 + alpha * v1
        return interp_pose