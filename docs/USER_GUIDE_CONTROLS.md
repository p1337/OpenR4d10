# OpenR4d10 Bedien- und Diensthandbuch

Diese Anleitung beschreibt die heute implementierte Bedienung des physischen
OpenR4d10 und der dazugehörigen Browseroberfläche. Sie ist die verbindliche
Nutzerübersicht; technische Entwicklerdetails bleiben in
[`ARCHITECTURE.md`](ARCHITECTURE.md), [`HARDWARE.md`](HARDWARE.md) und
[`MENU_TREE.md`](MENU_TREE.md).

Die zugehörigen, frei skalierbaren Bediengrafiken sind:

- [`controls-overview.svg`](../web/controls-overview.svg) – Hardware und
  Grundbelegung;
- [`service-controls.svg`](../web/service-controls.svg) – weiß hinterlegter,
  druckbarer Bedienvergleich aller 16 aktuell aktivierten Dienste: 13 sind
  bereit, drei benötigen noch Konfiguration. Jede Zeile
  zeigt links die reale Whisplay-Front mit einem direkt vom laufenden Gerät
  aufgenommenen Dienstbild und rechts ausschließlich die dort gültigen
  Funktionen. RSS und Webcams werden ausdrücklich als browser-only gezeigt,
  statt eine noch nicht vorhandene native Ansicht zu erfinden. Dasselbe gilt
  für aktivierte Adapterverträge ohne Geräteansicht; ihr Konfigurationsbedarf
  bleibt in der Tafel sichtbar.

Die Hardwaregrafik bildet ausschließlich den belegten realen Platinenstack ab:
Whisplay vorne, Raspberry Pi Zero 2 W in der Mitte und PiSugar 3 hinten. Ihre
Whisplay-Front- und Rückseitenmerkmale sowie die PiSugar-Taster stammen aus den
offiziellen Herstelleransichten. Sie erfindet weder ein Gehäuse noch seitliche
Tasten. Die beiden ALPS-Doppelencoder stehen in einem klar getrennten,
gestrichelten Planungsbereich, weil sie noch nicht montiert, vermessen oder
elektrisch zugeordnet sind. Die Grafik ist druckfähig, aber ausdrücklich keine
Bohr-, Gehäuse- oder Leiterplattenschablone.

Verwendete Primärquellen:

