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
SKULL_SOURCE_END_FRAME = 18
SKULL_SLOWDOWN_FACTOR = 3
LOOP_SOURCE_START_FRAME = 54
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


def build_timeline(pixels: np.ndarray) -> tuple[np.ndarray, int]:
    """Extend the moving skull phase and select the measured smoother loop."""
    if len(pixels) <= LOOP_SOURCE_START_FRAME:
        raise ValueError("Approved source is shorter than the reviewed timeline")
    if SKULL_SOURCE_END_FRAME >= LOOP_SOURCE_START_FRAME:
        raise ValueError("Skull extension must finish before the final logo loop")

    # Source frames 0..18 remain present at every third output position. The
    # two interpolated positions between them keep fire and camera motion alive
    # instead of freezing the first frame. This adds exactly 36 / 24 = 1.5 s.
    positions = np.linspace(
        0,
        SKULL_SOURCE_END_FRAME,
        SKULL_SOURCE_END_FRAME * SKULL_SLOWDOWN_FACTOR + 1,
    )
    extended: list[np.ndarray] = []
    for position in positions:
        lower = int(position)
        upper = min(lower + 1, SKULL_SOURCE_END_FRAME)
        fraction = position - lower
        if fraction == 0:
            extended.append(pixels[lower])
        else:
            blended = (
                pixels[lower].astype(np.float32) * (1.0 - fraction)
                + pixels[upper].astype(np.float32) * fraction
            )
            extended.append(np.rint(blended).astype(np.uint8))

    timeline = np.concatenate(
        (np.stack(extended), pixels[SKULL_SOURCE_END_FRAME + 1 :]),
        axis=0,
    )
    loop_start = len(extended) + (
        LOOP_SOURCE_START_FRAME - SKULL_SOURCE_END_FRAME - 1
    )
    return timeline, loop_start


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
    source_frame_count = len(pixels)
    pixels, loop_start = build_timeline(pixels)
    frames: list[bytes] = []
    for frame in pixels:
        value = frame.astype(np.uint16)
        packed = ((value[..., 0] >> 3) << 11) | ((value[..., 1] >> 2) << 5) | (value[..., 2] >> 3)
        frames.append(packed.astype(">u2").tobytes())
    if not frames:
        raise ValueError("Source contains no video frames")
    write_pack(destination / "boot.opb", frames, fps, loop_start)
    write_pack(destination / "first.opb", [frames[0]], fps, 0)
    (destination / "first.rgb565").write_bytes(frames[0])
    Image.fromarray(pixels[0]).save(destination / "first.png")
    Image.fromarray(pixels[-1]).save(destination / "last.png")
    # MP4 is a small browser/phone preview, not the file decoded during boot.
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-video_size", f"{WIDTH}x{HEIGHT}", "-framerate", str(float(fps)),
        "-i", "-", "-an", "-c:v", "libx264", "-preset", "slow",
        "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(destination / "preview_240x280.mp4"),
    ], input=pixels.tobytes(), check=True)
    seam_error = float(
        np.abs(
            pixels[-1].astype(np.int16) - pixels[loop_start].astype(np.int16)
        ).mean()
    )
    report = {
        "source_name": source.name,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "width": WIDTH, "height": HEIGHT,
        "framing": "Portrait, original content shifted down 22 px; near-black footer removed; complete wordmark retained",
        "removed_footer_rows": BOTTOM_EMPTY_ROWS,
        "removed_footer_peak_rgb": discarded_peak,
        "fps_numerator": fps.numerator, "fps_denominator": fps.denominator,
        "source_frame_count": source_frame_count,
        "frame_count": len(frames), "duration_seconds": len(frames) / float(fps),
        "skull_source_end_frame": SKULL_SOURCE_END_FRAME,
        "skull_slowdown_factor": SKULL_SLOWDOWN_FACTOR,
        "skull_extension_frames": len(frames) - source_frame_count,
        "skull_extension_seconds": (len(frames) - source_frame_count) / float(fps),
        "pixel_format": "RGB565 big-endian, ST7789 wire order",
        "compression": "independent zlib frames, lossless after native RGB565 conversion",
        "raw_frame_bytes": WIDTH * HEIGHT * 2,
        "raw_pixel_bus_mbit_s": WIDTH * HEIGHT * 16 * float(fps) / 1_000_000,
        "loop_start_frame": loop_start,
        "loop_source_start_frame": LOOP_SOURCE_START_FRAME,
        "loop_frame_count": len(frames) - loop_start,
        "loop_seam_mean_absolute_rgb_error": seam_error,
        "loop_note": "Measured smoother final-logo loop begins at approved source frame 54; real-device recheck required.",
        "pack_bytes": (destination / "boot.opb").stat().st_size,
        "first_pack_bytes": (destination / "first.opb").stat().st_size,
        "preview_mp4_bytes": (destination / "preview_240x280.mp4").stat().st_size,
        "hardware_validation": "Display transport, colour order and orientation confirmed by 2026-10-30 device recording; revised timing and loop require recheck.",
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
