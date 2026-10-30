# Assets

The semantic text boot-sequence manifest remains in `boot/text-sequence.toml`.
The approved animation source is tracked as
`boot/OpenR4d10_APPROVED_ORIGINAL.mp4`; its SHA-256 and conversion provenance
are recorded in `../boot/assets/manifest.json`.

The native, losslessly frame-compressed RGB565 files used by the Pi are stored
under the repository's top-level `boot/assets/` directory. They are 240 x 280,
use the verified ST7789 wire order and are checked by the native verifier before
installation. See `../boot/README.md` for framing, timing, source attribution
and the remaining physical-hardware validation.
