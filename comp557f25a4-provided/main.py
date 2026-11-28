# Orlando Qiu 261175512
import parser
from scene import Scene
import argparse
from PIL import Image
import pathlib
import taichi as ti
import numpy as np

parse = argparse.ArgumentParser()
parse.add_argument("-i", "--infile", type=str, help="Name of json file that will define the scene", required = True)
parse.add_argument("-o", "--outdir", type=str, default="out", help="directory for output files, default is ./out")
parse.add_argument('-s', '--show', action='store_true', help="Show the image in a window")
parse.add_argument('-f', '--factor', type=float, default=1.0, help="Scale factor for resolution")
parse.add_argument('-ti', '--taichi', type=str, default='cpu', help="Taichi backend 'cpu', 'vulkan', 'cuda', 'metal', cpu is default")

args = parse.parse_args()

def save_image( image: ti.Vector.field, scene_file_name: str, outdir_name: str ):
        img = image.to_numpy()
        # remove the path and extension from scene file, put it in outdir with png extension
        outdir = pathlib.Path(outdir_name)
        outdir.mkdir(exist_ok=True) # Create output directory if it doesn't exist
        fout = str(outdir / pathlib.Path(scene_file_name).stem) + ".png"
        print("Saving image to", fout)
        img = np.clip(img, 0, 1)           # Clamp to [0,1]
        img = np.swapaxes(img, 0, 1)       # Change shape to (H, W, 3)        
        img = np.flip(img, axis=0)         # Flip vertically (up/down)
        img_pil = Image.fromarray((img * 255).astype(np.uint8))
        img_pil.save(fout)

if __name__ == "__main__":
    
    arch = {
        "cpu": ti.cpu,
        "cuda": ti.cuda,
        "vulkan": ti.vulkan,
        "metal": ti.metal
    }
    init_opitons = {
        'arch': arch[args.taichi],
        'debug': True,
        # 'print_ir': True,
        # 'kernel_profiler': False,
        # 'verbose': False,
        # 'advanced_optimization': False,
        'log_level': ti.DEBUG  #[ti.INFO, ti.TRACE, ti.WARN, ti.ERROR, ti.CRITICAL, ti.DEBUG]
    }
    ti.init(**init_opitons)

    full_scene = Scene()

    scene_file_name = args.infile
    parser.load_scene( scene_file_name, args.factor, full_scene )
    print("Scene Loaded")

    samples = full_scene.camera.samples
    if args.show:
        gui = ti.GUI('Image', (full_scene.camera.width, full_scene.camera.height))
        iteration = 1
        while gui.running:
            if iteration <= samples or samples < 0:
                full_scene.render()
                print(f"Completed {iteration-1} / {samples} samples per pixel")
                iteration += 1
            gui.set_image( full_scene.image )
            gui.show()
        save_image( full_scene.image, scene_file_name, args.outdir )
    else:
        if samples < 0:
            samples = 1  # just do one iteration if not showing and requesting infinite samples
        for iteration in range(1, samples + 1):
            full_scene.render()
            print(f"Completed {iteration} / {samples} samples per pixel")
        save_image( full_scene.image, scene_file_name, args.outdir )

    ti.profiler.print_kernel_profiler_info()
