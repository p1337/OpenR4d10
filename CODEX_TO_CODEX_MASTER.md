# Codex-zu-Codex-Masteranweisung – OpenR4d10

## 0. Zwingende Startregel

**Diese Datei muss von jeder Codex-Instanz vollständig gelesen werden, bevor
irgendeine Analyse, Konstruktion, Programmierung, Kaufempfehlung, Änderung,
Simulation oder Antwort zum OpenR4d10-Projekt erfolgt.**

Diese Datei ist die zentrale, fortlaufend gepflegte Projektwahrheit.

Sobald Robert eine neue Erkenntnis, Korrektur, Hardwareangabe, Abmessung,
Bedienregel, Designentscheidung oder Funktionsanforderung nennt, muss die
arbeitende Codex-Instanz:

1. die neue Information zuerst in die passenden Abschnitte dieser Datei
   einarbeiten,
2. Widersprüche zu älteren Angaben ausdrücklich auflösen,
3. danach Spezifikation, Code, Datenbank, UI und Renderings anpassen,
4. die Änderung im Änderungsprotokoll am Dateiende eintragen,
5. erst anschließend das Ergebnis als abgeschlossen melden.

Neue Erkenntnisse dürfen nicht nur im Chat, in einem Rendering oder in
Quellcode verbleiben. Sie müssen hier dauerhaft dokumentiert werden.

## 1. Projektziel

OpenR4d10 wird ein offen entwickeltes, vollständig programmierbares,
robustes Handheld im Stil eines hochwertigen professionellen Funkgeräts.

Der endgültige öffentliche Projekt- und Produktname lautet exakt
**OpenR4d10**. Die Standardschreibweise ist `OpenR4d10`; auf Logo und Gehäuse
darf `OPENR4D10` stehen. Gesprochen wird der Name „Open Radio“. Der geplante
Repository-Pfad lautet `p1337/OpenR4d10`. `OpenHandheld` und `openplayer` sind
ausschließlich historische Arbeitsnamen und dürfen nicht mehr als sichtbare
Marke, Daemonname oder neuer Systempfad verwendet werden. Der aktuelle Dienst,
Python-Namespace und die installierten Pfade heißen einheitlich `openr4d10`.

Primärer Zweck:

- eigenständiger Audio-Stream-Empfänger,
- digitaler Scanner für frei empfangbare oder berechtigt zugängliche Inhalte,
- Webradio und lokale Musik,
- BrandMeister-/DMR-Audio über IP, primär zum Hören,
- Sprach-, Chat-, Feed- und Mediathekdienste,
- Audioaufzeichnung aller geeigneten Quellen,
- Bedienung vollständig am Gerät,
- zusätzliche Bedienung und Streaming über einen Webbrowser,
- offene Plattform für installierbare Dienstmodule.

Das Gerät ist kein klassisches Sendefunkgerät. Empfang, Audio, Bedienung,
Aufzeichnung und optionale Push-to-Talk-Netzdienste stehen im Vordergrund.
Verschlüsselte oder zugriffsgeschützte Funkkommunikation wird nicht umgangen.

Neben der Weboberfläche sind zukünftig native Apps für iOS und Android
vorgesehen. Deren eigentliche Implementierung beginnt jedoch ausdrücklich erst,
nachdem die Hardware aufgebaut, geprüft und das Gehäuse gedruckt wurde. Die
Weboberfläche bleibt parallel vollständig erhalten.

## 2. Verifizierter beziehungsweise festgelegter Hardwarebestand

Aktueller Ziel-Stack:

- Raspberry Pi Zero 2 W,
- PiSugar 3 für Raspberry Pi Zero mit circa 1200-mAh-Akku,
- PiSugar Whisplay HAT,
- Whisplay-Display mit nativer Auflösung 240 × 280 Pixel,
- im Whisplay vorhandene Audiohardware mit integriertem Lautsprecher und
  Mikrofonen,
- zwei bestellte ALPS-Doppelachsen-Drehencoder, Typfamilie
  EC11EBB24C03/Angebotsvariante mit zwei koaxialen Drehachsen, Drucktaster und
  acht Anschlüssen,
- insgesamt vier mechanische Drehfunktionen und zwei Drucktaster,
- USB-C zum Laden und für Service.

Die beiden Encoder sind am 2026-10-30 noch auf dem Versandweg aus China nach
Waiblingen und stehen weder zum Vermessen noch zum elektrischen Test zur
Verfügung. UI, Bedienmodell und Eingabeschnittstelle werden deshalb sofort mit
simulierten Encoderereignissen umgesetzt. Die spätere GPIO-Anbindung darf nur
den Eingabeadapter ergänzen und keine Neuentwicklung der UI erfordern.

Realer Aufbau am 2026-10-30:

- die vollständige 2-x-20-Stiftleiste des Raspberry Pi Zero 2 W ist an allen
  40 Kontakten verlötet,
- das Whisplay HAT ist auf der Vorderseite aufgesteckt,
- das PiSugar-3-Akkupack ist auf der Rückseite montiert,
- der PiSugar versorgt den Pi nach realer Nutzerbestätigung erfolgreich im
  Akkubetrieb; offen ist nur die Softwareanbindung seiner Messwerte,
- der Raspberry Pi startet und der OpenR4d10-Dienst läuft,
- die RGB-LED des Whisplay leuchtet; das LCD blieb mit dem bisherigen
  absichtlich unkonfigurierten/headless Display-Backend schwarz.

Die leuchtende RGB-LED belegt nur Versorgung beziehungsweise einzelne
Whisplay-Verbindungen. Sie ist kein Nachweis für funktionierende SPI-
Bildübertragung. Der vorhandene, gegen den Hersteller-Code abgeglichene native
ST7789-Player wird deshalb in den Hauptinstaller integriert und muss auf diesem
realen Stack noch auf Bild, Farben, Orientierung, Framerate und Stabilität
geprüft werden. Encoderleitungen werden erst nach endgültiger Pinfreigabe und
mechanischer Prüfung mit dem montierten PiSugar 3 angelötet.

Vor endgültigem PCB- oder Gehäusedesign sind die exakten Datenblätter,
Pinbelegungen und real gemessenen Abmessungen der tatsächlich gelieferten
Encoder zu erfassen. Angebotsbilder sind keine belastbare Maßquelle.

### Hardwaregrenzen

- Das Whisplay ist klein; die Oberfläche muss für 240 × 280 Pixel optimiert
  bleiben.
- Der Pi Zero 2 W reicht für UI, Audio, Webserver, Datenbank, Netzwerkdienste
  und leichte Visualisierungen.
- Dauerhaft schwere SDR-Demodulation und große, flüssige Waterfalls können den
  Pi Zero 2 W überfordern.
- In der aktuellen Gehäuseversion ist **kein SDR-Schacht** vorgesehen.
- Ein externer SDR kann später über einen zweiten Raspberry Pi oder OpenWebRX
  im Netzwerk vollständig vom Handheld gesteuert werden.
- Ein Cloud-Codex beziehungsweise Remote-Codex-Client ist möglich; ein großes
  modernes Codex-/LLM-Modell läuft nicht vollständig lokal auf dem Pi Zero 2 W.

## 3. Mechanik und Industriedesign

Verbindliche Gehäuseregeln:

- professionelles, serienreif wirkendes, robustes Handheld,
- keine einfache eckige Box und kein unfertiger Prototypenlook,
- Kanten mit klaren 45-Grad-Fasen und gezielten Vertiefungen,
- kompakte, kontrollierte Flächenübergänge,
- keine zufälligen Eckklötze, Ausbeulungen oder dekorativen Fremdkörper,
- keine automatisch hinzugefügten Kühlrippen oder Honeycomb-Flächen,
- zwei koaxiale Doppelknöpfe oben,
- Knöpfe möglichst weit auseinander, ohne die Gerätebreite zu vergrößern,
- die Breite des Geräts wird durch den Whisplay-/Pi-/PiSugar-Platinenstack
  bestimmt, **nicht durch die Encoder**,
- Encoderkörper bleiben innerhalb der breitesten Platinenkontur,
- nur die Knöpfe und notwendige Drehfreiheit dürfen darüber hinausgehen,
- sämtliche Platinen, Encoder, Anschlüsse und Kabelwege müssen vor dem
  Rendering maßhaltig simuliert werden,
- keine erfundenen Encoder-Zusatzplatinen,
- keine erfundenen Fronttasten,
- seitlich dürfen im Normalbetrieb keine Kabel herausstehen,
- USB-C-Anschlüsse und Ausschnitte müssen an den realen Positionen sitzen,
- Gehäuse soll auf einem Prusa MK4 druckbar sein,
- starre Schalen bevorzugt aus PETG/ASA; TPU nur als eingesetzte Stoß-, Dicht-
  oder Griffelemente,
- Displayfront soll hochwertig und geschützt wirken.

Jede Gehäusefreigabe benötigt:

1. maßhaltige Frontansicht ohne Gehäuse,
2. mindestens eine weitere Komponentenansicht ohne Gehäuse,
3. Front, Rückseite, links, rechts, oben und unten mit Gehäuse,
4. mindestens eine isometrische Gehäuseansicht,
5. eine Kollisionsprüfung von Encoderkörpern, Platinen, Akku und Anschlüssen.

### Logo

Das OpenR4d10-Signet steht auf schwarzem Hintergrund: ein vollständig weiß
ausgefüllter, nicht böse blickender Schädel,
mit runden Augenhöhlen, dreieckiger Nase, Oberkiefer und
ohne Unterkiefer. Der Schädel wirkt wie ein flaches weißes Pappschild, dessen
hintere beziehungsweise obere Kante mit Alkohol benetzt wurde und real brennt.
Die Flamme ist **eine zusammenhängende hyperrealistische Flammenfläche**, kein
Bündel einzelner Flammen, keine parallelen Farbstreifen und kein Punk-Haar.
Sie bleibt extrem kompakt und kurz, höchstens ungefähr ein Zwölftel der
Schädelhöhe. Der brennende Bereich erstreckt sich lückenlos über die gesamte
obere Schädelbreite bis zu beiden äußersten Seitenkanten. Dort dürfen weder ein
weißer Rand noch eine Verjüngung, ein Übergangsbogen oder eine harte obere
Schädelkontur sichtbar bleiben: Das Weiß des Schädels löst sich über die volle
Breite weich und nahtlos in transparentes Alkohol-Blau auf.
Darüber ist die Flamme überwiegend fast farblos/weiß
mit dezentem natürlichem Gelb und Orange. Kein Regenbogen, kein kräftiges Rot,
kein Plastik-, Glas- oder Neonlook. Rasterbasierte realistische Feuerdetails
sind ausdrücklich zulässig; keine Crossbones oder Schrift im Signet.

Die Farbrichtung ist physikalisch und darf niemals vertauscht werden: direkt an
der brennenden Schädelkante beziehungsweise Brennstoffquelle liegt der kurze
blau-weiße, heißeste Bereich. Mit wachsendem Abstand vom Schädel folgen Weiß,
Gelb und Orange; nur die äußersten Flammenspitzen dürfen orange-rötlich sein.
Blau an den äußeren Spitzen und Rot/Orange direkt an der Schädelkante sind
verboten. Diese Regel gilt nach der 45-Grad-Rotation weiterhin relativ zur
Schädelkante, nicht relativ zur oberen oder unteren Bildkante.

Die Grundrichtung der Flammen folgt exakt der Schädelmittelachse und steht damit
rechtwinklig auf der Verbindungslinie zwischen den Augen. Es gibt keinen
seitlichen Wind und kein diagonales Wegkippen relativ zum Schädel. Der blaue
Übergangsbereich bleibt deutlich kürzer als der warme orangefarbene
Flammenanteil. Die mittleren Flammenspitzen dürfen etwas länger als die äußeren
sein, bleiben aber natürlich asymmetrisch und nicht gespiegelt.

Die vom Nutzer am 2026-10-30 zuletzt bereitgestellte Bildreferenz
`upload/47858918-75D3-4081-88FF-9EBF55BCBF7C.jpeg` ist die **einzige und
unveränderliche Masterbasis** für Form, Rotation, Schädel, Flammenkontur,
Flammenlänge und Farben. Keine generierte Zwischenfassung darf sie ersetzen.
Animationen und Bootscreens dürfen das Logo nicht neu gestalten. Schädel,
Gesicht, Farbpalette, Ausgangskomposition und Ansatz der Flammen bleiben an
dieser Vorlage gebunden. Die einzelnen Flammenkonturen sind jedoch ausdrücklich
nicht eingefroren: echte Flammenzungen müssen sich neu bilden, teilen, aufsteigen
und auflösen. Zeitliche Neusynthese und neue feine Feuerdetails sind für diese
Animation erlaubt und erforderlich; eine Verformung des Referenzfotos allein
erfüllt die Anforderung nicht. Die neueste Animationsspezifikation unten hat
Vorrang vor älteren Längen-, Standbild- und Frame-für-Frame-Konturvorgaben.

