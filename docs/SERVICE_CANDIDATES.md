# Mögliche weitere Dienste

Stand: 31. Oktober 2026. Diese Liste ist eine technische Vorauswahl, kein
Installationsversprechen. Ein Dienst wird erst nach eigener Sicherheits-,
Lizenz-, Last- und Bedienprüfung in den Dienst-Store aufgenommen. Zugangsdaten
bleiben immer ausschließlich auf dem Gerät.

## Priorität A – hoher Nutzen, gut für den Pi Zero 2 W

| Kandidat | Nutzen am Gerät | Anbindung | Aufwand / Grenze |
|---|---|---|---|
| Podcasts | Abonnieren, Cover, Kapitel, Tempo, Fortsetzen | RSS/Atom und Podcasting-2.0-Tags | niedrig; Downloads und Speicherlimit nötig |
| Home Assistant | Zustände anzeigen, Szenen und Geräte schalten | lokale REST-/WebSocket-API mit eigenem Token | niedrig bis mittel; nur freigegebene Entitäten |
| MQTT | Sensorwerte, kurze Meldungen, Schalter und Automationen | TLS-fähiger MQTT-Client | niedrig; Broker-Zugang lokal konfigurieren |
| OpenSubsonic / Navidrome | eigene Musik, Suche, Favoriten, Playlists, Cover | OpenSubsonic-API | mittel; API-Schlüssel lokal, Audio per Direktstream |
| Jellyfin Audio | eigene Musik und Hörbücher von einem vorhandenen Server | Jellyfin-HTTP-API und Direktstream | mittel; der Pi ist Client, nicht Transcoding-Server |
| Audiobookshelf | Hörbücher/Podcasts, Kapitel und Hörposition | Server-API mit Bearer-Token | mittel; API-Dokumentation ist derzeit nicht vollständig aktuell |
| MPD | kompakte Fernbedienung für einen Music Player Daemon | MPD-Protokoll | niedrig; besonders sinnvoll im LAN |
| Snapcast | synchrones Multiroom-Audio, Raum- und Lautstärkewahl | Snapclient plus JSON-RPC-Steuerung | mittel; zusätzliche dauerhafte Audiolast messen |
| Kalender / ICS / CalDAV | nächste Termine, Timer und Erinnerungen | ICS lesend, optional CalDAV | niedrig bis mittel; Schreibzugriff separat bestätigen |
| DWD-Warnungen | amtliche Warnlage zusätzlich zu Radar/Satellit | DWD Open Data | niedrig; bestehenden Wetterdienst erweitern |

## Priorität B – attraktiv, aber zusätzliche Hardware oder Konten

| Kandidat | Nutzen am Gerät | Anbindung | Aufwand / Grenze |
|---|---|---|---|
| Meshtastic | Text, Knotenstatus, Telemetrie und Position aus einem LoRa-Mesh | USB/serielles Protobuf oder privates MQTT | mittel; separates Meshtastic-Funkgerät erforderlich |
| Matrix | Räume, Direktnachrichten, Sprachnachrichten und später PTT-artige Bedienung | standardisierte Client-Server-API | hoch; sichere Token- und E2EE-Geräteverwaltung nötig |
| SIP-Intercom | Anruf, Gegensprechen und PTT-nahe Nutzung | PJSIP/SIP-Konto | hoch; Echo, Mikrofonrouting und Netzsicherheit prüfen |
| Nextcloud | Kalender, Dateien, Benachrichtigungen und Audio aus eigener Cloud | WebDAV/CalDAV/OCS | mittel; App-Passwort lokal speichern |
| Kodi-Fernbedienung | Wiedergabe, Bibliothek, Cover und Lautstärke eines Kodi-Systems | JSON-RPC im LAN | niedrig bis mittel; OpenR4d10 bleibt Fernbedienung |
| Music Assistant | zentrale Musikauswahl und Player-Gruppen im Smart Home | Music-Assistant-/Home-Assistant-Schnittstelle | mittel; API-Stabilität vorher prüfen |
| AirPlay-Empfänger | Ton vom Handy auf dem Whisplay-Lautsprecher | kompatibler lokaler Empfängerdienst | mittel; Protokoll- und Paketpflege prüfen |
| DLNA/OpenHome-Renderer | Audio aus üblichen Medien-Apps im LAN empfangen | UPnP/OpenHome | mittel; Discovery und sauberes Audio-Ownership nötig |
| USB-DAB+-Empfänger | echtes DAB+ mit Senderliste und Radiotext | unterstützter USB-Tuner | hoch; CPU-Last und konkreten Tuner zuerst verifizieren |
| RTL-SDR-Scanner | lokaler, legal konfigurierter Empfang und Spektrum | USB-SDR plus begrenzter lokaler Demodulator | hoch; Frequenzen, Bandbreite und Rechtslage strikt begrenzen |

## Priorität C – erst nach genauer Produkt- und Rechtsprüfung

- NINA-/Katastrophenschutzmeldungen: sehr sinnvoll, aber ausschließlich über
  eine offiziell dokumentierte und dauerhaft zulässige Quelle.
- Internet-Archive-Audio: öffentliche Sammlungen sind interessant; Rechte und
  Metadaten unterscheiden sich pro Objekt.
- Radio-Browser/Senderverzeichnis: bequem zum Hinzufügen neuer Sender, aber
  Drittanbieter-Verfügbarkeit, falsche URLs und Moderation müssen abgefangen
  werden.
- Sprachassistent: lokale Befehle sind denkbar; permanentes Cloud-Mikrofon und
  ungefragte Audioübertragung bleiben ausgeschlossen.
- Fahrrad-Sensoren: BLE-Herzfrequenz, Geschwindigkeit, Trittfrequenz oder
  Reifendruck sind möglich, sobald konkrete Profile und Sensoren bekannt sind.

## Technische Auswahlregeln

1. Bevorzugt werden offizielle, dokumentierte lokale APIs und offene Protokolle.
2. Der Pi Zero 2 W dekodiert Audio, führt aber keine schwere Medientranscodierung aus.
3. Jeder Dienst muss ohne Zugangsdaten installierbar sein und seinen
   Konfigurationsbedarf klar anzeigen.
4. Geheimnisse gehören weder ins Repository noch in Statusantworten, Logs,
   Backups oder Vorschaubilder.
5. Audio-Dienste verwenden das vorhandene Audio-Ownership: Ein neuer
   Play-Befehl ersetzt die alte Audioquelle; visuelle Dienste unterbrechen sie nicht.
6. Jeder Dienst benötigt eine kompakte Geräteansicht, eine suchbare Webliste,
   definierte Encoderaktionen und einen sauberen Deinstallationspfad.

## Primärquellen für die spätere Detailprüfung

- [Home Assistant REST API](https://developers.home-assistant.io/docs/api/rest/)
- [OpenSubsonic API](https://opensubsonic.netlify.app/docs/opensubsonic-api/)
- [Jellyfin networking](https://jellyfin.org/docs/general/post-install/networking/)
- [Audiobookshelf API](https://api.audiobookshelf.org/)
- [Snapcast JSON-RPC](https://github.com/snapcast/snapcast/blob/develop/doc/json_rpc_api/control.md)
- [Meshtastic serial integration](https://meshtastic.org/docs/configuration/module/serial/)
- [Meshtastic MQTT integration](https://meshtastic.org/docs/software/integrations/mqtt/)
- [Matrix Client-Server API](https://spec.matrix.org/latest/client-server-api/)
