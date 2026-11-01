# Mediatheken

## Nutzerfunktion

Der Browser-Tab **Mediatheken** durchsucht aktuelle öffentlich-rechtliche
Sendungen und bietet drei ausdrücklich getrennte Wiedergabewege:

- **Im Browser ansehen** verwendet das HTML5-Videoelement des verbundenen
  Browsers.
- **Audio auf Gerät** übergibt die kleinste verfügbare Senderfassung an den
  einen zentralen `MpvEngine`; das Whisplay wechselt nach erfolgreichem Start
  in `PLAYER` und zeigt Sender, Titel, Ergebnisposition und Status. mpv erhält
  dabei ausdrücklich `vid=no`, sodass keine Videospur im Hintergrund dekodiert
  wird.
- **Video auf Gerät** verwendet dieselbe kleinste Fassung und denselben
  `MpvEngine`, zeigt aber zusätzlich das wirklich wiedergegebene Videobild auf
  dem Whisplay und aktiviert dafür genau bei diesem Ladeweg `vid=auto`.

In dieser Geräteansicht schaltet der rechte äußere Encoder beziehungsweise
Pfeil hoch/runter zyklisch durch die Ergebnisse derselben Suche und startet den
gewählten Beitrag unmittelbar. Der rechte Druck beziehungsweise Enter
pausiert oder setzt die reale Wiedergabe fort. Der gewählte Audio-/Video-Modus
bleibt beim Wechsel erhalten. Katalogsuche, Auswahl und **Im Browser ansehen**
verändern die Geräteansicht nicht.

Die Gerätequelle wird immer in der Reihenfolge `url_video_low`, `url_video`,
`url_video_hd` gewählt; HD wird auf dem 240-x-280-Gerät nie bevorzugt. Im
Video-Modus bleibt mpv die einzige Bild-, Ton- und Zeitquelle. Seine
Software-Screenshots werden ohne Warten über dieselbe private IPC angefordert,
bei laufendem Video höchstens 25-mal pro Sekunde aus einer einzelnen JPEG-Datei
unter `/run/openr4d10` übernommen und sofort gelöscht. Nur der 240-x-175-Pixel-
Videobereich von x=0 bis x=239 und y=105 bis y=279 wird in diesem Takt per SPI
übertragen; Kopfzeile, Status und alle
anderen UI-Ansichten behalten die normale Vollbildgrenze von 10 FPS. Auch
Skalierung und RGB565-Konvertierung bearbeiten pro Videoframe nur
diese Teilfläche und rufen den vollständigen UI-Renderer nicht auf. Es gibt keinen zweiten
ffmpeg-/mpv-Prozess und keine dauerhaften Videoframes unter `/var/lib`.
Pausieren hält deshalb Bild und Ton gemeinsam an. Ein fehlender oder verspäteter
Frame blockiert weder Ton noch Eingaben; der Renderer behält das letzte gültige
Bild. Während Pause bleibt dieses Bild ohne nutzlose Neuzeichnung stehen;
die ebenfalls asynchronen mpv-Antworten werden begrenzt und nicht blockierend
aus dem privaten Steuerkanal entfernt.

Das laufende Video ist die einzige Medienausnahme ohne Seiten- und Unterrand.
Es füllt die gesamte untere Displayfläche bis zur letzten Pixelzeile; ein
mittiger Zuschnitt ist dafür beabsichtigt. Logos, Wetterbilder und andere
Medien behalten die normale Maske und ihre Ränder.

Beim Ersetzen eines laufenden Beitrags ordnet der Player jedes mpv-
`start-file`/`end-file`-Paar über dessen `playlist_entry_id` zu. Ein verspätetes
Endereignis der vorherigen Quelle darf dadurch den bereits laufenden neuen
Beitrag nicht mehr fälschlich als gestoppt melden oder dessen Videotakt
abschalten. Die neue ID wird bereits aus der erfolgreichen `loadfile`-Antwort
übernommen, weil mpv 0.40 diese Antwort vor dem alten Endereignis sendet;
`start-file` bestätigt anschließend den laufenden Zustand.