- [PiSugar Whisplay Overview](https://docs.pisugar.com/docs/product-wiki/whisplay/overview)
  mit Herstelleransichten von Vorder- und Rückseite;
- [PiSugar3 Series / PCB instructions](https://docs.pisugar.com/docs/product-wiki/battery/pisugar3/pisugar-3-series)
  mit Stackreihenfolge und Kennzeichnung von Power-, Custom- und Reset-Taster.

## Ein Bedienmodell für das ganze Gerät

OpenR4d10 folgt in jedem Dienst demselben Grundmuster:

| Hardware | Standardfunktion | Browser |
| --- | --- | --- |
| linker Encoder, äußerer Ring | Lautstärke in 10-%-Schritten | `W` / `S` |
| linker Encoder, innerer Ring | Sekundärfunktion des Dienstes, sonst SQL | `A` / `D` |
| linker Encoder, Druck | bewusst frei | keine Aktion |
| rechter Encoder, äußerer Ring | Kanal, Eintrag oder Listenauswahl | Pfeil hoch / runter |
| rechter Encoder, innerer Ring | vorheriger oder nächster Dienst | Pfeil links / rechts |
| rechter Encoder, kurzer Druck | auswählen, Play oder Pause | `Enter` |
| rechter Encoder, 2 Sekunden | Quick-Menü des Dienstes | virtueller langer Druck |
| Whisplay-Hardwaretaste | PTT-Kontext; in Menüs immer zurück | `Backspace` halten |
| PiSugar-Powertaste, kurz | globales Hauptmenü | Leertaste |
| PiSugar-Powertaste, lang | PiSugar schaltet das Gerät aus | keine Simulation |
| PiSugar-Custom, einmal | oberes rechtes Drehen: nächster Kanal/Eintrag | Pfeil runter |
| PiSugar-Custom, doppelt | rechter Encoder-Druck: auswählen/Play/Pause | `Enter` |
| PiSugar-Custom, lang | unteres rechtes Drehen: nächster Dienst | Pfeil rechts |

Die Begriffe *außen* und *innen* beziehen sich auf die beiden koaxialen
Drehachsen jedes Doppelencoders, nicht auf zwei getrennte Knöpfe. Im Display
stehen die aktuell gültigen Kürzel direkt im Funktionskopf. Ein Dienst darf
die Grundbelegung nur dort abwandeln, wo die Standardfunktion keinen Sinn
ergibt; die sichtbaren Kürzel müssen diese Abweichung sofort zeigen.

## Hardware, die der Nutzer tatsächlich bedient

- zwei geplante ALPS-Doppelencoder mit je zwei Drehachsen und einem Drucktaster;
- eine Whisplay-Hardwaretaste auf BCM17 – das ist immer die mit **PTT**
  bezeichnete Taste;
- eine PiSugar-3-Powertaste für Hauptmenü und Ausschalten;
- einen PiSugar-3-Custom-Taster als Ein-Tasten-Ersatz für Kanal vor,
  rechten Encoder-Druck und Dienst vor;
- 240 × 280 Pixel Whisplay-LCD mit regelbarer Hintergrundbeleuchtung;
- zwei Whisplay-Mikrofone;
- ein eingebauter 8-Ohm-/1-W-Lautsprecher;
- Anschluss für einen externen Mono-Lautsprecher;
- eine RGB-LED, derzeit ohne Nutzerfunktion.

Encoderpositionen und deren GPIOs sind noch nicht final hardwareverifiziert.
Die logische Bedienung im Programm und Browser ist bereits vollständig davon
entkoppelt.

## Dienstübersicht

| Dienst-ID | Nutzername | Heute nutzbar über |
| --- | --- | --- |
| `system` | System | Gerät und Browser |
| `webradio` | Webradio | Gerät und Browser |
| `weather` | Wetter | Gerät und Browser |
| `ambient` | AmbientR4D10 | Gerät und Browser |
| `local_media` | Lokale Medien / Musik | gemeinsamer Geräteplayer und Browser |
| `recorder` | Sprachaufzeichnung | Gerät und Browser |
| `rss` | RSS / Atom | Browser |
| `podcasts` | Podcasts | gemeinsamer Geräteplayer und Browser |
| `webcam` | Webcams | Browser |
| `brandmeister` | BrandMeister / DMR | Gerät und Browser |
| `ard_mediathek` | ARD Mediathek | gemeinsamer Geräteplayer und Browser |
| `zdf_mediathek` | ZDF Mediathek | gemeinsamer Geräteplayer und Browser |
| `public_mediatheken` | Öffentliche Mediatheken | gemeinsamer Geräteplayer und Browser |

`ARD Mediathek` begrenzt die Suche auf die ARD-Angebote, `ZDF Mediathek` auf
die ZDF-Angebote. `Öffentliche Mediatheken` bündelt die zusätzlich geprüften
deutschen Informations-, Kultur-, Dokumentations- und Regionalsender. Die drei
Dienste bleiben getrennte Katalogmodule, verwenden aber absichtlich dieselbe
PLAYER-Bedienung und denselben zentralen Audio-/Videoplayer.

### System

**Wofür:** Gerätezustand, Netzwerk, Akku, installierte Adapter und Diagnose.

**Am Gerät:** reine Statusansicht. Es gibt kein Senderbild und keinen
Play-Knopf. Der rechte innere Ring wechselt zum nächsten Dienst. Ein kurzer
PiSugar-Druck öffnet von überall das Hauptmenü.

**Im Browser:** Systemstatus, Diagnose, abgesicherte Updates, WLAN-Reparatur,
Sprache, Helligkeit und Akzentfarbe.

### Webradio

**Wofür:** kuratierte und eigene Internetradios, Senderlogos, Titelanzeige und
optionale Liedaufzeichnung.

**Am Gerät:** äußerer rechter Ring wählt Sender, rechter Druck startet oder
pausiert, äußerer linker Ring regelt die Lautstärke. Ein kurzer PTT-Druck merkt
das aktuelle Lied einschließlich Ringspeicher zum Speichern vor. Ein
PTT-Doppelklick schaltet die fortlaufende titelgetrennte Aufnahme ein oder aus.

**Im Browser:** Sender hinzufügen, aktivieren, sortieren, suchen und filtern;
Play/Pause/Stop sowie Lied behalten und fortlaufende Aufnahme.

### Wetter

**Wofür:** DWD-Regenradar Deutschland sowie DWD/EUMETSAT-Satellitenbilder für
Deutschland und Europa.

**Am Gerät:** äußerer rechter Ring wählt das Wetterbild, rechter Druck öffnet
oder aktualisiert den gewählten Kanal. Wetter übernimmt niemals den
Audioausgang; laufende Musik bleibt hörbar.

**Im Browser:** Animation, Kanäle, Reihenfolge und eigene Radarregionen.

### AmbientR4D10

**Wofür:** lokal zwischengespeicherte Café-, Natur-, Wasser-, Regen-, Verkehr-
und Nachtklänge sowie bis zu zwei dezente Zusatzebenen.

**Am Gerät:** äußerer rechter Ring wechselt die Szene und startet sie sofort,
rechter Druck pausiert oder setzt fort. Zwei Sekunden rechter Druck öffnen das
Ebenenmenü: außen rechts auswählen, rechter Druck ein/aus, innen links
Ebenenlautstärke, PTT zurück.

**Im Browser:** Szenen verwalten, Ebenen mischen und Favoritenmischung
dauerhaft speichern.

### Lokale Medien und Musik

**Wofür:** Musikdateien, Radioaufnahmen, Favoriten, Shuffle und „Mein
Soundmix“.

**Am Gerät:** gemeinsame `PLAYER`-Ansicht. Außen rechts wählt Eintrag,
rechter Druck wählt beziehungsweise startet oder pausiert, außen links bleibt
Lautstärke. Die Verwaltung der Bibliothek erfolgt derzeit im Browser.

**Im Browser:** Medien neu einlesen, Favoriten verwalten, Shuffle, nächster und
vorheriger Titel sowie Löschen.

### Podcasts

**Wofür:** öffentliche RSS-/Atom-Podcastfeeds abonnieren und Folgen abspielen.

**Am Gerät:** eine ausdrücklich gestartete Folge läuft in der gemeinsamen
`PLAYER`-Ansicht; rechter Druck ist Play/Pause, außen links Lautstärke. Eine
vollständige Podcast-Suche und Aboverwaltung direkt am Gerät ist noch nicht
implementiert.

**Im Browser:** Feed abonnieren, aktualisieren, durchsuchen, sortieren,
Folge auswählen und abspielen.

### ARD Mediathek, ZDF Mediathek und öffentliche Mediatheken

**Wofür:** öffentlich erreichbare deutsche Nachrichten, Dokumentationen,
Wissenschaft, Kultur und Sendungen als Audio oder niedrig aufgelöstes Video.
Alle drei Katalogdienste verwenden denselben sicheren Player.

**Am Gerät:** `PLAYER` zeigt zunächst die lokalisierte Gruppenauswahl. Außen
rechts wählt Gruppe oder Beitrag, rechter Druck bestätigt beziehungsweise
spielt/pausiert. Innen links spult zunächst 15 Sekunden je Rastung und nach
mehr als einer Minute minutenweise; außen links bleibt immer Lautstärke. PTT
kurz setzt Favorit und Wiedereinstiegsmarke, PTT zwei Sekunden pausiert das
Video und öffnet die Gruppenauswahl.

**Im Browser:** Sender, Themen, Suche, ungesehen/Archiv/Favoriten sowie getrennte
Aktionen für Browservideo, Geräteaudio und Gerätevideo.

### BrandMeister / DMR HoseLine

**Wofür:** ausschließlich Empfang öffentlicher BrandMeister-HoseLine-
Talkgroups. OpenR4d10 sendet dabei niemals Sprache oder DMR-PTT.

**Am Gerät:** außen rechts bewegt sich talkgroupweise, innen links springt 25
Talkgroups. Rechter Druck startet oder stoppt den Empfang der aktivierten
Gruppen. PTT kurz aktiviert/deaktiviert die markierte Gruppe. PTT zwei Sekunden
öffnet bereits während des Haltens den Länderfilter; in Menüs ist PTT zurück.
Maximal sechs Gruppen sind gleichzeitig aktiv, die siebte öffnet eine
Ersetzen-Auswahl.

**Im Browser:** vollständiger Katalog, Suche, Länder, Aktivierung, Sprecher-
und Aktivitätsanzeige sowie Geräte- oder Browserempfang.

### Sprachaufzeichnung

**Wofür:** verlustsicher fortsetzbare Stereo-Sprachaufnahmen aus den beiden
Whisplay-Mikrofonen. Beim Öffnen werden alle anderen Audioquellen sofort
beendet.

**Am Gerät:** PTT halten startet unmittelbar, Loslassen pausiert unmittelbar.
PTT-Doppelklick startet Daueraufnahme; der nächste normale oder doppelte Druck
beendet sie. Rechter Druck spielt ab oder pausiert. Außen rechts verschiebt den
Cursor um 1 Sekunde, außen links um 0,1 Sekunde, innen links springt an Anfang
oder Ende. Die Wiedergabelautstärke des Recorders ist fest 100 %.

**Im Browser:** dieselbe Aufnahme, Wellenform, Cursor und Wiedergabe. Dateien
liegen geordnet unter `Media/VoiceRecorder/JJMMTT`.

### RSS / Atom

**Wofür:** begrenztes Laden öffentlicher Nachrichtenfeeds, einschließlich
kuratierter Quellen.

**Am Gerät:** noch keine eigene native Dienstansicht. Es wird deshalb keine
nicht vorhandene Encoderfunktion behauptet.

**Im Browser:** Quelle wählen oder öffentliche Feedadresse eingeben und die
letzten Einträge öffnen.

### Webcams

**Wofür:** geordnete Bibliothek eigener, zugangsdatenfreier Snapshot-, MJPEG-
und RTSP-Quellen. Bilder werden begrenzt, geprüft und lokal neu kodiert.

**Am Gerät:** noch keine eigene native Kameraansicht oder Kanalbedienung.

**Im Browser:** Quelle hinzufügen, anzeigen, sortieren, aktualisieren und
löschen. Authentifizierte Kameras und ONVIF benötigen später einen getrennten
Geheimnisadapter.

## Menübedienung

In jeder Liste gilt ohne Ausnahme:

1. äußerer rechter Ring wählt die Zeile;
2. rechter Druck bestätigt;
3. PTT geht eine Ebene zurück;
4. kurzer PiSugar-Druck öffnet das globale Hauptmenü;
5. Dienstwechsel beendet laufendes Audio nicht automatisch.

Erst ein ausdrückliches Play in einem anderen Audiodienst übernimmt den
Lautsprecher. Visuelle Dienste wie Wetter dürfen Musik im Hintergrund nicht
unterbrechen. Beim Öffnen der Sprachaufzeichnung gilt bewusst die einzige
harte Ausnahme: alle Streams werden sofort beendet.

## Was nicht als fertiger Dienst bezeichnet werden darf

Anker SOLIX, Remote SDR, privates OpenR4d10-PTT, Mumble, Discord, Telegram,
Spotify, YouTube Audio, internationale Medien, Offline-Sprache, Bluetooth-
Audio, Codex Remote und TeamSpeak sind im Katalog vorhandene Ausbau- oder
Adapterverträge. Ohne erfolgreich verbundenen Adapter sind sie keine bereits
nutzbaren Dienste und erhalten deshalb in dieser Bedienmatrix keine erfundene
Hardwarebelegung.