Der Schädel wird zunächst als unverzerrte, frontale und senkrechte Ansicht zur
Kamera aufgebaut. Die windstill nach oben brennende Flamme ist dabei bewusst
**natürlich asymmetrisch**, unregelmäßig und keinesfalls gespiegelt. Erst wenn
Schädel und Feuer fertig aufgebaut sind, wird das **gesamte fertige Signet exakt
45 Grad gegen den Uhrzeigersinn** in der Bildebene gedreht. Es erfolgt keine
perspektivische Drehung des Kopfes.

## 4. Grundlegende Bedienlogik

Die zwei ALPS-Doppelencoder ergeben vier Drehachsen:

| Position | Standardfunktion |
|---|---|
| links außen | Lautstärke |
| links innen | Squelch |
| rechts außen | Kanal beziehungsweise Eintrag |
| rechts innen | Dienst |

Die zwei Encoder-Drucktaster sind verbindlich so belegt:

| Drucktaster | kurz drücken | 2 Sekunden halten |
|---|---|---|
| links | Hauptmenü | Einstellungen des aktiven Dienstes |
| rechts | Play/Pause; bei BrandMeister Kanal/Talkgroup aktivieren oder deaktivieren | Quick-Menü inklusive Aufnahme |

Bis die Encoder verfügbar sind, bildet die Weboberfläche dieselben logischen
Eingaben zusätzlich auf eine PC-Tastatur ab:

- `W`/`S`: linker äußerer Encoder (Lautstärke höher/niedriger),
- `A`/`D`: linker innerer Encoder (Squelch niedriger/höher),
- Pfeil hoch/runter: rechter äußerer Encoder (Kanal vor/zurück),
- Pfeil links/rechts: rechter innerer Encoder (Dienst zurück/vor),
- Leertaste: linker Drucktaster,
- Enter: rechter Drucktaster,
- `Q` halten: PTT aktiv; Loslassen beendet PTT.

Die Tastatursteuerung ist in Text- und Auswahlfeldern inaktiv, damit Eingaben
nicht versehentlich Gerätesteuerungen oder PTT auslösen. PTT bleibt bis zur
Einrichtung eines berechtigten PTT-Dienstadapters ein sichtbares logisches
Eingabesignal und darf keine funktionierende Audioübertragung vortäuschen.

Die Druckfunktionen werden im oberen Displaybereich vertikal angezeigt:

- links grau: **MENÜ**,
- rechts grau: **PLAY** beziehungsweise die kontextabhängige Kurzfunktion.

Die vier oberen Funktionsfelder zeigen immer die aktuelle Belegung und den
aktuellen Wert. In Untermenüs dürfen die Achsen kontextabhängig anders belegt
werden; die Felder müssen dies sofort anzeigen.

## 5. Verbindlicher Aufbau der Hauptanzeige

Display: 240 × 280 Pixel, ohne Touchpflicht.

Oberer schwarzer Funktionskopf:

- Zeile links: Lautstärke und Wert,
- Zeile rechts: Kanal und Wert,
- zweite Zeile links: SQL/Squelch und Wert,
- zweite Zeile rechts: Dienst und aktueller Dienst,
- Werte direkt hinter den Parametern und sauber spaltenweise ausgerichtet,
- vertikale graue Klickbeschriftung links und rechts.

Statuszeile:

- links WLAN-Symbol mit drei Bögen,
- direkt daneben WLAN-Modus/SSID und IP-Adresse,
- Datum und Uhrzeit mittig,
- Batteriestand rechts.

Medien-/Dienstbereich:

- dienstabhängige Hauptinformationen,
- Sender, Kanal, Titel, Status und Visualisierung,
- großer interner Play-/Pause-Button im Mediendesign,
- **keine künstliche Medien-Fortschrittsanzeige bei Live-Streams**,
- keine dauerhaft sichtbare Meldung „REC bereit“,
- kein permanenter Hinweis „Play halten Quick-Menü“.

Der Funktionskopf muss optisch eindeutig vom Medienbereich getrennt bleiben.

## 6. Einstellungsmenü auf dem Gerät

Die Geräteeinstellungen enthalten genau diese Hauptbereiche:

1. **Display**
   - Displayhelligkeit von 0 bis 100 Prozent,
   - Änderungen werden sofort auf dem realen Whisplay sichtbar,
   - der Wert wird als nicht geheime UI-Einstellung dauerhaft in SQLite
     gespeichert und nach Dienst- oder Geräteneustart wieder angewendet,
   - die Raspberry-Pi-Zero-2-W-Umsetzung verwendet den vom Hersteller
     vorgesehenen Software-PWM-Pfad auf dem bereits verifizierten aktiven-low
     Backlight BCM22; kein neuer Pin und kein paralleler Hardwareadapter.
2. **Akzentfarbe**
   - normaler Menüeintrag wie alle anderen,
   - öffnet beim Anwählen eine eigene Farbauswahl,
   - Farbton, Sättigung, Helligkeit und Preset werden mit den vier Drehachsen
     bedient,
   - Live-Vorschau der Akzentfarbe.
3. **WLAN**
   - vollständige Standalone-Einrichtung am Gerät,
   - Netzsuche, SSID, Kennwort, DHCP/feste IP, gespeicherte Netze und Priorität.
4. **Dienstmodule**
   - installierte Dienste konfigurieren, aktivieren, deaktivieren, aktualisieren
     und deinstallieren.
5. **Dienst-Store**
   - eigener Hauptmenüpunkt,
   - lädt einen signierten beziehungsweise prüfsummengesicherten Katalog aus
     dem öffentlichen Git-Repository,
   - zeigt verfügbare, installierte und aktualisierbare Dienste,
   - installiert nur nach sichtbarer Berechtigungsanzeige und Bestätigung.
6. **Bluetooth**
   - Bluetooth ein/aus,
   - Audiogeräte,
   - Bluetooth-HID-Tastaturen.
7. **Eingabe und Sprache**
   - PTT-Verhalten,
   - deutsches Diktat,
   - Sprachbefehle,
   - Vorlesefunktion.
8. **Sprache**
   - Standardsprache ist Englisch,
   - Schnellwahl oben: English, Deutsch, Polski, Français, Español,
   - darunter vollständige, alphabetisch nach Eigenbezeichnung sortierte
     Sprachliste; die fünf Schnellwahlsprachen erscheinen dort ebenfalls,
   - nicht wörtlich, sondern funktions- und kontextgerecht übersetzen.
9. **System**
   - Updates, Diagnose, Protokolle, Neustart, Sicherung und Wiederherstellung.
10. **Informationen & Support**
   - muss der letzte Hauptmenüpunkt bleiben,
   - Entwickler, Projekt, Version, Lizenzen und Quellcode,
   - freiwillige Unterstützung über konfigurierbaren PayPal-/Spendenlink,
   - öffnet einen QR-Code; ohne konfigurierten Link wird kein QR-Code gezeigt,
   - Text: Unterstützung weiterer offener und gemeinwohlorientierter Projekte.

**Die Datenbankverwaltung erscheint nicht auf dem Gerät.** Sie ist nur in der
Weboberfläche verfügbar.

**Die Browser-Audioauswahl erscheint nicht auf dem Gerät.** Sie wird nur
angeboten, wenn tatsächlich ein Webbrowser verbunden ist.

## 7. WLAN und Ersteinrichtung

Das Gerät muss ohne PC und ohne vorhandenes WLAN vollständig einrichtbar sein.

Startlogik:

1. gespeicherte WLAN-Netze versuchen,
2. bei erfolgreicher Verbindung normalen Client-Modus benutzen,
3. wenn keine Verbindung zustande kommt, automatisch einen eigenen
   Konfigurations-Hotspot starten,
4. Smartphone verbindet sich mit diesem Hotspot,
5. Captive Portal beziehungsweise lokale Webadresse öffnet die Konfiguration,
6. Zugangsdaten werden gespeichert und der Verbindungsversuch wiederholt.

Der Hotspot darf später auch manuell aktiviert werden.

## 8. Audio und Bluetooth

Standalone-Verhalten:

- Standardausgabe ist immer der interne Lautsprecher.
- Bluetooth kann vollständig deaktiviert oder aktiviert werden.
- Ist Bluetooth-Audio aktiviert und ein Audiogerät verbunden, erfolgt die
  Ausgabe darüber.
- Bei Trennung oder Fehler erfolgt automatisch der Rückfall auf den internen
  Lautsprecher.
- Bluetooth-Tastaturen werden als HID-Eingabegeräte unterstützt.

Nur im verbundenen Webinterface gibt es drei auswählbare Ausgabeziele:

1. Gerät,
2. Webbrowser,
3. Bluetooth.

Der zentrale Audio-Router muss eine Quelle gleichzeitig an Wiedergabe,
Browserstream und Recorder verteilen können.

## 9. Spracheingabe, PTT und Vorlesen

Der vorhandene physische PTT-/Displaybutton erhält folgende Zusatzfunktion:

- Doppelklick aktiviert die deutsche Spracheingabe,
- erneuter Druck beendet sie,
- während der Aktivität erscheint ein animierter, mehrfarbiger Rand um das
  gesamte Display ähnlich einem Sprachassistenten.

Kontext:

- Fokus in einem Textfeld: Sprache wird als deutscher Text diktiert.
- Kein Textfeld aktiv: lokale Sprachbefehle werden ausgeführt.

Mindestens unterstützte Sprachbefehle:

- Dienst auswählen,
- nächsten oder vorherigen Titel wählen,
- Play/Pause,
- Lautstärke ändern,
- Squelch ändern.

Die Grundfunktionen müssen mit einem kompakten deutschen Offline-STT-Modell
arbeiten. Text-to-Speech muss für Feeds und Chatnachrichten aktivierbar sein.

## 10. Dienstmodulsystem

Dienste sind installierbare Pakete, vorzugsweise aus Git-Repositories.

Jedes Paket enthält mindestens:

- Manifest mit ID, Name, Version, Autor, kompatibler Core-Version,
- Python-Einstiegspunkt,
- benötigte Berechtigungen,
- optionale Geräteansicht,
- optionale Webansicht,
- Datenbankschema und Migrationen,
- Updatequelle,
- Prüfsumme beziehungsweise Signaturinformation.

Benötigt ein Dienst einen Token oder API-Schlüssel, muss seine Konfiguration:

- eine kurze dienstspezifische Anleitung anzeigen, wo der Benutzer seinen
  eigenen Token erhält,
- ausdrücklich erklären, dass jeder Benutzer einen eigenen Token eintragen
  muss,
- niemals Roberts Tokens, Entwickler-Tokens oder gemeinsame Standardtokens
  enthalten oder ausliefern,
- Tokens maskiert erfassen und ausschließlich lokal in einem geschützten
  Secret-Speicher ablegen,
- Tokens weder in SQLite, Logs, Backups noch Telemetrie speichern,
- nur den Status „eingerichtet/nicht eingerichtet“ in der Datenbank führen.

Verwaltung:

- hinzufügen,
- installieren,
- aktivieren/deaktivieren,
- konfigurieren,
- aktualisieren,
- deinstallieren.

Module dürfen den Core nicht unkontrolliert verändern. Sie laufen mit
definierten Berechtigungen, Ressourcenlimits und getrennten Datenverzeichnissen.

### Sicherheitsgrenze für Dienstmodule

- Dienstmodule dürfen niemals Pi-, Linux-, SSH-, WLAN-, Core-, Git-, Codex-
  oder Zugangsdaten anderer Dienste lesen.
- Ein Modul erhält einen eigenen unprivilegierten Benutzer beziehungsweise
  eine isolierte Laufzeit, ein eigenes Datenverzeichnis und nur deklarierte
  Ressourcen.
- `/home`, `/root`, `/etc/openr4d10`, der zentrale Secret-Speicher, SSH-Keys,
  WLAN-Profile und die Datenverzeichnisse anderer Module sind unsichtbar.
- Das Root-Dateisystem ist für Module schreibgeschützt; schreibbar sind nur
  das private Modulverzeichnis und ein begrenztes temporäres Verzeichnis.
- Hardware, Netzwerkziele, Audio, Mikrofon, Browserstream und Recorder werden
  ausschließlich über einen Core-Broker nach expliziter Manifestberechtigung
  bereitgestellt.
- Secrets werden einem Modul niemals als Datei oder globale Umgebungsvariable
  gegeben. Der Core verwendet sie nur für eng definierte Proxy-Aufrufe oder
  kurzlebige, dienstbezogene Handles.
