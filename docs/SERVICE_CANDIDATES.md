# Mögliche weitere Dienste

Stand: 31. Oktober 2026. Diese Liste ist eine technische Vorauswahl und kein
Installationsversprechen. Ein Dienst wird erst nach eigener Sicherheits-,
Lizenz-, Last- und Bedienprüfung in den Dienst-Store aufgenommen. Zugangsdaten
bleiben ausschließlich auf dem Gerät und niemals in Git, SQLite, Statusdaten,
Backups oder Logs.

Legende: **A** = mit vorhandener Architektur gut umsetzbar, **B** = zusätzlicher
Adapter, Dienst oder Hardware nötig, **C** = erst nach Produkt-, Lizenz- oder
Rechtsprüfung. `lokal` bedeutet ohne Hersteller-Cloud; `Konto` bedeutet einen
isolierten Adapter mit eigener Benutzerkennung und `systemd`-Credentials.

Podcasts sind seit 0.10.37 kein Kandidat mehr: Der native Dienst kann
öffentliche RSS-/Atom-Feeds abonnieren, begrenzt aktualisieren, durchsuchen und
Audio-Episoden über den vorhandenen Player abspielen.

## Energie, Photovoltaik und Smart Home

| # | Kandidat | Klasse | Nutzen und realistische Anbindung |
|---:|---|:---:|---|
| 1 | Anker SOLIX | A/B | PV-, Haus-, Netz-, Speicherleistung, Akkustand und Tagesenergie. Bevorzugt lokales Modbus TCP bei unterstützten Geräten; sonst klar gekennzeichneter Community-Cloudadapter mit lokal hinterlegtem Konto. |
| 2 | Home Assistant | A | Freigegebene Entitäten, Szenen und Automationen über lokale REST-/WebSocket-API; ideal als sichere Brücke zu vielen Herstellern. |
| 3 | MQTT | A | Sensorwerte, kurze Meldungen und Schalter über TLS-fähigen Broker; Topics müssen freigegeben werden. |
| 4 | OpenDTU / AhoyDTU | A | Lokale Balkonkraftwerk-Leistung, Ertrag und Wechselrichterstatus per HTTP/MQTT. |
| 5 | Fronius Solar API | A | Wechselrichter-, Smart-Meter- und Ertragswerte über die dokumentierte lokale HTTP-API. |
| 6 | Victron Venus OS | A/B | Batterie, Solarregler, Netz und Verbraucher über MQTT oder Modbus TCP im LAN. |
| 7 | SMA / ennexOS | B | PV- und Speicherwerte über dokumentiertes Modbus/SunSpec; genaue Gerätefreigabe nötig. |
| 8 | Shelly | A | Leistung, Energie und Schaltzustände über lokale RPC-Schnittstelle. |
| 9 | Tasmota | A | Gerätewerte und feste Schaltaktionen über MQTT oder lokale HTTP-Kommandos. |
| 10 | ESPHome | A | Sensoren und sichere Aktionen vorzugsweise über Home Assistant oder die native API. |
| 11 | Zigbee2MQTT | A | Zigbee-Sensoren, Schalter und Batteriestände über vorhandenen MQTT-Broker. |
| 12 | Z-Wave JS UI | B | Freigegebene Z-Wave-Werte und Aktionen über WebSocket/MQTT; eigener Controller nötig. |
| 13 | Tibber | B | Strompreis, Verbrauch und Pulse-Livewerte über offizielles Konto/API; Token nur lokal. |
| 14 | dynamische Strompreise | A/B | Börsen-/Tarifkurve und günstige Zeitfenster über offiziell lizenzierte Datenquelle. |
| 15 | Modbus-Energiezähler | B | Hausverbrauch und Einspeisung aus freigegebenen Registern via Modbus TCP/RTU. |
| 16 | NUT / USV | A | Akkustand, Netzbetrieb und Restlaufzeit einer vorhandenen USV im LAN. |
| 17 | Wallbox / OCPP | B/C | Ladezustand und begrenzte Start/Stopp-Aktionen; nur pro Modell und mit Sicherheitsgrenzen. |
| 18 | Wärmepumpe | B/C | Temperaturen, Verdichterstatus und Energie über offizielle lokale API, Modbus oder Home Assistant. |

