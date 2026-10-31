# DWD satellite weather

OpenR4d10 uses the public DWD Web Map Service at
`https://maps.dwd.de/geoserver/dwd/wms`. The capabilities document is the
single source of available timestamps; no image timestamp is guessed.

Initial product:

- layer: `Satellite_meteosat_1km_euat_rgb_day_hrv_and_night_ir108_3h`
- title reported by DWD: `Satellitenbild METEOSAT (RGB) Europa gesamt 3h`
- update interval reported by DWD: three hours
- default channel 1: Germany crop, WMS 1.3 EPSG:4326 axis-order bounding box
  `47,5,55.5,16` (south, west, north, east)
- default channel 2: Europe crop `30,-25,72,45`
- visible credit: `DWD / EUMETSAT`

The DWD integration guide permits WMS images in sites and asks clients not to
refresh more often than every five minutes. OpenR4d10 therefore caches the
capabilities response for at least 300 seconds, downloads at most eight recent
usable frames per channel and never points browser image elements at the remote
service. Every response is size-limited, decoded with Pillow and re-encoded as
a local JPEG. A missing WMS timestamp is skipped. If the network or DWD is
unavailable, the last valid local frames remain available.

The DWD source and use references checked on 2026-10-31 are:

- [DWD WMS capabilities](https://maps.dwd.de/geoserver/dwd/wms?service=WMS&request=GetCapabilities&version=1.3.0)
- [DWD guide for embedding WMS services](https://www.dwd.de/DE/wetter/warnungen_aktuell/objekt_einbindung/einbindung_karten_geodienste.pdf?__blob=publicationFile&v=14)
- [DWD copyright and source attribution](https://kunden.dwd.de/agroprog/STYLES/copyright.jsp)

Weather channel records contain only a name, a generated non-secret external
ID, a numeric bounding box, source text and persistent position. They never
contain credentials, tokens or remote user-provided URLs. The Germany and
Europe defaults are seeded exactly once so deletions and reordering survive
updates. Custom crops are restricted to the coverage published for the layer:
latitude 23–77 degrees and longitude -54–54 degrees.