- Installation führt statische Manifestprüfung, Prüfsummenprüfung und einen
  Secret-/Malware-Scan aus. Unsignierte Community-Pakete werden sichtbar als
  nicht verifiziert markiert und sind standardmäßig blockiert.

### Git-basierter Dienst-Store

Der öffentliche Store-Katalog liegt versioniert im Git-Repository. Jeder
Eintrag enthält Manifest, Repository, Version, Core-Kompatibilität,
Berechtigungen, Prüfsumme/Signatur, Übersetzungen und Updatekanal. Der Store ist
kein beliebiger Code-Downloader: Er prüft Schema, Herkunft, Hash,
Kompatibilität und Berechtigungen vor der Installation. Community-Dienste
gelangen ausschließlich über geprüfte Pull/Merge Requests in den Katalog.

### Fest eingeplante Dienste

- BrandMeister/DMR-Audio über IP zum Hören,
- Webradio,
- YouTube-Audio innerhalb der technisch und rechtlich verfügbaren Schnittstellen,
- Mumble-Client mit Push-to-Talk,
- Discord-Client mit Push-to-Talk,
- lokaler Musikplayer für MP3/MP4 und Aufzeichnungen,
- Webcams: bis zu zwei Ansichten horizontal; Standbilder periodisch,
  Videostreams live,
- Audiorecorder,
- RSS-/moderner Feed-Reader mit Abonnements und optionalem Vorlesen,
- Telegram-Client als eigener Dienst, optionales Vorlesen neuer Nachrichten,
- ARD-Mediathek,
- ZDF-Mediathek,
- weitere gängige deutsche Mediatheken,
- US-/englischsprachige Mediatheken und News-Quellen.

Mumble-Serveradresse, Benutzername, Kennwort und Zertifikate sind lokale
Benutzereinstellungen. Das Repository enthält keinerlei produktive
Mumble-Zugangsdaten.

Der Discord-Dienst verwendet ausschließlich den offiziellen Login-/OAuth-
beziehungsweise Bot/App-Ablauf. Benutzer- und Bot-Tokens bleiben lokal im
Secret-Speicher und werden niemals eingecheckt. Geplant ist ein
OpenR4d10-Discord mit freiwillig auswählbaren Sprachkanälen nach Sprache
beziehungsweise Land; PTT erfolgt nur nach Benutzerbeitritt und sichtbarer
Mikrofonfreigabe. Kanalstruktur und Moderationskonzept werden noch festgelegt.

### Optionale beziehungsweise später zu prüfende Dienste

- Spotify über offiziell verfügbare Schnittstellen,
- TeamSpeak,
- weitere Chat-/PTT-Netzdienste,
- Remote-SDR/OpenWebRX,
- Codex-Client zu einem entfernten Codex- oder API-Dienst.

WhatsApp ist nur einzuplanen, wenn eine offiziell nutzbare und für diesen
Gerätetyp geeignete Schnittstelle vorhanden ist.

## 11. Datenhaltung

Lokale Hauptdatenbank: SQLite mit Migrationen.

In der Datenbank liegen:

- System- und UI-Einstellungen,
- Displayhelligkeit in Prozent,
- Akzentfarbe und Presets,
- WLAN-Profile,
- Bluetooth-Geräteinformationen soweit zulässig,
- installierte Module, Versionen und Zustände,
- Dienstkonfigurationen,
- Sender, Kanäle, Favoriten und Verlauf,
- Audio-Routing,
- Aufnahme- und Mediendaten-Metadaten.
- Sprachen, Übersetzungsschlüssel, funktionaler Kontext und Übersetzungen,
- lokale Einwilligungszustände für das freiwillige Aktivierungsregister,
- ausschließlich Secret-Metadaten, niemals Tokenwerte.

Die kuratierte Radio-Grundausstattung wird beim ersten Lauf genau einmal in
die dauerhafte Senderbibliothek übernommen. Danach ist ausschließlich diese
Datenbankliste für Reihenfolge und Gerätebedienung maßgeblich: Standardsender
und später angelegte Sender können gleichberechtigt sortiert und gelöscht
werden; neue Einträge werden am Listenende ergänzt. Ein absichtlich gelöschter
Standardsender darf bei Dienstneustart oder Softwareupdate nicht automatisch
wieder erscheinen.

Große Audio- und Videodateien bleiben im Dateisystem. Die Datenbank enthält
Pfad, Quelle, Zeit, Dauer, Codec, Größe und Prüfsumme. Keine unnötigen großen
BLOBs in SQLite.

Die Datenbank wird ausschließlich über die Weboberfläche editiert:

- Tabellenansicht ähnlich phpMyAdmin,
- Suche, Filter und Sortierung,
- sichere Formularbearbeitung,
- CSV/JSON-Export und Import,
- Backup und Wiederherstellung,
- optionaler SQL-Expertenmodus mit Warnung und Sicherung.

### Sicherung und Wiederherstellung

OpenR4d10 erzeugt versionierte, portable Backup-Pakete mit:

- SQLite-Konsistenzbackup,
- Core-, UI-, WLAN-, Bluetooth- und Spracheinstellungen soweit exportierbar,
- Liste installierter Dienste mit Repository, Version und Prüfsumme,
- Wiederherstellungsplan zur automatischen Nachinstallation aus dem Store,
- allen dienstbezogenen Einstellungen und Datenbankmigrationen,
- optional Aufzeichnungsmetadaten und auf Wunsch Mediendateien.

Secrets, Tokens, SSH-Schlüssel und Passwörter sind im normalen Backup niemals
enthalten. Ein separates Secret-Backup ist nur ausdrücklich, lokal und mit
starker passwortbasierter Verschlüsselung zulässig. Backups können lokal
gespeichert, im Browser heruntergeladen und später über sichere Zielmodule
beispielsweise auf USB, SFTP oder WebDAV geschrieben werden. Cloud-Ziele
benötigen eigene Benutzer-Credentials und sind standardmäßig deaktiviert.

## 12. Weboberfläche

Die Weboberfläche ist eine responsive PWA und zeigt:

- identische Live-Ansicht des Gerätedisplays,
- virtuelle Bedienung aller Drehachsen und Druckfunktionen,
- alle Dienste,
- Live-Audio aller geeigneten Dienste,
- Aufnahmen und lokale Medien,
- Einstellungen und Dienstmodule,
- ausschließlich hier den Datenbankeditor,
- WLAN-Ersteinrichtung im Hotspotmodus.

Systemupdates müssen direkt aus der lokalen Weboberfläche ausdrücklich
bestätigt und gestartet werden können; eine SSH-Konsole darf dafür nicht
erforderlich sein. Der unprivilegierte Webdienst erhält dabei weder `sudo`
noch allgemeine Root- oder Shellrechte. Er darf ausschließlich eine feste
Updateanforderung an einen separat installierten, root-eigenen systemd-Helfer
übergeben. Dieser verwendet nur die fest eingetragene öffentliche
Projektquelle, übernimmt keine URL und kein Kommando aus dem Browser, schreibt
einen begrenzten Status und nutzt weiterhin den einzigen vorhandenen
`bootstrap.sh`-/`install.sh`-Installationsweg. Die Oberfläche muss Start,
laufende Installation, Fehler und den anschließenden automatischen Neustart
verständlich anzeigen und Mehrfachstarts verhindern.

Vor jeder tatsächlichen Installation eines Updates muss der vorhandene
secret-freie SQLite-Zustand mit der bestehenden konsistenten Backup-Funktion
gesichert werden. Schlägt diese Sicherung fehl, darf das Update nicht beginnen.
Damit bleiben insbesondere die persönliche Senderliste und ihre Reihenfolge
auch dann wiederherstellbar, wenn eine spätere Migration oder Installation
fehlschlägt; Git-/Archivdateien dürfen den Zustand unter `/var/lib/openr4d10`
niemals ersetzen.

Bei verbundenem Browser kann der Benutzer die Ausgabe zwischen Gerät,
Webbrowser und Bluetooth wählen. Das Gerät kann gleichzeitig lokal spielen,
aufzeichnen und an berechtigte Browser streamen, soweit die Leistung reicht.

## 13. Freiwilliges Aktivierungsregister und Gerätekarte

Beim ersten Start darf das Gerät eine Teilnahme am öffentlichen
OpenR4d10-Aktivierungsregister anbieten. Die Teilnahme ist freiwillig,
standardmäßig ausgeschaltet und für die Gerätefunktion nicht erforderlich.

Zulässige, getrennt wählbare Stufen:

1. anonyme Aktivierung: zufällige Geräte-ID, Hardware-/Softwareversion,
2. grobe Region: Land/Region/Stadt aus der IP serverseitig ableiten,
3. präzise GPS-Position: nur nach separater ausdrücklicher Einwilligung und nur
   wenn tatsächlich GPS-Hardware vorhanden ist.

Datenschutzregeln:

- keine heimliche Aktivierungsmeldung,
- keine vorausgewählten Einwilligungen,
- Einwilligung muss verständlich, informiert und jederzeit widerrufbar sein,
- Roh-IP niemals dauerhaft speichern; nach grober Geolokalisierung verwerfen,
- öffentlich nur grobe oder aggregierte Punkte anzeigen,
- präzise GPS-Position niemals öffentlich darstellen,
- Benutzer kann seinen Registereintrag am Gerät oder im Webinterface löschen,
- Registry-Endpunkt ist konfigurierbar und im öffentlichen Quellcode sichtbar.

RevolverMaps ist kein geeigneter Kern: Es war ein Website-Besucherwidget und
kein kontrollierbares Geräteverzeichnis. Bevorzugt wird ein eigener kleiner
Registry-Dienst mit PostgreSQL und einer OpenStreetMap-basierten Karte.

## 14. Internationalisierung

Standardsprache aller Funktionen, Schlüssel, Module und Entwicklertexte ist
Englisch. UI-Texte werden aus einer Übersetzungsdatenbank geladen; fehlt ein
Text, erfolgt ein sauberer Fallback auf Englisch.

Vollständig kuratierte Startsprachen:

- English,
- Deutsch,
- Polski,
- Français,
- Español.

Übersetzungen müssen sinngemäß zur tatsächlichen Funktion passen. Jeder
Übersetzungsschlüssel enthält deshalb einen Funktionskontext und darf nicht
blind maschinell Wort für Wort übersetzt werden. Weitere gängige Weltsprachen
können als Community-Sprachpakete ergänzt und über einen Vollständigkeitsstatus
gekennzeichnet werden.

Übersetzungsdateien liegen als menschenlesbare, validierbare Dateien im
öffentlichen Git-Repository. Nutzer dürfen neue Sprachen und Korrekturen über
Forks und Pull/Merge Requests beitragen. Automatische Prüfungen kontrollieren
Schema, vorhandene Schlüssel, Platzhalter, maximale Displaylängen, Kontext und
englischen Fallback. Eine Übersetzung wird erst nach Review als kuratiert
markiert; Maschinenübersetzung allein genügt nicht.

## 15. Öffentliche Projektwebsite und Besucherkarte

Die GitHub-Projektseite zeigt offen und klar beschriftet:

- einen Besucher-/Seitenaufrufzähler für alle Seitenaufrufe,
- eine Weltkarte mit ausreichend grober Herkunftsregion,
- getrennte Statistiken für Webseitenbesuche und freiwillig registrierte
  OpenR4d10-Geräte.

Es gibt keine heimlichen Tracker, kein Fingerprinting und keine Weitergabe an
Werbenetzwerke. Die Zählung erfolgt über einen eigenen, quelloffenen Endpoint.
Die Website erklärt direkt neben beziehungsweise unter der Karte, welche Daten
verarbeitet werden. Roh-IPs werden nur flüchtig zur groben Regionsermittlung
verarbeitet und nicht gespeichert; veröffentlicht werden nur aggregierte
Werte. Ein Do-Not-Track-/Opt-out wird respektiert. GitHub Pages selbst ist nur
das statische Frontend; Zähler und Karte benötigen den eigenen Registry-/Stats-
Backenddienst.

## 16. Informationen, Entwickler und Unterstützung

Der letzte Einstellungsmenüpunkt heißt „About & Support“ beziehungsweise
lokalisiert „Informationen & Support“. Er zeigt:

- OpenR4d10 by Robert Stefanowicz,
- aktive Core- und Hardwareversion,
- Repository-, Lizenz- und Mitwirkendenlinks,
- optionalen PayPal-/Unterstützungslink,
- daraus lokal erzeugten QR-Code.

Der PayPal-Link ist eine öffentliche Konfiguration und kein Secret. Er wird
erst eingetragen, sobald Robert den endgültigen Link festlegt. Solange das
Projekt keine rechtlich anerkannte Gemeinnützigkeit besitzt, darf die
Oberfläche keine steuerlich absetzbare „gemeinnützige Spende“ versprechen.

