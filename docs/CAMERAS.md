# Camera service

OpenR4d10 keeps an ordered camera library in the existing non-secret SQLite
state. The browser can add, refresh, reorder and delete up to 100 sources.
Every retrieved frame is decoded with Pillow, checked for a 40-megapixel
maximum, reduced to at most 640 × 480 and re-encoded as a local JPEG before it
is served. Remote camera bytes are never proxied directly.

Supported credential-free source types:

- `snapshot`: one HTTP(S) image, bounded to 5 MiB;
- `mjpeg`: the first complete JPEG from an HTTP(S) multipart stream, bounded
  to 5 MiB and a ten-second connection timeout;
- `rtsp`: one frame through the fixed `/usr/bin/ffmpeg` command, TCP transport,
  a 15-second process timeout and a 5-MiB output limit.

Persistent URLs may not contain user information or a query string. This
prevents passwords, signed links and access tokens from entering SQLite,
status responses, backups or logs. Authenticated private RTSP cameras and
ONVIF discovery must use a separate service adapter whose credentials stay in
a root-owned 0600 file. Windy likewise requires the user's own API key in that
adapter. These modes are not reported as ready until their adapter completes a
real handshake.

Curated public cameras require a stable official image or stream URL, clear
permission for automated display, a documented attribution and a measured
refresh interval. A city name or an embeddable HTML player is not enough. The
repository therefore does not invent fifty camera URLs or scrape EarthCam,
YouTube, municipal pages or other sites whose media contract is unknown.
