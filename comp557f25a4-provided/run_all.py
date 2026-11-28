# Orlando Qiu 261175512
import glob
import subprocess
import sys

# Find all JSON files in the scenes folder
scene_files = glob.glob("scenes/*.json")

if not scene_files:
    print("No scene files found in the scenes/ folder!")
else:
    for scene in sorted(scene_files):
        print(f"\n--- Running: {scene} ---")
        # fix from template since im on windows and the template uses linux commands
        subprocess.run([sys.executable, "main.py", "-i", scene])