## 17. Softwarearchitektur

Empfohlener Kern:

- Debian 13 Trixie für `aarch64` auf Raspberry Pi Zero 2 W,
- Python-Core-Service,
- FastAPI für REST, WebSocket und Weboberfläche,
- SQLite mit versionierten Migrationen,
- PipeWire für Audio-Routing,
- BlueZ für Bluetooth-Audio und HID-Tastatur,
- WebRTC für Browser-Liveaudio,
- HTTP/HLS als kompatibler Fallback,
- systemd für Autostart, Watchdog und Wiederherstellung,
- lokales deutsches Speech-to-Text,
- lokales Text-to-Speech,
- modularer Dienst-Runner mit Berechtigungen und Ressourcenlimits.
- pro Dienst gehärtete systemd-Sandbox beziehungsweise gleichwertiger
  Container/Namespace mit `ProtectSystem=strict`, `ProtectHome=true`, privaten
  temporären Verzeichnissen, Capability-Entzug und expliziten Pfadfreigaben,
- Core-Broker als einzige Schnittstelle für Secrets, Audio, Mikrofon, Netzwerk
  und Hardware.

Das Whisplay besitzt keine eigenständige Anwendungsfirmware für die gesamte
Produktoberfläche. Die Anwendungslogik, Darstellung, Eingaben, Audio- und
Netzdienste laufen auf dem Raspberry Pi. Eventuelle Controller-Firmware auf dem
HAT wird nur über die dokumentierten Schnittstellen angesprochen.

## 18. Verbindlicher Entwicklungsablauf für jede Codex-Instanz

1. Diese Datei vollständig lesen.
2. Neueste Nutzeranweisung identifizieren.
3. Bestand prüfen: konkrete Modelle, Versionen, Maße und vorhandene Dateien.
4. Neue Erkenntnisse sofort in diese Datei einarbeiten.
5. Widersprüche auflösen; niemals stillschweigend alte und neue Regeln mischen.
6. Erst danach Architektur, Code, UI oder CAD ändern.
7. Quellcode vollständig liefern und lokal ausführen.
8. Renderings visuell prüfen.
9. Hardwarekompatibilität anhand Datenblatt und realen Maßen prüfen.
10. Keine Kaufempfehlung ohne vollständige Kompatibilitätsprüfung.
11. Keine erfundenen Bauteile, Anschlüsse, Tasten, Platinen oder Abmessungen.
12. Bestehende funktionierende Dateien nicht unnötig neu erstellen.
13. Änderungen testen und Ergebnis konkret dokumentieren.
14. Änderungsprotokoll unten ergänzen.

## 19. Noch zu verifizieren

- exakte Version und Maße des tatsächlich gelieferten ALPS-Encoders,
- Pinbelegung beider Encoderachsen und des gemeinsamen Drucktasters,
- freie GPIOs nach Montage von Whisplay und PiSugar,
- mögliche GPIO-/I²C-Erweiterung für Encoder und weitere Taster,
- reale Stromaufnahme aller Betriebsarten,
- Akkulaufzeit mit internem Lautsprecher, WLAN und Bluetooth,
- exakte Whisplay-Audio-Schnittstellen und maximal erreichbare Lautstärke,
- mechanische Endmaße des vollständigen Stacks,
- thermisches Verhalten im geschlossenen Gehäuse,
- Leistungsgrenze des Pi Zero 2 W bei gleichzeitiger WebUI, Audio, STT und
  mehreren Streams,
- verfügbare und zulässige BrandMeister-Audiozugänge,
- API- und Loginbedingungen externer Dienste.
- endgültiger öffentlicher Registry-Endpunkt, Datenschutzerklärung und
  Löschprozess,
- endgültiger PayPal-/Unterstützungslink,
- rechtliche Verantwortlichkeit und Aufbewahrungsdauer des Aktivierungsregisters.
- endgültiger GitHub-Pages-/Stats-Backend-Endpunkt und Datenschutztext,
- Discord-App-/OAuth-Konzept, Voice-SDK-Kompatibilität auf ARM/Linux und
  Moderationsstruktur der Länder-/Sprachkanäle,
- Backup-Zielmodule, Verschlüsselungsformat und Wiederherstellungstests,
- Signaturverfahren und Reviewprozess des Dienst-Stores.

## 20. Veröffentlichung, Installation und Geheimnisschutz

Das Projekt wird öffentlich mit einsehbarem Quellcode veröffentlicht. Die
gewünschte Lizenz erlaubt Nutzung und Veränderung nur **nichtkommerziell** und
verlangt immer Namensnennung.

Rechtlich wichtig: Eine Lizenz mit Nichtkommerziell-Klausel gilt nach der
OSI-Definition nicht als „Open Source“. Das Projekt wird deshalb präzise als
**source-available, noncommercial** bezeichnet.

Lizenzaufteilung:

- Software, Firmware und Installationsskripte:
  PolyForm Noncommercial License 1.0.0 plus verpflichtender Erhalt des
  Namensnennungs-/NOTICE-Hinweises.
- Gehäuse, CAD-, 3D-Druck-, Grafik-, Dokumentations- und Designdateien:
  Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International.

Verbindliche Schutzregeln:

- niemals echte Passwörter, WLAN-Schlüssel, SSH-Schlüssel, API-Schlüssel,
  Tokens, Cookies, Pi-Zugangsdaten, Codex-/OpenAI-Zugangsdaten oder private
  Konfigurationsdateien einchecken,
- keine Telemetrie und kein automatisches Hochladen lokaler Konfigurationen,
- Mumble-, Discord- und Store-Credentials niemals im Repository,
- lokale Secrets ausschließlich auf dem Gerät erzeugen,
- Secret-Dateien mit Dateirechten 0600 speichern,
- Beispielkonfigurationen enthalten nur eindeutig erkennbare Platzhalter,
- .gitignore blockiert .env, Schlüssel, Zertifikate, Datenbanken, Backups,
  Aufnahmen, Logs und lokale Konfigurationen,
- vor jedem Commit und Release automatischen Secret-Scan ausführen,
- Installer lädt ausschließlich öffentliche Projektdateien und überträgt
  keinerlei Nutzerdaten.

Geplanter Installationsaufruf nach Veröffentlichung des Repositories:

```bash
curl -fsSL https://raw.githubusercontent.com/p1337/OpenR4d10/main/bootstrap.sh | sudo bash
```

Der Installer ist wiederholbar und für Debian 13 Trixie auf dem Raspberry Pi
Zero 2 W ausgelegt. `bootstrap.sh` lädt das vollständige öffentliche Archiv
ohne Git-Abhängigkeit und übergibt an den einzigen lokalen Installer
`install.sh`. Dieser installiert Systempakete, Anwendung, Systemdienst und
lokale Konfiguration. Hardwaretreiber dürfen erst aktiviert werden, wenn die
tatsächlich verwendete Hardwareversion verifiziert ist.

## 21. Änderungsprotokoll

### 2026-10-30 – Persistente Whisplay-Displayhelligkeit

- Robert verlangt eine Displayhelligkeit in den Einstellungen, deren Wert
  dauerhaft gespeichert wird. Die lokale Weboberfläche erhält deshalb einen
  klar beschrifteten Regler von 0 bis 100 Prozent mit sofortiger Anwendung.
- Die Einstellung wird unter einem nicht geheimen Schlüssel in der vorhandenen
  SQLite-Datenbank gespeichert, im normalen Kernbackup mitgesichert und beim
  Start vor dem ersten Anwendungsbild wieder an den Displayadapter übergeben.
- Die offizielle aktuelle PiSugar-Whisplay-Laufzeit bestätigt auf Raspberry Pi
  Zero 2 W Software-PWM für den Backlight-Ausgang: `set_backlight(0..100)`
  verwendet 1000 Hz und invertiert den Tastgrad für den aktiven-low Anschluss
  auf dem bereits belegten BCM22; geprüft wurde Hersteller-Commit
  `bb4cdcc5371838009804940559e828d6a7a7ba04`. OpenR4d10 übernimmt diese bestehende
  Herstellerlogik in den eigenen exklusiven `WhisplayPanel`-Besitzer; es wird
  weder `whisplay-daemon` parallel gestartet noch ein neuer GPIO erfunden.
- Der native frühe Bootplayer besitzt keine SQLite-Abhängigkeit und läuft vor
  dem Anwendungskern. Der gespeicherte Wert gilt daher ab Übernahme durch die
  physische OpenR4d10-UI; eine separate zweite Boot-Konfiguration wird nicht
  eingeführt.

### 2026-10-30 – Dauerhafte, sortierbare Radios und Pflichtbackup vor Updates

- Robert legt fest: Befindet sich die Geräteoberfläche im Dienst `RADIO` und
  läuft noch kein Stream, startet ein kurzer rechter Klick beziehungsweise
  Enter immer den ersten Eintrag der aktuellen Senderliste. Bei laufendem oder
  pausiertem Stream bleibt dieselbe Taste echtes Play/Pause.
- Die sechs kuratierten Standardsender werden einmalig in die dauerhafte
  SQLite-Senderbibliothek übernommen. Ab dann dürfen sie wie eigene Sender
  umsortiert und gelöscht werden; neue Sender werden über die Weboberfläche
  angelegt. Ein gelöschter Standardsender darf weder beim Neustart noch nach
  einem Update erneut erzwungen werden. Kanalwahl und Anzeige verwenden diese
  persönliche Reihenfolge statt einer unveränderlichen Preset-Reihenfolge.
- Vor jedem Update über den vorhandenen Bootstrap-/Installerpfad muss zwingend
  ein konsistentes, secret-freies Kernbackup der vorhandenen Datenbank erzeugt
  werden. Bei einem Backupfehler bricht die Installation vor jeder Änderung
  ab. Das persistente Zustandsverzeichnis bleibt zusätzlich grundsätzlich
  außerhalb der aus GitHub geladenen Release-Dateien.

### 2026-10-30 – Systemupdate direkt aus der Weboberfläche

- Robert verlangt, ein OpenR4d10-Update ohne SSH-Konsole direkt in der lokalen
  Webmaske anstoßen zu können. Dafür wird ein ausdrücklich zu bestätigender
  System-Update-Bereich mit sichtbarem Status ergänzt.
- Der bestehende unprivilegierte Webdienst darf dadurch keine allgemeinen
  Administratorrechte bekommen. Er erstellt nur eine feste, inhaltlose
  Anforderungsdatei im eigenen Runtime-Verzeichnis. Ein root-eigener
  systemd-Path und ein fest installiertes Updateprogramm reagieren darauf und
  rufen ausschließlich den vorhandenen Git-freien Bootstrap von
  `p1337/OpenR4d10` auf; Browserdaten dürfen weder URL noch Argumente oder
  Shellbefehle bestimmen.
- Updateprogramm und Weboberfläche verwenden eine kleine, nicht geheime
  Statusdatei für `idle`, `queued`, `running`, `failed` und `rebooting`.
  Doppelte Anforderungen werden abgewiesen. Bei Erfolg gelten weiterhin alle
  Installerprüfungen und der bereits festgelegte automatische Neustart.

### 2026-10-30 – Encoderwerte müssen reale Medienfunktionen steuern

- Der reale Test zeigt zusätzlich: Die virtuelle Lautstärke lief sichtbar von
  ungefähr 30 bis 100 Prozent, ohne die hörbare Lautstärke zu ändern. Ebenso
  veränderte die Kanalachse nur eine Zahl, nicht den abgespielten Radiosender.
  Beides sind Präsentationszustände ohne bisherige Verbindung zum Medienkern
  und damit derselbe Architekturfehler wie beim zunächst wirkungslosen Enter.
- `left_outer` muss die echte `mpv`-Lautstärke begrenzt von 0 bis 100 ändern.
  Jede Encoder-Rastung beziehungsweise jeder W/S-Tastendruck verändert sie
  verbindlich um 10 Prozentpunkte, nicht in langsamen Ein-Prozent-Schritten.
  Schnell aufeinanderfolgende virtuelle oder spätere physische Eingaben werden
  zentral serialisiert, damit keine Lautstärke- oder Sender-Rastung durch
  parallele Browseranfragen verloren geht.
  `right_outer` wählt im Radio-Dienst zyklisch den vorherigen beziehungsweise
  nächsten kuratierten Sender und lädt dessen echten Stream. Tastatur,
  Webtasten und spätere GPIO-Encoder verwenden dafür weiterhin ausschließlich
  den gemeinsamen `device_input`-Pfad.
- Im Radio-Hauptbild ist der verständliche Sendername statt der technischen
  Stream-Adresse darzustellen. Das bereits sicher lokal zwischengespeicherte
  Senderbild wird groß genutzt; wenn es fehlt, erscheint eine klare lokale
  Initialenkachel. Der bisherige künstliche Equalizer wird entfernt. Bei einem
  Live-Stream darf keine erfundene Fortschritts- oder Audiodatenanzeige
  suggeriert werden.