## Sprache, Push-to-talk und Kommunikation

| # | Kandidat | Klasse | Nutzen und realistische Anbindung |
|---:|---|:---:|---|
| 19 | privates OpenR4d10-PTT | B | Direkt gekoppelte Geräte, eindeutige Sprechtaste, TLS und keine offenen öffentlichen Räume. |
| 20 | Mumble | B | Räume, Hören und echtes PTT über einen eigenen Server; Audioadapter getrennt vom Kern. |
| 21 | Matrix | B | Räume, Direktnachrichten und Sprachnachrichten; E2EE-Geräteverwaltung ist Pflicht. |
| 22 | SIP-Intercom | B | Haussprechstelle oder Nebenstelle über PJSIP; Echo- und Mikrofontest auf echter Hardware. |
| 23 | Meshtastic | B | Text, Knoten, Telemetrie und Position über ein separates LoRa-Gerät per USB/seriell. |
| 24 | Reticulum / LXMF | B/C | Unabhängige Textkommunikation über vorhandene Reticulum-Interfaces; Ressourcenbedarf testen. |
| 25 | Jami | B/C | Dezentrale Gespräche ohne eigenen Zentralserver; ARM64-Client und Bedienbarkeit prüfen. |
| 26 | Jitsi-Audioraum | C | WebRTC-Audioraum und PTT-artige Stummschaltung; für Pi Zero 2 W wahrscheinlich grenzwertig. |
| 27 | TeamSpeak | C | PTT und Kanäle nur über offiziell zulässige Client-/SDK-Lösung und passende Lizenz. |
| 28 | Discord | C | Nachrichten/Benachrichtigungen über offizielle App; kein Nutzerkonto automatisieren und keine verbotenen Selfbots. |
| 29 | Telegram / TDLib | B | Nachrichten und Sprachnachrichten mit lokaler TDLib-Anmeldung; Session bleibt im Adapter. |
| 30 | ntfy | A | Eigene Pushmeldungen, Alarmbestätigung und Text-to-Speech über einen eigenen oder freigegebenen Server. |
| 31 | Gotify | A | Lokale Pushmeldungen und Prioritäten; App-Token nur im isolierten Adapter. |
| 32 | Apprise-Brücke | B | Ein einheitlicher Benachrichtigungsausgang zu freigegebenen Zielen; Geheimnisse bleiben außerhalb des Kerns. |

## Kameras, Weltbilder und visuelle Dienste

| # | Kandidat | Klasse | Nutzen und realistische Anbindung |
|---:|---|:---:|---|
| 33 | eigene Snapshot-Kameras | A | Beliebig viele sortierbare öffentliche HTTPS-Bildquellen mit Name, Intervall und lokalem Re-Encode. |
| 34 | eigene MJPEG-Kameras | A/B | MJPEG live anzeigen; serverseitig nur einen Frame begrenzt dekodieren statt den Stream neu zu transcodieren. |
| 35 | RTSP-Kameras | B | Über `ffmpeg` kontrolliert Einzelbilder ziehen; keine ungeschützten Zugangsdaten in einer URL speichern. |
| 36 | ONVIF-Kameras | B | Lokale Discovery, Profile und Snapshot-URI; Zugangsdaten nur im Kameraadapter. |
| 37 | Windy Webcams | B | Weltweite Webcam-Suche nach Ort/Kategorie; offizieller API-Key und kurzlebige Bild-URLs nötig. |
| 38 | kommunale Verkehrskameras | A/B | Offizielle Straßen-/Pass-Webcams als kuratierte Kanäle, wenn Lizenz und Abrufintervall passen. |
| 39 | Bahnsteig-/Hafenkameras | B/C | Nur offiziell veröffentlichte Quellen; keine privaten oder personenbezogenen Kameras. |
| 40 | ISS-Livebild und Position | B | Offizielle NASA-/ESA-Quellen, aktuelle Position und Sichtbarkeitsfenster. |
| 41 | NASA Earth / EPIC | A/B | Aktuelle Erdansichten mit korrekter Quellenangabe und Cache. |
| 42 | NOAA Space Weather | A | Sonnenaktivität, Polarlichtwahrscheinlichkeit und Warnungen über offizielle Datenfeeds. |
| 43 | Blitzortung | B/C | Blitzkarte nur mit erlaubter API/Lizenz; keine HTML-Seite scrapen. |
| 44 | lokale Fotodiashow | A | Bilder aus einem geschützten lokalen Ordner oder einer explizit freigegebenen Quelle. |
| 45 | Immich-Fotorahmen | B | Freigegebenes Album oder aktuelle Favoriten über den eigenen Server; Token nur lokal. |

