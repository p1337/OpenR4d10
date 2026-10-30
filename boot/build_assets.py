#!/usr/bin/env python3
"""Offline conversion only: approved video -> exact 240x280 RGB565 assets."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
import zlib
from fractions import Fraction
from pathlib import Path

import numpy as np
from PIL import Image

WIDTH, HEIGHT = 240, 280
BOTTOM_EMPTY_ROWS = 22
HEADER = struct.Struct("<8sHHIIIII")
RECORD = struct.Struct("<II")


def write_pack(path: Path, frames: list[bytes], fps: Fraction, loop_start: int) -> None:
    with path.open("wb") as stream:
        stream.write(HEADER.pack(b"OR4BOOT1", WIDTH, HEIGHT, fps.numerator,
                                 fps.denominator, len(frames), loop_start, WIDTH * HEIGHT * 2))
        for frame in frames:
            encoded = zlib.compress(frame, level=6)
            stream.write(RECORD.pack(len(encoded), zlib.crc32(frame)))
            stream.write(encoded)


def build(source: Path, destination: Path) -> dict:
    destination.mkdir(parents=True, exist_ok=True)
    metadata = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate", "-of", "json", str(source),
    ]))["streams"][0]
    fps = Fraction(metadata["r_frame_rate"])
    if not 1 <= fps <= 30:
        raise ValueError("Review frame rate explicitly; expected original <=30 fps")
    # Preserve width and the complete wordmark. The approved source contains
    # a near-black footer beneath the fire; merely padding above does not put
    # the actual flame base at the physical display edge.
    vf = "scale=240:280:force_original_aspect_ratio=decrease:flags=lanczos,setsar=1,pad=240:280:0:oh-ih:black"
    rgb = subprocess.check_output([
        "ffmpeg", "-v", "error", "-i", str(source), "-an", "-vf", vf,
        "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ])
    pixels = np.frombuffer(rgb, dtype=np.uint8).reshape(-1, HEIGHT, WIDTH, 3)
    discarded = pixels[:, -BOTTOM_EMPTY_ROWS:]
    discarded_peak = int(discarded.max())
    if discarded_peak > 16:
        raise ValueError("Bottom framing would remove visible content; review this source explicitly")
    pixels = np.pad(pixels[:, :-BOTTOM_EMPTY_ROWS],
                    ((0, 0), (BOTTOM_EMPTY_ROWS, 0), (0, 0), (0, 0)))
    vf += f",crop={WIDTH}:{HEIGHT-BOTTOM_EMPTY_ROWS}:0:0,pad={WIDTH}:{HEIGHT}:0:{BOTTOM_EMPTY_ROWS}:black"
    frames: list[bytes] = []
    for frame in pixels:
        value = frame.astype(np.uint16)
        packed = ((value[..., 0] >> 3) << 11) | ((value[..., 1] >> 2) << 5) | (value[..., 2] >> 3)
        frames.append(packed.astype(">u2").tobytes())
    if not frames:
        raise ValueError("Source contains no video frames")
    loop_count = max(1, round(float(fps)))
    loop_start = max(0, len(frames) - loop_count)
    write_pack(destination / "boot.opb", frames, fps, loop_start)
    write_pack(destination / "first.opb", [frames[0]], fps, 0)
    (destination / "first.rgb565").write_bytes(frames[0])
    Image.fromarray(pixels[0]).save(destination / "first.png")
    Image.fromarray(pixels[-1]).save(destination / "last.png")
    # MP4 is a small browser/phone preview, not the file decoded during boot.
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", str(source), "-an", "-vf", vf,
        "-fps_mode", "passthrough", "-c:v", "libx264", "-preset", "slow",
        "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(destination / "preview_240x280.mp4"),
    ], check=True)
    report = {
        "source_name": source.name,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "width": WIDTH, "height": HEIGHT,
        "framing": "Portrait, original content shifted down 22 px; near-black footer removed; complete wordmark retained",
        "removed_footer_rows": BOTTOM_EMPTY_ROWS,
        "removed_footer_peak_rgb": discarded_peak,
        "fps_numerator": fps.numerator, "fps_denominator": fps.denominator,
        "frame_count": len(frames), "duration_seconds": len(frames) / float(fps),
        "pixel_format": "RGB565 big-endian, ST7789 wire order",
        "compression": "independent zlib frames, lossless after native RGB565 conversion",
        "raw_frame_bytes": WIDTH * HEIGHT * 2,
        "raw_pixel_bus_mbit_s": WIDTH * HEIGHT * 16 * float(fps) / 1_000_000,
        "loop_start_frame": loop_start,
        "loop_frame_count": len(frames) - loop_start,
        "loop_note": "Final second of approved video, forward playback; loop seam requires visual hardware review.",
        "pack_bytes": (destination / "boot.opb").stat().st_size,
        "first_pack_bytes": (destination / "first.opb").stat().st_size,
        "preview_mp4_bytes": (destination / "preview_240x280.mp4").stat().st_size,
        "hardware_validation": "not yet tested on the physical Pi Zero 2 W / Whisplay",
    }
    (destination / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    build(args.source, args.destination)