- Die Auswahl eines kuratierten Senders stößt das bereits begrenzte, dekodierte
  und lokal neu codierte Senderbild-Caching im Hintergrund an. Der Streamstart
  darf weder auf das Bild warten noch bei dessen Ausfall scheitern; bis zum
  nächsten Display-Refresh bleibt die Initialenkachel sichtbar.

### 2026-10-30 – Enter/ rechter Kurzklick steuert den echten Audioplayer

- Der reale Browsertest hat gezeigt: Enter erreichte zwar als logischer
  `right_press` die Geräteanzeige und wechselte dort das Play/Pause-Symbol,
  der laufende Webradio-Stream wurde jedoch nicht pausiert. Ursache war eine
  fehlende Verbindung zwischen dem bereits gemeinsamen Eingabepfad und dem
  vorhandenen Medienkern.
- Ein kurzer rechter Klick muss über den zentralen Anwendungskern denselben
  echten Play/Pause-Befehl an `mpv` senden wie die Web-Schaltfläche. Erst nach
  erfolgreicher Medienaktion darf die Geräteanzeige den neuen Zustand zeigen.
  Enter, der spätere Encoder und der Browserknopf bleiben dabei ein gemeinsamer
  logischer Eingabepfad; eine zweite Tastatur-Mediensteuerung ist verboten.
- Ein langer rechter Klick bleibt ausschließlich das Quick-Menü und darf den
  Stream nicht pausieren. Ohne aktiven oder pausierten Stream wird kein
  erfundener Wiedergabezustand erzeugt, sondern eine klare Fehlermeldung
  zurückgegeben.

### 2026-10-30 – Ein-Befehl-Installation startet nach Erfolg selbst neu

- Robert verlangt, dass der Ein-Befehl-Installer den für neue Kernelmodule und
  Overlays notwendigen Neustart selbst ausführt. Diese neue ausdrückliche
  Anweisung ersetzt die frühere Regel, den Pi nicht automatisch neu zu starten.
- Nach vollständig erfolgreicher Installation, Web-Healthcheck und Diagnose
  kündigt `install.sh` den Neustart sichtbar an, synchronisiert ausstehende
  Schreibvorgänge und fordert den systemd-Neustart an. Bei jedem vorherigen
  Fehler darf kein Neustart ausgelöst werden.
- Für bewusste Wartungsarbeiten bleibt `--no-reboot` als ausdrückliche
  Ausnahme erhalten. `--check` ist weiterhin strikt nur lesend und startet
  niemals neu. `bootstrap.sh` reicht beide Optionen an den einzigen lokalen
  Installer weiter.
- Der reale Neustart nach 0.10.6 bestätigt ALSA-Karte `whisplaysound`, Codec
  WM8960 und den Lautsprecherregler auf 80. Offen bleibt ein realer Hörtest;
  die PiSugar-Warnung betrifft weiterhin ausschließlich Telemetrie.

### 2026-10-30 – Trixie-Kernel-Headerpaket am realen Pi korrigiert

- Der erste Lauf von 0.10.5 wurde vor der Treiberinstallation von APT mit
  `Unable to locate package raspberrypi-kernel-headers` beendet. Dieser ältere
  Paketname ist in Roberts Debian-13-/Raspberry-Pi-Repository nicht vorhanden.
- Auf dem realen System mit Kernel `6.18.50+rpt-rpi-v8` ist das passende Paket
  `linux-headers-6.18.50+rpt-rpi-v8` in Version `1:6.18.50-1+rpt1` installiert;
  sein Metapaket heißt `linux-headers-rpi-v8`. Der Build-Link zeigt auf
  `/usr/src/linux-headers-6.18.50+rpt-rpi-v8`.
- Der Hauptinstaller muss deshalb `linux-headers-$(uname -r)` installieren und
  anschließend `Makefile` sowie `scripts/basic/fixdep` im tatsächlichen
  Kernel-Buildverzeichnis prüfen. Ein allgemeines oder geratenes Headerpaket
  darf die passend zum laufenden Kernel erforderlichen Header nicht ersetzen.

### 2026-10-30 – Offiziellen Whisplay-Audiotreiber in den Hauptinstaller aufnehmen

- Robert beauftragt ausdrücklich, die fehlende interne Audioausgabe jetzt in
  den vorhandenen Ein-Befehl-Installer einzubauen. Es entsteht kein zweiter
  Installationsweg.
- Verwendet wird ausschließlich der offizielle vereinheitlichte PiSugar-
  `whisplay-soundcard`-Treiber für WM8960 und ES8389, gepinnt auf Hersteller-
  Commit `736975188ebbe146d319e450aad19c218a310611`. Der Installer darf keine
  Codec-Revision raten.
- Der geprüfte Herstellerquellcode wird mit unveränderter Apache-2.0-Lizenz,
  Herkunft und Prüfsumme im Repository mitgeführt. Dadurch bleiben
  `bootstrap.sh` und `install.sh` Git-frei und benötigen während der
  Installation keinen zweiten Fremddownload.
- Der Hauptinstaller installiert die Kernel-Bauwerkzeuge, aktiviert I²C und
  I²S, baut das Modul für den laufenden Kernel, installiert Overlay und ALSA-
  Konfiguration und meldet den zwingend erforderlichen Neustart klar. Die
  spätere ausdrückliche Entscheidung zum automatischen Neustart hat gegenüber
  der damaligen manuellen Neustartgrenze Vorrang.
- `doctor` muss unterscheiden zwischen fehlendem Treiber, installiertem aber
  noch nicht durch Neustart aktiviertem Treiber und einer vorhandenen ALSA-
  Karte `whisplaysound`. Reale Lautsprecherfunktion ist erst nach Neustart und
  Hörtest bestätigt.

### 2026-10-30 – Laufender SWR3-Stream ohne Whisplay-Audiogerät bestätigt

- Auf dem realen Pi mit OpenR4d10 0.10.4 meldet der Webradio-Core SWR3 als
  `playing`; der zugehörige `mpv`-Prozess läuft ohne gemeldeten Streamfehler.
  Fehlender Ton ist deshalb kein Lautstärke-, WLAN- oder Senderproblem.
- ALSA stellt ausschließlich `vc4-hdmi` bereit. Es gibt weder eine
  `whisplaysound`-Karte noch `/dev/i2c-*`; in der Bootkonfiguration sind nur
  SPI und der generische Audio-/HDMI-Pfad aktiv. Der interne Lautsprecher kann
  ohne Whisplay-I2C/I2S-Treiber kein Signal erhalten.
- Das offizielle PiSugar-Whisplay-Projekt stellt inzwischen einen einheitlichen
  Soundkartentreiber für WM8960 und ES8389 bereit. Auf diesem HAT ist kein
  auslesbarer HAT-EEPROM-Knoten vorhanden, weshalb der offizielle manuelle
  `whisplay-soundcard`-Overlaypfad benötigt wird. Eine Integration muss gegen
  eine geprüfte Herstellerrevision gepinnt werden, Bootdateien nachvollziehbar
  ändern und anschließend einen Neustart plus reale ALSA-/Lautsprecherprüfung
  verlangen.

### 2026-10-30 – PiSugar-Stromversorgung real bestätigt

- Robert bestätigt den laufenden Pi im Akkubetrieb über den montierten
  PiSugar. Die bisherige Webformulierung „PiSugar-Adapter fehlt“ war deshalb
  sachlich falsch: Hardware und Stromversorgung sind vorhanden.
- Nicht eingerichtet ist ausschließlich der Software-/Telemetrieadapter für
  Ladestand und weitere PiSugar-Messwerte. Die Weboberfläche muss genau diese
  Grenze benennen und darf weder fehlende Hardware noch bereits messbare
  Batteriedaten behaupten.

### 2026-10-30 – Browser-Tastatursteuerung und sichere PTT-Taste

- Die virtuelle Encoderbedienung erhält die verbindliche Tastaturbelegung
  `WASD`, Pfeiltasten, Leertaste, Enter und `Q` für PTT. Alle Tasten verwenden
  die bestehende logische Eingabeschnittstelle und keine parallele Navigation.
- `Q` ist ein gehaltenes Signal: `keydown` aktiviert PTT, `keyup`, Fokusverlust
  oder ausgeblendeter Tab deaktiviert es. Damit darf PTT nicht durch einen
  verlorenen Tastaturzustand eingeschaltet bleiben.
- Tastaturkürzel greifen nicht in Formularfeldern oder editierbaren Elementen.
  Solange kein echter berechtigter PTT-Dienstadapter bereitsteht, zeigt die UI
  nur den Eingabestatus und behauptet keine Mikrofon- oder Audioübertragung.

### 2026-10-30 – Adapterstatus und reale Audiogrenze präzisiert

- Die reale Webansicht von 0.10.1 zeigte das Whisplay korrekt als verbunden,
  verwendete in der allgemeinen Statusüberschrift bei allein fehlender
  PiSugar-Telemetrie aber noch den pauschalen Text, Display und Energie seien
  offen. Die Zusammenfassung muss die tatsächlich offenen Adapter einzeln
  benennen und darf einen funktionierenden Displayadapter nicht relativieren.
- Ein Wiedergabeversuch lieferte `timed out`. Vom Pi aus wurden die geprüften
  SWR3-, sunshine-live- und Deutschlandfunk-Streams mit `ffprobe` erfolgreich
  als MP3 erreicht; WLAN und Streamquellen sind damit nicht die Ursache.
- Auf dem realen System ist derzeit ausschließlich `vc4-hdmi` als ALSA-
  Wiedergabegerät vorhanden. Der Whisplay-Lautsprecher ist noch nicht als
  Audiogerät eingebunden. Bis dessen exakte Codec-/Overlay-Konfiguration
  verifiziert ist, darf keine funktionierende interne Audioausgabe behauptet
  und kein Treiber geraten werden.

### 2026-10-30 – Reale UI bestätigt; virtuelle Encoderbedienung

- Nach Installation von 0.10.1 bestätigt Robert die native 240-x-280-UI auf
  dem realen Whisplay als sichtbar und optisch gelungen. Seit der korrigierten
  Displayübergabe treten keine neuen Displayadapterfehler auf.
- Da die bestellten Doppelencoder noch nicht geliefert sind, muss die bereits
  vorhandene hardwareunabhängige Eingabeschnittstelle jetzt auch über die
  lokale Weboberfläche bedienbar sein. Die Webbedienung verwendet dieselben
  vier logischen Drehachsen und zwei Druckereignisse wie der spätere
  GPIO-Adapter; sie ist keine parallele Navigationsimplementierung.
- Browserereignisse werden streng auf bekannte Controls, kleine ganzzahlige
  Drehschritte und begrenzte Haltedauer validiert. Sie aktualisieren die echte
  physische Anzeige unmittelbar, ohne GPIO-Nummern oder Encoderverdrahtung
  vorwegzunehmen.

### 2026-10-30 – Displayübergabe bei Installation im laufenden System

- Auf dem frisch installierten realen Pi wurde beobachtet, dass der
  Anwendungsdienst sofort startet, der frühe Bootplayer in diesem bereits
  laufenden Boot aber erwartungsgemäß noch nicht ausgeführt wurde. Dadurch
  fehlte `/run/openr4d10-boot` und die Geräte-UI meldete wiederholt
  `Boot display runtime is absent`, während Weboberfläche, WLAN und SSH stabil
  blieben.
- Der Anwendungsdienst deklariert nun denselben erhaltenen Laufzeitordner wie
  der Bootplayer. Bei einer laufenden Installation kann die UI den gemeinsamen
  Lock direkt übernehmen und das Panel initialisieren; beim normalen Neustart
  bleibt die vorhandene Release-/Lock-Übergabe vom Bootplayer unverändert.
- Ein Regressionstest prüft die systemd-Vertragswerte für gemeinsamen
  Laufzeitordner, Schreibrechte und Erhalt über Dienstneustarts.

### 2026-10-30 – Kuratierte Radio- und Feed-Grundausstattung

- Die lokale Weboberfläche erhält eine sofort nutzbare, kuratierte Auswahl
  verifizierter Webradios. Gewünscht sind insbesondere SWR3, sunshine live,
  Deutschlandfunk, RMF FM, Radio ZET und ein geeigneter BBC-Nachrichten-/
  Radiodienst; weitere seriöse Sender dürfen ergänzt werden.
- Zusätzlich werden mehrere seriöse RSS-/Atom-Nachrichtenquellen als Presets
  angeboten. Stream- und Feed-Adressen müssen vor Aufnahme gegen offizielle
  beziehungsweise eindeutig zuständige Quellen geprüft werden und bleiben als
  aktualisierbare Daten getrennt von Wiedergabe- und Parserlogik.
