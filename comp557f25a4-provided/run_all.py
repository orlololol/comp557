import glob
import subprocess

# Find all JSON files in the scenes folder
scene_files = glob.glob("scenes/*.json")

if not scene_files:
    print("No scene files found in the scenes/ folder!")
else:
    for scene in sorted(scene_files):
        print(f"\n--- Running: {scene} ---")
        subprocess.run(["python", "main.py", "-i", scene])