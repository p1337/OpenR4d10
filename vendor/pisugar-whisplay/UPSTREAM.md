# PiSugar Whisplay sound-card source

This directory contains an unmodified, deliberately pinned subset of the
official [PiSugar/Whisplay](https://github.com/PiSugar/Whisplay) repository.

- upstream commit: `736975188ebbe146d319e450aad19c218a310611`
- upstream commit date: 2026-10-30
- source archive: `https://github.com/PiSugar/Whisplay/archive/736975188ebbe146d319e450aad19c218a310611.tar.gz`
- source archive SHA-256: `1fac1045fb763de52eed5aa23704d7752ff5e024c9ce64692cf9832261cfb88a`
- license: Apache License 2.0; see `LICENSE`

Copied without modification from that revision:

- `LICENSE`
- `README.md`
- `audio/whisplay-soundcard/`, stored here as `audio/`

OpenR4d10 invokes `audio/scripts/install.sh` only after its own strict Debian
13, aarch64 and Raspberry Pi Zero 2 W platform gate. The vendor installer
builds the unified WM8960/ES8389 driver for the running kernel and configures
the official `whisplay-soundcard` device-tree overlay.

To update this source, review a specific upstream commit, download its GitHub
archive, verify and record the complete archive SHA-256, replace only the
listed files, run the full OpenR4d10 test suite and test the resulting driver
on the physical target before changing the pinned revision above.