- Senderbilder dürfen nicht ungeprüft als fremder Webinhalt in die Oberfläche
  eingebettet werden. Zulässig sind begrenzt geladene, dekodierte und lokal neu
  erzeugte Bilder mit dokumentierter Quelle oder sichere lokale Ersatzkacheln.
  Ausfall eines Bildes darf Wiedergabe und Senderauswahl nicht blockieren.
- Umgesetzt sind sechs Radios (SWR3, sunshine live, Deutschlandfunk, RMF FM,
  Radio ZET und BBC World Service) sowie vier Nachrichtenfeeds (tagesschau,
  Deutschlandfunk Nachrichten, RMF24 und BBC News World). Die Auswahl kann
  direkt abgespielt beziehungsweise geladen und ein Radiosender idempotent in
  die Favoriten übernommen werden.
- Der öffentliche Status enthält weder die internen Stream- und Feed-Adressen
  noch die entfernten Bildadressen. Senderbilder werden auf maximal 2 MiB und
  20 Megapixel begrenzt, dekodiert, auf höchstens 256 × 256 verkleinert und als
  lokales JPEG neu erzeugt; bei Fehlern bleibt eine Initialenkachel sichtbar.
- Quellen, Adressen, Prüfreferenzen und Aktualisierungsregeln sind dauerhaft in
  `docs/PRESETS.md` dokumentiert. Nach Umsetzung umfasst die lokale Suite 45
  Tests, davon fünf plattformbedingt unter Windows übersprungen.

### 2026-10-30 – Portables, secret-freies Kernbackup

- Der Core erhält ein versioniertes Backup-Paket mit einer über die SQLite-
  Backup-API konsistent erzeugten Datenbankkopie, öffentlichem Manifest,
  Prüfsumme und nicht geheimem Dienstplan. Medien-, Aufnahme-, WLAN-, Konto-,
  Token-, Passwort-, Schlüssel- und Secret-Dateien sind nicht enthalten.
- Eine Wiederherstellung validiert Archivstruktur, Größenlimits, SHA-256,
  SQLite-Integrität und unterstützte Schemaversion. Sie verweigert den Vorgang,
  solange der Systemdienst läuft, und überschreibt eine vorhandene Datenbank
  nur nach ausdrücklichem `--replace`.
- Backup und Restore verwenden atomare Zieldateien und erlauben keine
  frei wählbaren Archivpfade oder Pfadtraversierung. Externe Zielmodule wie
  USB, SFTP und WebDAV bleiben separate, standardmäßig deaktivierte Adapter.

### 2026-10-30 – Dauerhafter Dienst-Lebenszyklus

- Dienstmodule erhalten einen dauerhaften Aktiv-/Inaktiv-Zustand in der
  versionierten Datenbank und eine Bedienung in der Weboberfläche. `System`,
  Webradio, lokale Medien, Recorder, Feeds und Webcam sind als vorhandene
  Kernmodule standardmäßig aktiv; konto- und adapterabhängige Module bleiben
  standardmäßig inaktiv.
- Ein deaktivierter Dienst wird weder als bereit ausgegeben noch über seinen
  externen Socket angesprochen. Aktivieren allein genügt bei externen Modulen
  weiterhin nicht: Manifest, erreichbarer Adapter und Status-Handshake bleiben
  zwingend.
- Das Systemmodul kann nicht deaktiviert werden. Das Deaktivieren einer aktuell
  laufenden Medienquelle beendet deren Wiedergabe beziehungsweise Aufnahme,
  bevor der Zustand gespeichert wird.

### 2026-10-30 – Isolierter Vertrag für externe Dienstadapter

- Externe Dienste mit eigenen Konten oder Tokens werden nicht als Bibliothek im
  privilegierten Hauptprozess geladen. Jeder Dienst läuft zukünftig als
  eigener, lokal installierter Prozess mit eigener Unix-Socket-Schnittstelle
  und kann dadurch einen eigenen Systembenutzer sowie ausschließlich seine
  eigenen geschützten Zugangsdaten erhalten.
- Der OpenR4d10-Kern kennt nur versionierte, nicht geheime TOML-Manifeste in
  `/etc/openr4d10/services.d` und ein begrenztes JSON-Protokoll über lokale
  Unix-Sockets. Weder Shell-Aufruf noch Adaptercode, Token oder Passwort werden
  in den Kern beziehungsweise seine SQLite-Datenbank übernommen.
- Ein vorhandener Menüeintrag allein macht einen externen Dienst nicht bereit:
  erst Manifest, erreichbarer Socket und erfolgreicher Status-Handshake dürfen
  den Zustand `ready` ergeben. Fehlende oder fehlerhafte Adapter bleiben
  sichtbar und ehrlich als zu konfigurieren beziehungsweise fehlerhaft markiert.

### 2026-10-30 – Projektwissen versioniert; Sender- und Medienbibliothek

- Die zentrale Masteranweisung lag versehentlich nur in einem durch
  `.gitignore` ausgeschlossenen Arbeitsordner. Sie liegt ab sofort als
  `CODEX_TO_CODEX_MASTER.md` im Repository-Stamm, wird mit Git versioniert und
  ist damit für nachfolgende Projektchats tatsächlich verfügbar.
- Radiosender können über die lokale Weboberfläche gespeichert, abgespielt und
  gelöscht werden. Dauerhaft gespeicherte Sender-URLs dürfen keine Query-Teile
  enthalten, damit temporäre Tokens oder ähnliche Werte nicht versehentlich in
  SQLite landen; solche URLs bleiben nur für direkte, nicht persistente
  Wiedergabe zulässig.
- Der geschützte lokale Medienordner kann ohne Shell eingelesen werden. Nur
  freigegebene Audio-/Medienendungen innerhalb dieses Ordners werden
  indexiert; entfernte Dateien verschwinden beim nächsten Scan wieder.
- Öffentliche Statusdaten enthalten bei Sendern keine vollständigen
  Datenbankwerte und bei lokalen Medien keine Dateipfade. Gleichzeitige
  Zugriffe des Webservers und der Hauptschleife auf SQLite werden serialisiert.
- Nach diesem Bibliotheksblock bestanden 34 lokale Tests; vier zusätzliche
  Linux-/C-spezifische Prüfungen liefen erst in GitHub Actions beziehungsweise
  auf Linux. Mit dem anschließend implementierten Dienstadaptervertrag umfasst
  die Suite zunächst 38, nach dem Dienst-Lebenszyklus 39 und nach Backup/
  Restore 41 lokale Tests,
  davon fünf auf Windows übersprungene Linux-/C-/Unix-Socket-Prüfungen.

### 2026-10-30 – Dienstkatalog, Datenbank und sichere Medienprozesse

- Eine versionierte SQLite-Datenbank speichert ausschließlich nicht geheime
  Einstellungen, Dienstzustände, Sender, Kanäle, Medien- und
  Aufnahmemetadaten. Secret-ähnliche Schlüssel werden technisch abgewiesen.
- Der zentrale Katalog enthält alle fest eingeplanten und optionalen Dienste
  und unterscheidet sichtbar zwischen bereit, fehlender lokaler Abhängigkeit
  und erforderlicher lokaler beziehungsweise offizieller Anmeldung.
- Direkte Audioquellen, Webradio und lokale Medien verwenden einen isolierten
  `mpv`-Prozess mit dokumentiertem JSON-IPC. Aufnahmen verwenden `ffmpeg` ohne
  Shell und schreiben Opus-Dateien in das private Zustandsverzeichnis.
- Medien-URLs dürfen keine eingebetteten Zugangsdaten enthalten. Query-Strings
  werden weder im öffentlichen Status noch in Aufnahmedateinamen ausgegeben.
- Die lokale Weboberfläche erhält validierte JSON-Steuerung für
  Play/Pause/Stop und Aufnahme. Externe Dienste bleiben so lange als
  konfigurationspflichtig markiert, bis ihre echte API beziehungsweise ihr
  lokaler Adapter und die individuellen Benutzerdaten vorhanden sind.

### 2026-10-30 – Reales Whisplay-Bild bestätigt; Bootanimation korrigieren

- Die Geräteaufnahme `IMG_3019.mp4` zeigt die native Bootanimation auf dem
  realen Raspberry-Pi-Zero-2-W/Whisplay/PiSugar-3-Stack. SPI-Bildübertragung,
  Displayinitialisierung, RGB-Farbreihenfolge und Orientierung funktionieren.
- Die Skull-Phase ist auf dem realen Display zu kurz. Sie wird um 1,5 Sekunden
  verlängert, wobei die vorhandene Bewegung zeitlich interpoliert weiterläuft;
  ein eingefrorenes Standbild ist nicht zulässig.
- Die bisherige Warteschleife ab Originalframe 49 springt sichtbar vom letzten
  Frame zurück. Der Loop beginnt künftig bei Originalframe 54. Das ist bei
  mindestens 18 Loopframes der ähnlichste gemessene Anschluss an den letzten
  Originalframe. Originalvideo und dessen SHA-256 bleiben unverändert.
- Die Geräteaufnahme selbst wird nicht veröffentlicht oder in das Repository
  übernommen. Manifest, Preview und native OPB-Dateien müssen aus dem
  unveränderten freigegebenen Original reproduzierbar neu erzeugt werden.

### 2026-10-30 – UI-Entwicklung vor Eintreffen der Encoder

- Die beiden ALPS-Doppelencoder sind noch auf dem Versandweg aus China nach
  Waiblingen; Löten und reale Eingangstests sind derzeit unmöglich.
- Die physische 240-x-280-Geräteoberfläche wird trotzdem jetzt implementiert.
  Alle vier Drehachsen und beide Klickfunktionen erhalten eine hardwarefreie,
  testbare Ereignisschnittstelle; der GPIO-Adapter folgt nach Wareneingang und
  Vermessung.

### 2026-10-30 – Realer Hardwareaufbau und Display-Inbetriebnahme

- Robert hat die komplette 40-polige Stiftleiste des Pi Zero 2 W verlötet,
  das Whisplay vorn und das PiSugar-3-Akkupack hinten montiert.
- Der Pi und OpenR4d10 starten; die Whisplay-RGB-LED leuchtet. Das LCD blieb
  beim bisherigen `unconfigured`-Backend erwartungsgemäß schwarz.
- Der bestehende native Whisplay-Bootplayer wird deshalb in den GitHub-
  Hauptinstaller aufgenommen. Dies ist die erste reale Zielhardware-Prüfung;
  ein sichtbares Bild ist erst nach Ausführung auf Roberts Gerät bestätigt.
- Die endgültige Encoderverdrahtung bleibt bis zur eigenen Freigabe offen.

### 2026-10-30 – Hochformat und tatsächlicher unterer Flammenrand

- Robert bestätigt die Geräteausgabe im Hochformat: 240 Pixel Breite,
  280 Pixel Höhe. Das Seitenverhältnis ist nur leicht hochkant, nicht 9:16.
- Die Flammen müssen in der Endperspektive bis unmittelbar an den physischen
  unteren Displayrand reichen. Ein schwarzer Streifen unter dem Feuer ist
  ausdrücklich falsch, auch wenn die Videodatei nominell 240 × 280 Pixel hat.
- Der vollständige Schriftzug `OpenR4d10` darf durch die Anpassung nicht
  abgeschnitten werden. Kein pauschales Fill-/Cover-Zuschneiden der Vorlage.
- In der bisherigen nativen Datei endete die sichtbare Flammenbasis bei Zeile
  257 statt 279; die Platzierung wurde korrigiert. Originalvorlage und Animation
  bleiben unverändert. Nur der ungenutzte untere Bildrand wird entfernt und das
  Bild auf der nativen Fläche entsprechend tiefer platziert.
- Bootzeitangaben sind Planungswerte für Pi Zero 2 W, keine Messung von Roberts
  Gerät. Erste Displayanzeige und vollständig betriebsbereite UI unterscheiden.
- Korrekturprüfung: Alle beibehaltenen Pixel sämtlicher 73 Frames identisch;
  nur 22 beinahe schwarze Fußzeilen (maximaler RGB-Wert 13/255) entfernt.
  Die blaue Flammenbasis erreicht Zeile 279 in sämtlichen 24 Endschleifenframes.
  Neuer Paketumfang: 1.589.895 Byte, erstes Bild 12.551 Byte, MP4 235.268 Byte.

### 2026-10-30 – Native Whisplay-Bootmedien und frühestmögliche Anzeige