## Netzwerk, VPN und Betrieb

| # | Kandidat | Klasse | Nutzen und realistische Anbindung |
|---:|---|:---:|---|
| 46 | WireGuard-Client | A/B | Root-eigenes NetworkManager-Profil importieren, verbinden/trennen und Status anzeigen; private Schlüssel nie an Web/Kern geben. |
| 47 | OpenVPN-Client | B | Bestehendes NetworkManager-Profil schalten; Zertifikate und Schlüssel root-only. |
| 48 | Tailscale | B | Fernzugriff über offiziellen ARM64-Client; Konto-/Gerätebindung außerhalb des Kerns. |
| 49 | ZeroTier | B | Virtuelles LAN über offiziellen Client; Network-ID und Mitgliedschaft lokal verwalten. |
| 50 | Tor-Clientstatus | B/C | Nur Client-/Onion-Service-Status; ausdrücklich kein offenes Exit-Relay auf dem Radio. |
| 51 | Pi-hole / AdGuard Home | A | DNS-Status, Blockquote, letzte Warnungen und zeitlich begrenztes Pausieren über offizielle lokale API. |
| 52 | Uptime Kuma | A | Dienstzustände und Ausfälle aus einer vorhandenen Kuma-Instanz. |
| 53 | Prometheus / Netdata | A/B | Kleine, fest definierte Systemkennzahlen; keine frei eingebbaren Queries im Gerät. |
| 54 | Wake-on-LAN | A | Gespeicherte LAN-Geräte mit festem Aufweckknopf; keine beliebigen Netzwerkpakete. |
| 55 | NAS-Status | A/B | Speicher, Temperatur, SMART-Sammelstatus und Jobs über offizielle Synology-/QNAP-/TrueNAS-API. |
| 56 | Druckerstatus | A | Tinte/Toner, Papier und Warteschlange über IPP/CUPS im LAN. |
| 57 | Backupstatus | A/B | Letzter erfolgreicher Restic/Borg/Proxmox-Backupjob aus einer lesenden Statusquelle. |
| 58 | feste Wartungsaktionen | B | Neustart ausgewählter eigener Dienste über exakt erlaubte Helper; niemals eine freie Web-Shell. |

## Standort, Mobilität und Umgebung

