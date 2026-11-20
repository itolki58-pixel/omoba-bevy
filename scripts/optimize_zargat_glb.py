#!/usr/bin/env python3
"""Downscale and recompress embedded Zargat glTF images without touching skin/animation data."""
from __future__ import annotations

import json
import struct
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

GLB_MAGIC = b"glTF"
JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942
MAX_TEXTURE_SIZE = 2048


def optimize(path: Path) -> None:
    raw = path.read_bytes()
    if len(raw) < 20:
        raise RuntimeError("GLB is truncated")
    magic, version, total_length = struct.unpack_from("<4sII", raw, 0)
    if magic != GLB_MAGIC or version != 2 or total_length != len(raw):
        raise RuntimeError("Not a valid GLB 2.0 container")

    chunks: list[tuple[int, bytes]] = []
    offset = 12
    while offset < len(raw):
        length, kind = struct.unpack_from("<II", raw, offset)
        offset += 8
        data = raw[offset : offset + length]
        if len(data) != length:
            raise RuntimeError("GLB chunk is truncated")
        chunks.append((kind, data))
        offset += length

    json_index = next((i for i, (kind, _) in enumerate(chunks) if kind == JSON_CHUNK), None)
    bin_index = next((i for i, (kind, _) in enumerate(chunks) if kind == BIN_CHUNK), None)
    if json_index is None or bin_index is None:
        raise RuntimeError("GLB must contain JSON and BIN chunks")

    document = json.loads(chunks[json_index][1].rstrip(b" \t\r\n\0").decode("utf-8"))
    binary = chunks[bin_index][1]
    views = document.get("bufferViews", [])
    images = document.get("images", [])
    images_by_view: dict[int, list[dict]] = {}
    for image in images:
        if "bufferView" in image:
            images_by_view.setdefault(image["bufferView"], []).append(image)

    rebuilt = bytearray()
    optimized_count = 0
    for view_index, view in enumerate(views):
        old_offset = int(view.get("byteOffset", 0))
        old_length = int(view["byteLength"])
        data = binary[old_offset : old_offset + old_length]
        if len(data) != old_length:
            raise RuntimeError(f"bufferView {view_index} is outside the BIN chunk")

        if view_index in images_by_view:
            image_def = images_by_view[view_index][0]
            image_name = image_def.get("name", "zargat_texture").lower()
            with Image.open(BytesIO(data)) as source:
                source.load()
                original_size = source.size
                if max(source.size) > MAX_TEXTURE_SIZE:
                    ratio = MAX_TEXTURE_SIZE / max(source.size)
                    new_size = (
                        max(1, round(source.width * ratio)),
                        max(1, round(source.height * ratio)),
                    )
                    source = source.resize(new_size, Image.LANCZOS)
                is_data_map = any(
                    token in image_name for token in ("normal", "roughness", "metallic", "_rm")
                )
                preserve_alpha = source.mode in ("RGBA", "LA")
                encoded = BytesIO()
                if is_data_map or preserve_alpha:
                    if source.mode not in ("RGB", "RGBA", "L", "LA"):
                        source = source.convert("RGBA" if preserve_alpha else "RGB")
                    source.save(encoded, format="PNG", optimize=True, compress_level=9)
                    image_def["mimeType"] = "image/png"
                else:
                    if source.mode != "RGB":
                        source = source.convert("RGB")
                    source.save(
                        encoded,
                        format="JPEG",
                        quality=88,
                        optimize=True,
                        progressive=False,
                        subsampling=0,
                    )
                    image_def["mimeType"] = "image/jpeg"
                data = encoded.getvalue()
                optimized_count += 1
                print(
                    f"Zargat image {image_name}: {original_size} -> {source.size}, "
                    f"{len(data)} bytes ({image_def['mimeType']})"
                )
                if max(source.size) > MAX_TEXTURE_SIZE:
                    raise RuntimeError(f"Texture {image_name} exceeds 2K after optimization")

        while len(rebuilt) % 4:
            rebuilt.append(0)
        view["byteOffset"] = len(rebuilt)
        view["byteLength"] = len(data)
        rebuilt.extend(data)

    if document.get("buffers"):
        document["buffers"][0]["byteLength"] = len(rebuilt)
    json_data = json.dumps(document, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    json_data += b" " * ((-len(json_data)) % 4)
    bin_data = bytes(rebuilt)
    bin_data += b"\0" * ((-len(bin_data)) % 4)
    chunks[json_index] = (JSON_CHUNK, json_data)
    chunks[bin_index] = (BIN_CHUNK, bin_data)

    output = bytearray(struct.pack("<4sII", GLB_MAGIC, 2, 0))
    for kind, data in chunks:
        output.extend(struct.pack("<II", len(data), kind))
        output.extend(data)
    struct.pack_into("<I", output, 8, len(output))
    path.write_bytes(output)
    print(f"Zargat GLB optimized: {len(raw)} -> {len(output)} bytes; {optimized_count} images")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("client/assets/avatars/zargat.glb")
    optimize(target)
