# DWD weather loops

OpenR4d10 uses the public DWD Web Map Service at
`https://maps.dwd.de/geoserver/dwd/wms`. The capabilities document is the
single source of available timestamps; no image timestamp is guessed.

Initial products:

- default channel 1: official DWD rain-radar animation for Germany at
  `https://www.wettergefahren.de/DWD/wetter/radar/Radarfilm_WEB_DL.gif`
- default channel 2: Europe satellite crop from the WMS layer
  `Satellite_meteosat_1km_euat_rgb_day_hrv_and_night_ir108_3h`
- title reported by DWD: `Satellitenbild METEOSAT (RGB) Europa gesamt 3h`
- update interval reported by DWD: three hours
- Europe crop: `30,-25,72,45`
- visible credit: `DWD` for radar and `DWD / EUMETSAT` for satellite

The DWD integration guide permits WMS images in sites and asks clients not to
refresh more often than every five minutes. The radar source is the image linked
by DWD's own Radarfilm page. OpenR4d10 applies the same 300-second floor to both
sources, keeps at most eight usable frames and never points browser image
elements at either remote source. GIF and WMS responses are size-limited,
decoded with Pillow and re-encoded as local JPEGs. Invalid frames or missing WMS
timestamps are skipped. If the network or DWD is unavailable, the last valid
local frames remain available.

The DWD source and use references checked on 2026-10-31 are:

- [DWD WMS capabilities](https://maps.dwd.de/geoserver/dwd/wms?service=WMS&request=GetCapabilities&version=1.3.0)
- [DWD Radarfilm page](https://www.wettergefahren.de/wetter/deutschland/aktuell/radarfilm.html)
- [DWD Radarfilm GIF](https://www.wettergefahren.de/DWD/wetter/radar/Radarfilm_WEB_DL.gif)
- [DWD guide for embedding WMS services](https://www.dwd.de/DE/wetter/warnungen_aktuell/objekt_einbindung/einbindung_karten_geodienste.pdf?__blob=publicationFile&v=14)
- [DWD copyright and source attribution](https://kunden.dwd.de/agroprog/STYLES/copyright.jsp)

Weather channel records contain a name, stable non-secret external ID, source
kind, source text, optional numeric bounding box and persistent position. They
never contain credentials, tokens or arbitrary user-provided remote URLs. A
guarded one-time upgrade changes an existing untouched Germany default to the
fixed reviewed radar source without recreating a deleted default or changing
user order. Custom satellite crops remain restricted to the published layer
coverage: latitude 23–77 degrees and longitude -54–54 degrees.