| # | Kandidat | Klasse | Nutzen und realistische Anbindung |
|---:|---|:---:|---|
| 59 | lokale SSID-Ortsprofile | A | Opt-in-Zuordnung sichtbarer SSID/BSSID-Fingerprints zu Namen wie Zuhause/Werkstatt; vollständig lokal. |
| 60 | externe WLAN-Geolokalisierung | C | Technisch möglich, überträgt aber BSSIDs an einen Anbieter und braucht meist einen API-Key; standardmäßig aus. |
| 61 | USB-GNSS / GPSD | B | Position, Höhe, Geschwindigkeit und Uhrzeit mit eigenem USB-/UART-Empfänger. |
| 62 | lokale Geofencing-Aktionen | B | Anzeige-/Dienstprofil anhand GPS oder lokalem Ortsprofil, ohne Position in die Cloud zu senden. |
| 63 | ÖPNV / GTFS-Realtime | A/B | Abfahrten, Verspätungen und Haltestellenfavoriten aus offiziellen Verkehrsverbund-Feeds. |
| 64 | Bahn-Abfahrten | B | Favorisierte Bahnhöfe über eine offiziell erlaubte DB-/GTFS-Schnittstelle. |
| 65 | GPX-Fahrradnavigation | B | Offline-Track, Abbiegehinweise und Restdistanz; Kartenkacheln vorher begrenzt laden. |
| 66 | BLE-Fahrradsensoren | B | Herzfrequenz, Trittfrequenz, Geschwindigkeit und Leistung über standardisierte GATT-Profile. |
| 67 | ADS-B lokal | B/C | Flugzeuge eines eigenen `readsb`/dump1090-Empfängers anzeigen; keine schwere Dekodierung im UI-Kern. |
| 68 | AIS lokal | B/C | Schiffe eines eigenen AIS-Empfängers; Funk- und Standortrecht beachten. |
| 69 | Luftqualität | A/B | CO₂, PM2.5, VOC und Temperatur aus lokalen MQTT-/BLE-/I²C-Sensoren. |
| 70 | Pollen und UV | A/B | Amtliche oder offiziell lizenzierte Warn- und Vorhersagedaten nach gewählter Region. |
| 71 | Erdbeben | A | Aktuelle Ereignisse aus einem offiziellen GeoJSON-Feed, Entfernung lokal berechnen. |
| 72 | Strahlungsmessgerät | B | CPM/Dosis eines eigenen seriellen oder MQTT-Sensors; keine medizinische Interpretation. |

## Medien, Information und Werkzeuge

| # | Kandidat | Klasse | Nutzen und realistische Anbindung |
|---:|---|:---:|---|
| 73 | OpenSubsonic / Navidrome | A | Eigene Musik, Suche, Favoriten, Playlists und Cover per Direktstream. |
| 74 | Jellyfin Audio | A/B | Musik und Hörbücher vom eigenen Server; Pi bleibt Client und transcodiert nicht. |
| 75 | Audiobookshelf | B | Hörbücher, Kapitel, Hörposition und Podcasts über eigenen Server. |
| 76 | MPD | A | Sehr leichte Fernbedienung eines vorhandenen Music Player Daemon im LAN. |
| 77 | Snapcast | B | Raumwahl, Lautstärke und synchrones Multiroom-Audio; Dauerlast messen. |
| 78 | Kodi-Fernbedienung | A | Bibliothek, Cover, Wiedergabe und Lautstärke per JSON-RPC. |
| 79 | Music Assistant | B | Zentrale Musikauswahl und Playergruppen über vorhandene Installation. |
| 80 | DLNA / OpenHome | B | Audio im LAN empfangen oder einen Renderer steuern; Discovery sauber begrenzen. |
| 81 | AirPlay-Empfänger | B/C | Audio vom Handy über gepflegten kompatiblen Empfänger; Paket- und Protokollpflege prüfen. |
| 82 | Internet Archive Audio | B/C | Öffentliche Sammlungen durchsuchen; Rechte und Metadaten jedes Objekts beachten. |
| 83 | Radio Browser | B | Sender bequem suchen und übernehmen; URLs vor Speicherung prüfen und Ausfälle sichtbar machen. |
| 84 | CalDAV / ICS | A/B | Termine, Timer und Erinnerungen; Schreibzugriff getrennt und ausdrücklich bestätigen. |
| 85 | Nextcloud | B | Kalender, Benachrichtigungen, Dateien und Audio mit lokalem App-Passwort. |
| 86 | Paperless-ngx | A/B | Neue Dokumente, Tags und Inbox-Zähler vom eigenen Server; keine Dokumentinhalte ungefragt anzeigen. |
| 87 | Home Assistant Assist | B | Lokale Sprachbefehle über eine bestehende Assist-Pipeline; keine permanente Cloud-Aufzeichnung. |
| 88 | Offline-Sprachsteuerung | B | Kleine feste Befehlsmenge und Vorlesefunktion; CPU- und Mikrofonlast auf dem Zero 2 W testen. |