Auf Raspberry Pi OS Trixie wird die Videospur mit dem dort tatsächlich
unterstützten mpv-0.40-Wert `--video=auto` aktiviert. `--video=yes` ist auf
diesem Ziel ungültig und wird durch einen Vertragstest ausgeschlossen.

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
- der öffentliche Zustand enthält nur den aktiven Modus `audio` oder `video`,
  niemals die Gerätequelle;
- der lokale Videoendpunkt nimmt nur eine 24-stellige, bereits gecachte ID an
  und antwortet mit einer nicht cachebaren Weiterleitung; der Pi puffert oder
  proxyt keine große Videodatei;
- DRM, Anmeldung, Altersfreigabe, Geoblocking und Verfügbarkeitsfristen werden
  nicht umgangen.

Die Indexsuche ist eine komfortable technische Quelle, nicht die rechtliche
Verfügbarkeitszusage des Senders. Ein einzelner Beitrag kann daher trotz
Katalogtreffer bereits abgelaufen oder im jeweiligen Land nicht abspielbar sein.

## Geräte-Suchlauf, Puffer und Verlauf

Der obere linke Encoder bleibt ausschließlich für die Lautstärke zuständig. Der
untere linke Encoder spult je Rastung zunächst 15 Sekunden. Sobald der
aufsummierte Sprung mehr als eine Minute beträgt, zählen weitere Rastungen in
derselben Richtung minutenweise. Schnelle Eingaben werden sichtbar gesammelt
und nach einer kurzen Ruhephase als genau ein relativer mpv-Sprung ausgeführt.

Der gelbe Fortschrittsglow am unteren Bildrand folgt der echten
Abspielposition. Seine grüne Fortsetzung zeigt ausschließlich den tatsächlich
von mpv vorgeladenen Bereich. Gesehene Folgen und Favoriten werden ohne
Medien-URL in SQLite gespeichert. Ein PTT-Druck im Mediathek-Player setzt oder
entfernt einen Favoriten mit einer Wiedereinstiegsstelle 15 Sekunden vor der
aktuellen Position. Ungesehene Folgen bleiben in der Auswahl vorn; gesehene
Folgen erscheinen zusätzlich im Archiv.
## Geräte-Gruppenauswahl

Wenn in `PLAYER` noch kein Medium läuft, ist die lokalisierte Gruppenauswahl
direkt die normale Geräteansicht. Es gibt dort keinen vorgeschalteten
`LOCAL MEDIA`-/`LM`-Platzhalter und keinen notwendigen PTT-Zwischenschritt. Der
rechte äußere Encoder markiert Favoriten oder eine der kuratierten
Suchsammlungen; der rechte Druck startet die markierte Gruppe. Ein zwei
Sekunden gehaltener physischer Whisplay-PTT-Taster bleibt als alternativer
Schnellzugriff auf dieselbe, nicht duplizierte Auswahl erhalten.

Beschriftungen und Suchbegriffe folgen der Gerätesprache (`de`, `en`, `pl`,
`fr` oder `es`). MediathekView stellt kein verlässliches Sprachfeld bereit;
deshalb ist die sprachspezifische Suche der durchsetzbare Filter, während die
freigegebene Senderliste unverändert bleibt.

Die Auswahl stellt die begrenzte Netzabfrage in eine Worker-Queue und hält
Encoder/PTT dadurch unmittelbar ansprechbar. Das erste Video und jeder weitere
Kanalschritt werden aus der aufgelösten Ergebnismenge zufällig gewählt.
Favoriten werden anhand ihrer stabil gespeicherten Titel-/Inhaltsidentität neu
aufgelöst; ablaufende Medienadressen werden nie persistiert. Das Verlassen von
`PLAYER` verwirft eine noch laufende Gruppenabfrage, bevor sie Audio oder Video
übernehmen kann.