- Das freigegebene Projektvideo wird ausschließlich umgerechnet, nicht neu
  gestaltet: 240 × 280 Pixel, Seitenverhältnis der Vorlage erhalten, kein
  Abschneiden des Wortzeichens. Der zusätzliche schwarze Raum liegt oberhalb
  des quadratischen Motivs, sodass das Feuer unten bleibt.
- Für den Gerätestart wird das Video vorab in RGB565-Pixeldaten mit verlustfreier
  Einzelbildkompression übersetzt. Beim Booten sind weder MP4-Dekodierung noch
  Python, Browser, Audio oder Netzwerk für die Anzeige erforderlich.
- Vorgabe: Anfangsanimation einmal abspielen, anschließend die brennende
  Endperspektive in Bewegung halten, bis die echte Geräte-UI den Bildschirm
  übernimmt. Die Webserver-Bereitschaft allein ist keine Display-UI-Bereitschaft.
- Whisplay hat einen ST7789-LCD-Controller und flüchtiges Display-RAM, keinen
  eigenständigen programmierbaren Player mit Dateispeicher für Bootanimationen.
  Eine Animation kann nicht einfach dauerhaft auf dieses HAT geflasht werden.
- Bei kaltem Einschalten kann der vorhandene Pi-Stack vor Initialisierung von
  Host, SPI und LCD kein eigenes Bild liefern. Früher Start bedeutet optionaler
  Initramfs-Still-Splash und anschließend früher systemd-Player. Ein Bild exakt
  ab Anlegen der Versorgung benötigt eine andere Power-/Displayarchitektur,
  etwa laufenden Pi mit Display-Wakeup oder zusätzliche autonome Steuerhardware.
  Kein sofortiger Kaltstart wird behauptet oder ohne Messung zeitlich garantiert.
- Herstellerprofil verifiziert gegen PiSugar/Whisplay Commit
  `b2ccecab528caf939f0e3a900547cd094029f13e`: SPI0/CS0, BCM27 D/C,
  BCM4 Reset, BCM22 Backlight aktiv-low, RGB565, MADCTL 0xC0, y-Offset 20.
  Hersteller-Pythoncode setzt 100 MHz; eigener konservativer Startwert 32 MHz.
  24 Vollbilder/s benötigen allein für Pixel 25,8048 Mbit/s. Reale Framerate,
  Farben, Bootlatenz und Übergabe sind auf der gelieferten Hardware zu messen.
- Der native Player und ein optionaler Initramfs-Pfad werden vorbereitet und
  softwareseitig geprüft; mangels angeschlossenem Pi/Whisplay sind sie nicht als
  hardwaregetestet oder bereits auf Roberts Pi installiert auszugeben.
- Umsetzung liegt in `boot/`, UI-Übergabe in
  `src/openr4d10/boot_display.py`. Erzeugt: 73 Frames mit 24 fps, 240 × 280,
  RGB565, 1.593.280 Byte Animationspaket; frühes Einzelbild 12.550 Byte.
  Das Originalvideo ist unverändert geblieben. Die letzten 24 Originalframes
  dienen als wartende Schleife; deren sichtbare Naht ist noch zu prüfen.
- Softwareprüfung: strikter C-Build, native Frame-Prüfsummen, Abweisung kaputter
  Dateien, Display-Lock-Übergabe und vorhandene Projekttests. 12 Tests bestanden;
  Shell-Syntax, systemd-Unit auf Entwicklungshost und erste RGB565-Pixel geprüft.
  Keine Hardwaremessung, kein Nachweis für ein Bild unmittelbar bei Stromzufuhr.

### 2026-10-30 – Zeitverlängerung ausdrücklich an Runway delegieren

- Robert verlangt ausdrücklich, die Verlängerungsanweisung an Runway zu geben.
  Eine weitere lokale Montage ist nicht der gewünschte Lösungsweg dieses
  Auftrags. Die lokale Originaldatei bleibt dennoch als Projektquelle erhalten.
- Runway erhält ausschließlich das verlinkte freigegebene Originalvideo und
  die Anweisung: je eine Sekunde davor und danach ergänzen, Skull/Kamera bzw.
  Endperspektive/Schrift unverändert halten, vorhandenes Feuer weiterbewegen,
  kompletten Originalmittelteil mit allen Bewegungen und Übergängen erhalten.
- Keine neue Typografie, kein neues Logo, kein neu interpretiertes Feuer,
  keine neue Kamerafahrt und keine neue Spiegelung anfordern.
- Die Anweisung wurde als Video-zu-Video-Auftrag an Runway übermittelt:
  Task-ID `605f497f-b315-4203-a738-003437cbcd76`. Das Ergebnis ist während der
  Generierung nicht als geprüft oder unverändert zu bezeichnen. Der exakt
  übermittelte Prompt liegt in `assets/boot/RUNWAY_EXTENSION_PROMPT.txt`.

### 2026-10-30 – Exakten Runway-Link sichern; neue Logo-Endsequenz verwerfen

- Robert legt ausdrücklich die Datei `d0c782ca-38a8-4a69-89a2-b369cf86b938.mp4`
  als freigegebenes Original fest. Sie wurde erneut aus dem gelieferten Link
  heruntergeladen und im Projekt als
  `assets/boot/OpenR4d10_APPROVED_ORIGINAL.mp4` gesichert.
- SHA-256 des Originals:
  `b15de122f95d0fd0281ab81e989cba5d715456a701eed686bf14fcdcb24d6c19`.
  Die Datei ist byteidentisch mit `OpenR4d10_V7_Runway_source.mp4`.
- Das ruhende brennende Skull-Intro wurde positiv bewertet. Der neu generierte
  brennende Logo-Nachlauf aus V9 ist verworfen und darf nicht weiterverwendet
  werden. Auch andere vollständige Neugenerierungen ersetzen das Original nicht.
- Es bleiben ausschließlich je eine zusätzliche Sekunde vorne und hinten.
  Das gesamte verlinkte Original wird unverändert in den Mittelteil übernommen.
- Für die korrigierte Nachlaufsekunde wird bewegtes Originalmaterial aus der
  freigegebenen brennenden Endperspektive wiederverwendet, mit einem kurzen
  Übergang an der Anschlussstelle. Keine neue Schrift und keine neue
  Feuerdarstellung im Nachlauf generieren. Die bestehende Endperspektive bleibt.
- Signierte Download-URLs und deren Zugriffstokens werden nicht in
  Projektdateien oder öffentliche Repositories geschrieben.

### 2026-10-30 – Freigegebenen Mittelteil erhalten; je eine Sekunde ergänzen

- Robert gibt die Animation mit brennendem Wortzeichen ausdrücklich frei und
  verlangt anschließend ausschließlich eine Verlängerung um je eine Sekunde
  vorne und hinten. Mittelteil, Perspektive, Schrift und Bewegung dürfen bei
  dieser Änderung nicht nochmals neu generiert oder umgestaltet werden.
- Vorne: eine zusätzliche Sekunde ruhender Skull bei ruhiger Kamera; dessen
  Flammen brennen natürlich weiter. Hinten: eine zusätzliche Sekunde derselben
  Endperspektive mit lebenden Flammen und brennendem `OpenR4d10`.
- Keine eingefrorenen Endbilder als Ersatz für laufendes Feuer. Kamera und
  Schriftform bleiben in den Verlängerungen stabil.
- Grundlage ist der fertige, freigegebene dreisekündige Pass mit Task-ID
  `00ede6a9-9ca5-4d81-be35-a2d2071c5cbb`; dessen lokale Originaldatei ist
  `OpenR4d10_V7_Runway_source.mp4`. Bei Erhalt aller 73 Originalframes mit
  24 fps plus zweimal 24 Erweiterungsframes dauert der Master 121/24 Sekunden
  (5,041667 s). Dies ersetzt die zuvor abgeleitete 2,5-Sekunden-Endfassung.
- Der separat gestartete alternative Viersekunden-Timingversuch wird nicht
  als Ersatz für diesen freigegebenen Mittelteil verwendet.
- Der zusammengesetzte Master heißt
  `OpenR4d10_V9_APPROVED_PLUS_1S_1S_960.mp4`. `OpenR4d10_V9_verification.json`
  dokumentiert 24 + 73 + 24 Frames und identische Prüfsummen der decodierten
  RGB-Mittelframes vor der H.264-Ausgabecodierung. Vollständiger Produktionsbrief:
  `OpenR4d10_VIDEO_KI_Prompt_v9.txt`; Assembler:
  `assemble_openr4d10_approved_extension.py`.

### 2026-10-30 – KI-Feuerpass akzeptiert; Rauch-Reveal und brennender Schriftzug

- Robert bewertet den ersten echten Runway-Video-KI-Pass positiv. Die laufende
  Aufgabe wird mit diesem Video als Bewegungsreferenz weitergeführt.
- Am Ende breiten sich die eigenen Skull-Flammen über die komplette untere
  Bildschirmkante aus. Der Großteil der Flammen bleibt im unteren Fünftel.
- Danach erscheint der Schriftzug `OpenR4d10` hochwertig und cineastisch aus
  feinem Rauch und fängt selbst Feuer. Das Gesicht/Skull bleibt das ursprüngliche
  Anfangssignet; der brennende Schriftzug ist die Endmarke.
- Typografievorgabe für die Video-KI: moderne geometrische Sans-Serif,
  ExtraBold/Heavy, aufrecht, kräftige gleichmäßige Strichstärken, kompakte klare
  Buchstaben, sorgfältig enge Laufweite, horizontal ausgerichtet. Schreibweise
  exakt `OpenR4d10`: großes O und R, kleines pen und d, Ziffern 4, 1, 0.
  Weiß auf tiefschwarzem Grund; flache klare Glyphen statt Schrägschrift,
  metallischem 3D-Emblem oder ausgetauschten Buchstaben.
- Die Buchstaben bleiben lesbar, während dünne blaue Flammen an den Kanten
  zünden und weiß-gelb-orange Flammenzungen darüber aufsteigen. Rauch bleibt
  zurückhaltend und darf das Wort nicht verdecken.
- Die Acrylspiegelung ist ausdrücklich gestrichen. Diese neue Entscheidung
  ersetzt alle vorherigen Spiegelungsforderungen dieses Bootscreens.
- Die Flammen werden als Vordergrund über Schrift und Rauch komponiert.
  Kein deckender schwarzer Rechteckhintergrund darf Feuer verdecken.
- Neueste Zeitvorgabe: Der Skull brennt eine volle Sekunde bei ruhiger Kamera,
  bevor der Flug startet. Die bisherige 0,5-Sekunden-Startphase ist aufgehoben.
  Bei Erhalt des einsekündigen Flugs und der halben Sekunde Endmarke ergibt
  sich eine 2,5-Sekunden-Endfassung: 0–1 s Skull, 1–2 s Flug, 2–2,5 s Logo-Reveal
  und Entzündung. Diese letzte Vorgabe ersetzt das ältere 2,0-Sekunden-Timing.

### 2026-10-30 – V5 verworfen; Video-KI und verbindliche Ebenenreihenfolge

- V5 und alle lokalen Standbild-Verformungsversuche sind als unzureichend
  verworfen. Verschiebung, Mesh-Warp oder Helligkeitsflackern dürfen nicht
  als echte Flammensimulation oder generiertes Feuer ausgegeben werden.
- Eine Image-to-Video-KI soll zeitlich neue Flammenzungen, Öffnungen,
  Verzweigungen, Wirbel und auslöschende Spitzen erzeugen. Die Vorlage bestimmt
  Startbild, Gesicht und Feuerstil; sie friert die Feuerkonturen nicht ein.
- Neue Feinstruktur muss in den Videoframes entstehen. Hochskalieren,
  Nachschärfen oder engeres Zuschneiden des 1254-Pixel-JPEGs erzeugt keine neue
  Auflösung und darf nicht so beschrieben werden.
- 0–0,5 s: ruhige Kamera, ursprüngliche Skull-Neigung, natürlich brennende
  Haarflammen. 0,5–1,5 s: kontinuierlicher Kameraflug in die eigenen Haarflammen;
  der Skull richtet sich im Bild im Uhrzeigersinn auf, bis die Augen waagerecht
  liegen. Das Gesicht bleibt frontal zur Kamera.
- Die Kamerabewegung endet ohne Schnitt und ohne separat eingesetzten
  Feuerstreifen so, dass der Schädel unterhalb des Bildes liegt und nur seine
  eigenen weiterbrennenden Flammenspitzen im unteren Fünftel sichtbar bleiben.
- 1,5–2,0 s: kräftiges modernes weißes `OpenR4d10` mittig darüber, unmittelbar
  darunter die gut sichtbare, etwa halbhohe Acrylspiegelung mit Fade nach Schwarz.
