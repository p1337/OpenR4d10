# Mediatheken

## Nutzerfunktion

Der Browser-Tab **Mediatheken** durchsucht aktuelle öffentlich-rechtliche
Sendungen und bietet zwei ausdrücklich getrennte Wiedergabewege:

- **Im Browser ansehen** verwendet das HTML5-Videoelement des verbundenen
  Browsers.
- **Auf Gerät abspielen** übergibt eine bandbreitenärmere verfügbare Fassung an
  den einen zentralen `MpvEngine`; das Whisplay wechselt nach erfolgreichem
  Start in `PLAYER` und zeigt Sender, Titel, Ergebnisposition und Status.

In dieser Geräteansicht schaltet der rechte äußere Encoder beziehungsweise
Pfeil hoch/runter zyklisch durch die Ergebnisse derselben Suche und startet den
gewählten Beitrag unmittelbar. Der rechte Druck beziehungsweise Enter
pausiert oder setzt die reale Wiedergabe fort. Katalogsuche, Auswahl und
**Im Browser ansehen** verändern die Geräteansicht nicht.

Das SPI-Display spielt noch kein bewegtes Video. Diese Grenze bleibt bestehen,
bis Dekodierung, Audio-Synchronität, 10-FPS-Ausgabe und Eingabelatenz auf dem
realen Pi Zero 2 W gemessen wurden.

## Katalog und Sender

Der gemeinsame Adapter verwendet die dokumentierte, schlüssellose POST-Abfrage
des öffentlichen [MediathekViewWeb-Projekts](https://github.com/mediathekview/mediathekviewweb).
Die feste deutsche Auswahl besteht aus ARD, ZDF, ZDFinfo, ZDFneo, 3sat,
ARTE.DE, PHOENIX, ARD-alpha, tagesschau24, ONE, BR, HR, MDR, NDR, RBB, SR, SWR,
WDR und Deutsche Welle (`DW`). Verglichen wird der vollständige Kanalname ohne Teiltreffer; `SR` darf
beispielsweise niemals `SRF` einschließen.

Die Schnellwahlen sind nachvollziehbare aktuelle Suchprofile und keine
redaktionell erfundenen Empfehlungen:

- Neu
- Nachrichten
- Tatort & Krimi
- Dokumentationen
- Wissenschaft
- Terra X
- Harald Lesch
- Geschichte
- Natur

Ergebnisse sind nach dem gelieferten Veröffentlichungszeitpunkt absteigend
sortiert. Die offiziellen Programmseiten bestätigen unter anderem die
[aktuellen Tatort-Folgen](https://www.ardmediathek.de/ard/tatort),
[Terra X Harald Lesch](https://www.zdf.de/dokus/terra-x-harald-lesch-102) und
die thematisch gegliederten [ARTE-Dokumentationen](https://www.arte.tv/de/videos/dokumentationen-und-reportagen).

## Grenzen und Sicherheit

- ausschließlich HTTPS, keine eingebetteten Zugangsdaten und keine privaten
  oder lokalen Zieladressen;
- zehn Sekunden Zeitlimit, zwei MiB JSON, höchstens 30 öffentliche Ergebnisse;
- senderübergreifend höchstens 120 Rohzeilen, bevor der feste deutsche Filter
  und die 30-Ergebnisgrenze greifen;
- identische Suchprofile werden fünf Minuten lang in einem höchstens 16 Einträge
  großen Arbeitsspeicher-Cache wiederverwendet;
- Rohadressen bleiben prozesslokal und erscheinen nicht in Status, SQLite oder
  Backups;
- der lokale Videoendpunkt nimmt nur eine 24-stellige, bereits gecachte ID an
  und antwortet mit einer nicht cachebaren Weiterleitung; der Pi puffert oder
  proxyt keine große Videodatei;
- DRM, Anmeldung, Altersfreigabe, Geoblocking und Verfügbarkeitsfristen werden
  nicht umgangen.

Die Indexsuche ist eine komfortable technische Quelle, nicht die rechtliche
Verfügbarkeitszusage des Senders. Ein einzelner Beitrag kann daher trotz
Katalogtreffer bereits abgelaufen oder im jeweiligen Land nicht abspielbar sein.
