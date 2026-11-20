import bpy
import os
import sys
import math
import numpy as np

ROOT = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
SOURCE = os.path.join(ROOT, "art", "zargat", "source.glb")
OUTDIR = os.path.join(ROOT, "artifacts", "zargat")
OUTPUT = os.path.join(OUTDIR, "Zargat_intermediate.glb")

if not os.path.isfile(SOURCE):
    raise SystemExit(
        "Missing input model: art/zargat/source.glb. "
        "Add the approved source GLB to this path and rerun the workflow."
    )

os.makedirs(OUTDIR, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SOURCE)

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not meshes:
    raise SystemExit("The GLB imported, but contains no mesh objects.")

changed = 0
for material in bpy.data.materials:
    if not material.use_nodes:
        continue
    nodes = material.node_tree.nodes
    for node in nodes:
        if node.type != "TEX_IMAGE" or not node.image:
            continue
        image = node.image
        # Recolor only images connected to Principled BSDF Base Color.
        is_base_color = False
        for link in material.node_tree.links:
            if link.from_node == node and link.to_node.type == "BSDF_PRINCIPLED":
                if link.to_socket.name == "Base Color":
                    is_base_color = True
                    break
        if not is_base_color or image.channels < 3:
            continue

        w, h = image.size
        pixels = np.asarray(image.pixels[:], dtype=np.float32).reshape((h, w, image.channels))
        rgb = np.clip(pixels[:, :, :3], 0.0, 1.0)
        mx = rgb.max(axis=2)
        mn = rgb.min(axis=2)
        delta = mx - mn
        # Approximate HSV hue/saturation without altering neutral pixels.
        hue = np.zeros_like(mx)
        nz = delta > 1e-6
        r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
        mask = nz & (mx == r)
        hue[mask] = ((g[mask] - b[mask]) / delta[mask]) % 6.0
        mask = nz & (mx == g)
        hue[mask] = (b[mask] - r[mask]) / delta[mask] + 2.0
        mask = nz & (mx == b)
        hue[mask] = (r[mask] - g[mask]) / delta[mask] + 4.0
        hue /= 6.0
        # Red/orange regions become deeper ember-crimson; preserve highlights
        # and all neutral/metallic/normal-map textures.
        red_orange = (hue < 0.12) | (hue > 0.94)
        red_orange &= (rgb[:, :, 0] > rgb[:, :, 1] * 1.12)
        rgb[red_orange, 0] *= 0.72
        rgb[red_orange, 1] *= 0.58
        rgb[red_orange, 2] *= 0.62
        # Slightly deepen the overall red armor while retaining texture detail.
        pixels[:, :, :3] = np.clip(rgb, 0.0, 1.0)
        image.pixels[:] = pixels.reshape(-1).tolist()
        image.update()
        changed += 1

if changed == 0:
    print("WARNING: no connected Base Color texture was modified; exporting original materials.")

bpy.ops.export_scene.gltf(
    filepath=OUTPUT,
    export_format="GLB",
    export_apply=True,
    export_animations=True,
)
if not os.path.isfile(OUTPUT) or os.path.getsize(OUTPUT) < 1024:
    raise SystemExit("Export failed: output GLB is missing or unexpectedly small.")
print(f"Exported {OUTPUT} ({os.path.getsize(OUTPUT)} bytes); recolored textures: {changed}")