- Ebenen von hinten nach vorn: Schwarz, Schrift und Spiegelung mit transparentem
  Hintergrund, animierte Flammen im Vordergrund. Die Flammen werden zuletzt
  komponiert; weder Textkarte noch deren schwarzer Hintergrund dürfen sie
  überdecken. Schwarze Videoflächen sind keine deckenden Vordergrundflächen.
- Runway wurde während dieses Auftrags vom Nutzer verbunden. Der erste echte
  Image-to-Video-Auftrag mit dem unveränderten Masterbild hat die Task-ID
  `253c7126-17dd-43e6-9bb1-19a21ce5d875`. Erst nach Fertigstellung und Sichtprüfung
  dürfen Aussagen zur Ergebnisqualität erfolgen. Der vollständige
  Referenzbild-Prompt bleibt in `OpenR4d10_VIDEO_KI_Prompt_v6.txt` verfügbar.

### 2026-10-30 – Korrekte Logo-Rotation und asymmetrisches Feuer

- Schädel und windstilles, natürlich asymmetrisches Feuer werden zunächst
  aufrecht konstruiert; anschließend wird das gesamte fertige Signet exakt
  45 Grad gegen den Uhrzeigersinn gedreht. Nur die Schädelgrundform darf frontal
  ausgewogen sein; die Flammen dürfen ausdrücklich nicht symmetrisch wirken.

### 2026-10-30 – Vollbreit brennende, nochmals verkürzte Krone

- Die komplette obere Schädelbreite brennt bis zu beiden Außenkanten. Weißer
  Rand, sichtbare Verjüngung und Übergangsbogen sind verboten. Die Flamme ist
  gegenüber dem vorherigen Entwurf etwa halbiert und maximal ungefähr ein
  Zwölftel der Schädelhöhe lang.

### 2026-10-30 – Flammenachse und Farbproportion

- Flammen verlaufen entlang der Schädelmittelachse und exakt rechtwinklig zur
  Augenverbindung, ohne seitliche Windneigung. Blau wird kürzer, der warme
  Anteil bleibt erhalten; die Mitte ist geringfügig länger als die Außenseiten.

### 2026-10-30 – Verbindliche Logo-Mastervorlage

- Die erneut hochgeladene beste Fassung wurde als feste Mastervorlage bestimmt.
  Nur der blaue Übergangsbereich wird etwas kürzer; weder Geometrie noch
  Rotation, Feuerform, Feuerlänge oder warme Farben dürfen verändert werden.

### 2026-10-30 – Finale unveränderliche Masterbasis

- `47858918-75D3-4081-88FF-9EBF55BCBF7C.jpeg` ersetzt alle bisherigen
  Logo-Zwischenstände als einzige Grundlage. Boot-, App- und Webmedien müssen
  sichtbar auf exakt dieser Fassung basieren; kein erneutes Logo-Redesign.

### 2026-10-30 – Animations- und App-Icon-Paket

- Aus der verbindlichen Logo-Mastervorlage entsteht ein nahtloser, flüssiger
  Feuerloop: MP4, 1920 × 1920 px, 5 Sekunden.
- Zusätzlich wird eine hochwertige, größenoptimierte GIF-Fassung des
  5-Sekunden-Loops erzeugt.
- Für animierte Oberflächen werden 2-Sekunden-Loops in 512 × 512, 256 × 256 und
  128 × 128 px bereitgestellt.
- Da native iOS-/Android-App-Icons nicht animiert werden, gehört zusätzlich ein
  statisches 1024 × 1024 px App-Icon zum Paket. Die Animation bleibt für
  Splashscreen, Website, Store-Medien und In-App-Branding vorgesehen.

### 2026-10-30 – Native Apps und zweisekündiger Bootscreen

- Native iOS- und Android-Apps sind zusätzlich zur Weboberfläche geplant, aber
  erst nach Aufbau der Hardware und Druck des Gehäuses umzusetzen.
- Der Bootscreen dauert exakt 2,0 Sekunden. Von 0,0 bis 0,5 Sekunden bleibt
  die Kameraposition vor dem Skull statisch; das Gesicht bleibt unverändert,
  während die Haarflammen bereits natürlich brennen und ihre Form verändern.
- Von 0,5 bis 1,5 Sekunden fliegt die Kamera in den brennenden oberen
  Schädelbereich hinein. Es bleibt während des gesamten Übergangs derselbe
  brennende Schädel mit seinen eigenen Haarflammen. Diese Haarflammen müssen
  sichtbar und realistisch animiert sein und werden beim Hineinzoomen zunehmend
  feiner, detailreicher und schärfer, wie bei einem echten Kamera-Makrozoom mit
  durchgehendem 100-Prozent-Fokus. Es dürfen dafür keine zusätzlichen Flammen,
  kein getrenntes Feuerband und keine auf den Bildschirmrand projizierten
  Fremdflammen eingeblendet werden. Der letzte Zoomausschnitt besteht nur aus
  der hochaufgelösten Nahaufnahme genau dieser Schädel-Haarflammen; anschließend
  erscheint der Schriftzug.
- Von 1,5 bis 2,0 Sekunden steht `OpenR4d10` weiß, horizontal und vertikal
  zentriert auf Schwarz. Direkt darunter liegt eine vertikal gespiegelte
  Reflexion wie auf schwarzem Acryl: nur die obere Hälfte der Spiegelung ist
  sichtbar und fadet nach unten vollständig in Schwarz aus.
- Der Schriftzug verwendet eine moderne, kräftige geometrische Sans-Serif in
  Bold/Semibold; die frühere dünne Standardschrift ist verworfen. Die
  Acrylspiegelung muss auf dem realen 240-x-280-Display klar erkennbar sein:
  unmittelbar unter dem Schriftzug, vertikal gespiegelt, etwa halb so hoch,
  am Ansatz deutlich sichtbar und anschließend weich vollständig in Schwarz
  auslaufend. Sie darf weder fehlen noch wie ein zweiter normaler Schriftzug
  wirken.
- Die Spiegelung wird gegenüber dem ersten korrigierten Entwurf nochmals etwas
  stärker ausgeführt: höherer Kontrast direkt an der Acrylkante und geringfügig
  mehr sichtbare Höhe, weiterhin mit vollständigem weichem Fade nach Schwarz.
- Der erste verbindliche Handheld-Entwurf wird nativ in 240 × 280 Pixeln
  ausgegeben; zusätzlich entsteht ein hochauflösender mobiler App-Master.

### 2026-10-30 – Reale Flammenbewegung als Bootscreen-Referenz

- Die zuvor erzeugte reine Mesh-/Bildverformung gilt nicht als akzeptable
  Flammenanimation und darf nicht weiterverwendet werden.
- Das Nutzerreferenzvideo
  `upload/ScreenRecording_10-30-2026 05-01-14_1.mp4` ist für Dynamik,
  Turbulenz, Aufsteigen, Züngeln, Helligkeitswechsel und Auflösen der Flammen
  verbindlich. Bildinhalt aus dem Video darf nicht übernommen werden. Die
  frühere Forderung, dessen aufeinanderfolgende Bilder sichtbar zu verwenden,
  ist durch die spätere ausdrückliche Nutzerkorrektur aufgehoben.
- Das frühere separate Flammenband am unteren Displayrand ist ausdrücklich
  verworfen. Die reale Flammenreferenz dient ausschließlich dazu, die bereits
  im unveränderlichen Masterbild vorhandenen Schädel-Haarflammen zu beleben und
  deren Detailauflösung beim Zoom zu steigern. Position, Silhouette und Ursprung
  bleiben an den Masterflammen gebunden.
- Präzisierung: Bildinhalt, Farben, Textur und Flammenformen aus dem
  Referenzvideo dürfen zu keinem Zeitpunkt sichtbar in den Bootscreen kopiert,
  überblendet oder projiziert werden. Das Video liefert ausschließlich ein
  Bewegungsmodell für die Originalflammen des Skull-Masters. Auch wenn der Zoom
  die Bildschirmränder erreicht, sind dort nur vergrößerte Ausschnitte der
  blau-weiß-orangefarbenen Master-Haarflammen sichtbar.
- Die Haarflammen dürfen nicht lediglich durch Helligkeitsflackern oder eine
  kaum sichtbare Verformung eines Standbildes simuliert werden. Sie bilden eine
  eigenständige hochauflösende, tatsächlich bewegte Flammenebene aus dem
  Masterdesign: Flammenzungen, Außenkonturen, Zwischenräume und Glutbewegung
  verändern sich organisch über die Zeit. Ansatz, Grundsilhouette, Palette und
  Materialwirkung bleiben identisch zum Master (blau direkt am Schädel,
  weiß/gelb im Übergang, orange an den Spitzen). Der Zoom greift progressiv auf
  diese hochauflösende Ebene zu, sodass mit wachsender Vergrößerung mehr feine
  Flammendetails statt größerer Pixel sichtbar werden.
- Während des Hineinflugs richtet sich der anfangs um 45 Grad geneigte Skull
  kameraseitig gerade. Nach dem Zoom bleibt ausschließlich ein Ausschnitt
  derselben animierten Skull-Haarflammen im unteren Fünftel des Displays
  sichtbar. Dieser Bereich ist keine zusätzliche oder fremde Flammenprojektion,
  sondern die kontinuierliche Endposition des Zooms. `OpenR4d10` steht darüber
  auf Schwarz; direkt darunter bleibt die Acrylspiegelung sichtbar.

### 2026-10-30 – Verbindliche Flammen-Farbrichtung

- Blau/Weiß liegt ausschließlich an der Brennstoffquelle beziehungsweise direkt
  an der Schädelkante. Nach außen folgen Weiß, Gelb und Orange; orange-rötliche
  Töne gehören nur an die äußersten Spitzen. Die Rotation des Logos darf diese
  relative Farbrichtung niemals umkehren.

### 2026-10-30 – Name und Logo-Grundform

- Öffentliche Marke auf `OpenR4d10`, Logoform `OPENR4D10` und Aussprache
  „Open Radio“ festgelegt; der damals noch vorgesehene interne Technikname
  `openplayer` wurde später zugunsten des einheitlichen Namens `openr4d10`
  aufgegeben.
- Logo als freundlicher weißer 45-Grad-Schädel ohne Unterkiefer mit exakt fünf
  farbigen Flammen auf Schwarz definiert.

### 2026-10-30 – Community, Dienst-Store, Backups und Modulisolation

- Git-basierte Community-Übersetzungen mit Pull/Merge-Request-Workflow und
  automatischer Validierung festgelegt.
- Klar gekennzeichnete, datensparsame Projektwebsite-Besucherkarte und
  Seitenaufrufzähler ohne heimliches Tracking definiert.
- Discord als fester Dienst mit PTT und geplanten Länder-/Sprachkanälen
  ergänzt; Mumble- und Discord-Credentials auf lokale Secrets begrenzt.
- Portables Backupformat einschließlich Dienst-Nachinstallationsplan
  festgelegt.
- Git-basierter Dienst-Store als eigener Menüpunkt ergänzt.
- Harte Modulisolation gegen Zugriff auf Raspberry-Pi- und fremde
  Dienst-Credentials verbindlich gemacht.

### 2026-10-30 – Tokens, Aktivierungsregister, Spenden und Sprachen

- Eigene Tokens pro Benutzer mit dienstspezifischer Anleitung und lokalem
  Secret-Speicher festgelegt; Roberts Tokens dürfen nie ausgeliefert werden.
- Freiwilliges, widerrufbares Aktivierungsregister mit grober Karte und
  separater GPS-Einwilligung definiert.
- Letzten Menüpunkt „Informationen & Support“ mit konfigurierbarem PayPal-QR
  ergänzt.
- Englisch als Hauptsprache und funktionsgerechte Übersetzungsdatenbank
  festgelegt.
- English, Deutsch, Polski, Français und Español als vollständig kuratierte
  Startsprachen definiert.

### 2026-10-30 – Veröffentlichung und Installer

- Öffentliche, nichtkommerzielle Veröffentlichung mit zwingender Namensnennung
  festgelegt.
- Lizenztrennung für Software und Design-/CAD-Dateien festgelegt.
- Verbindlicher Schutz vor Veröffentlichung jeglicher Credentials ergänzt.
- Einzeiler-Installer für das geplante GitHub-Repository festgelegt.

### 2026-10-30 – Initiale Konsolidierung

- Sämtliche bisher bekannten Projektziele, Hardwareteile, Bedienregeln,
  Displayvorgaben, Gehäusevorgaben, Dienstideen, Datenbankregeln,
  Webfunktionen, WLAN-Fallback, Bluetooth-Tastatur, Audio-Fallback,
  Spracheingabe, RSS, Telegram und Mediatheken in einer verbindlichen
  Masteranweisung zusammengeführt.
- Regel eingeführt, dass jede neue Erkenntnis vor weiterer Arbeit in dieser
  Datei dokumentiert werden muss.