## Empfohlene nächste Ausbaureihenfolge

1. **SOLIX-Monitor** über den jetzt definierten Adaptervertrag; zuerst das
   konkrete Anker-Modell feststellen und lokalen Modbus bevorzugen.
2. **Freie Kameraliste** statt der bisherigen zwei temporären Slots: Name,
   Typ `snapshot`/`mjpeg`, Intervall, Reihenfolge, Aktivierung und Löschen.
3. **WireGuard-Client** über NetworkManager mit einem festen root-eigenen
   Import-/Schalt-Helper; niemals Schlüssel durch die normale Status-API.
4. **lokale SSID-Ortsprofile**, weil sie ohne externes Tracking funktionieren.
5. **Mumble oder privates OpenR4d10-PTT** als erster echter PTT-Dienst.
6. Danach Home Assistant, MQTT und OpenDTU, weil damit viele weitere Geräte
   ohne je einen neuen Herstelleradapter sichtbar werden.

## Technische Auswahlregeln

1. Bevorzugt werden offizielle, dokumentierte lokale APIs und offene Protokolle.
2. Der Pi Zero 2 W dekodiert Audio/Bilder, führt aber keine schwere dauerhafte
   Video- oder Medientranscodierung aus.
3. Jeder Dienst muss ohne Zugangsdaten installierbar sein und seinen
   Konfigurationsbedarf ehrlich anzeigen.
4. Geheimnisse gehören weder ins Repository noch in Statusantworten, Logs,
   Backups, URLs oder Vorschaubilder.
5. Audio-Dienste verwenden das vorhandene Audio-Ownership; visuelle Dienste
   unterbrechen laufende Musik nicht.
6. Jeder Dienst benötigt eine kompakte Geräteansicht, eine suchbare Webliste,
   definierte Encoderaktionen und einen sauberen Deinstallationspfad.
7. Kameras dürfen nur eigene, öffentliche oder ausdrücklich freigegebene
   Quellen verwenden. Private Netzbereiche bleiben standardmäßig gesperrt.
8. Standort aus WLAN-Umgebung ist ausschließlich opt-in. Die Standardlösung
   vergleicht lokal gespeicherte Fingerprints und lädt keine BSSIDs hoch.

## Primärquellen für die spätere Detailprüfung

- [Anker SOLIX Official Home Assistant integration](https://github.com/anker-charging/ha-anker-solix-official)
- [Community Anker SOLIX Python library](https://github.com/thomluther/anker-solix-api)
- [Home Assistant REST API](https://developers.home-assistant.io/docs/api/rest/)
- [Windy Webcams API](https://api.windy.com/webcams/docs)
- [NetworkManager WireGuard settings](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nm-settings-nmcli.html)
- [ONVIF profiles](https://www.onvif.org/profiles/)
- [OpenSubsonic API](https://opensubsonic.netlify.app/docs/opensubsonic-api/)
- [Jellyfin networking](https://jellyfin.org/docs/general/post-install/networking/)
- [Audiobookshelf API](https://api.audiobookshelf.org/)
- [Snapcast JSON-RPC](https://github.com/snapcast/snapcast/blob/develop/doc/json_rpc_api/control.md)
- [Meshtastic serial integration](https://meshtastic.org/docs/configuration/module/serial/)
- [Matrix Client-Server API](https://spec.matrix.org/latest/client-server-api/)
