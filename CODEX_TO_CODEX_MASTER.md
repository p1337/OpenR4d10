# Codex-zu-Codex-Masteranweisung – OpenR4d10

## 0. Zwingende Startregel

**Diese Datei muss von jeder Codex-Instanz vollständig gelesen werden, bevor
irgendeine Analyse, Konstruktion, Programmierung, Kaufempfehlung, Änderung,
Simulation oder Antwort zum OpenR4d10-Projekt erfolgt.**

Diese Datei ist die zentrale, fortlaufend gepflegte Projektwahrheit.

### Harte globale Display-Lesbarkeitsregel

Die aktuelle Batterie-Prozentanzeige verwendet im nativen 240-x-280-Renderer
`_font(9, bold=True)`. **Neun Pixel TrueType-Schriftgröße ist deshalb ab sofort
die absolute Mindestgröße jedes sichtbaren Textes auf dem physischen Display.**
Kein Dienst, Plugin, Menü, Hinweis, Status, Credit, Kürzel oder dynamischer Text
darf mit `_font(8)`, `_font(7)` oder kleiner gerendert werden. Der gemeinsame
Font-Loader erzwingt mindestens 9 Pixel auch für zukünftige Module. Wichtige
Hinweise und Aktionen müssen größer als dieses Minimum sein; bloßes Abschneiden
oder Verkleinern unter 9 Pixel ist keine zulässige Layoutlösung. Jeder Release
mit Displayänderungen muss automatisiert prüfen, dass kein gezeichneter Text
unter dieser Batterie-Referenzgröße liegt, und die echte 240-x-280-Ausgabe
zusätzlich visuell kontrollieren.

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

Die ausgewählte Geräteansicht und der tatsächlich laufende Audioplayer sind
zwei getrennte Zustände. Das Drehen des Dienstreglers navigiert ausschließlich
zwischen Diensten und darf einen laufenden Stream weder stoppen noch den
angezeigten Dienst beim nächsten Statusrefresh zurücksetzen. Der zuletzt
gestartete Audiodienst spielt im Hintergrund weiter, bis der Benutzer in einem
anderen audiofähigen Dienst ausdrücklich Play auslöst; erst dieser Play-Befehl
ersetzt die bisherige Audioquelle. Informations- und Bilddienste wie Wetter
besitzen den Player nicht und verändern laufende Musik weder beim Öffnen noch
beim Kanalwechsel oder Aktualisieren.

Nach einem Kaltstart beginnt die lokale Wiedergabelautstärke verbindlich bei
30 Prozent. Ein zufälliger, aus einer früheren Sitzung stammender oder technisch
abgeleiteter Wert wie 36 Prozent darf nicht als Startwert erscheinen. Die
zuletzt geöffnete sinnvolle Dienstansicht darf wiederhergestellt werden, sofern
der Dienst weiterhin aktiviert und verfügbar ist. Andernfalls wird die erste
aktivierte nutzbare Dienstansicht gewählt; `SYSTEM` ist kein automatischer
Medien-Fallback. System-, Einstellungs- und Diagnoseansichten sind keine
Audioquellen und zeigen daher weder Senderbild noch Play-/Pause-Schaltfläche.

Bis die Encoder verfügbar sind, bildet die Weboberfläche dieselben logischen
Eingaben zusätzlich auf eine PC-Tastatur ab:

- `W`/`S`: linker äußerer Encoder (Lautstärke höher/niedriger),
- `A`/`D`: linker innerer Encoder (Squelch niedriger/höher),
- Pfeil hoch/runter: rechter äußerer Encoder (vorheriger/nächster Kanal),
- Pfeil links/rechts: rechter innerer Encoder (Dienst zurück/vor),
- Leertaste: linker Drucktaster,
- Enter: rechter Drucktaster,
- Backspace halten: PTT aktiv; Loslassen beendet PTT. In Text-, Auswahl- und
  anderen bearbeitbaren Feldern bleibt Backspace ausschließlich die normale
  Löschtaste und löst niemals PTT oder Zurück aus.

Die Browser-Pfeiltastatur folgt überall der sichtbaren Richtung: Pfeil hoch
sendet auf dem gemeinsamen `right_outer`-Eingabepfad einen negativen Schritt
und wählt den vorherigen beziehungsweise oberen Eintrag, Pfeil runter sendet
einen positiven Schritt und wählt den nächsten beziehungsweise unteren
Eintrag. Eine zusätzliche kontextabhängige Umkehr im geöffneten Gerätemenü ist
verboten. Browser und späterer Encoder verwenden weiterhin denselben logischen
Eingabepfad; die Browserzuordnung bleibt lediglich eine Eingabeabbildung.

Die Tastatursteuerung ist in Text- und Auswahlfeldern inaktiv, damit Eingaben
nicht versehentlich Gerätesteuerungen oder PTT auslösen. In jedem geöffneten
Gerätemenü ist ein aktiver PTT-Druck die Zurück-Funktion und schließt zunächst
die aktuelle Menüebene. Nur wenn der gerade aktive Dienst PTT tatsächlich als
bereite Funktion beansprucht, bleibt der Druck beim Dienst und darf nicht als
Zurück interpretiert werden. Ohne einen solchen berechtigten PTT-Kontext darf
die Oberfläche weder aktives PTT noch eine funktionierende Audioübertragung
vortäuschen.

Die Druckfunktionen werden im oberen Displaybereich vertikal angezeigt:

- links grau: **MENÜ**,
- rechts grau: **PLAY** beziehungsweise die kontextabhängige Kurzfunktion.

Die vier oberen Funktionsfelder verwenden in der normalen Hauptansicht die
kompakten Bezeichnungen **VOL**, **SQL**, **CH** und **SRV**. Diese Kürzel sind
keine fest eingebrannten englischen Texte: jede kuratierte Oberflächensprache
liefert korrespondierende, auf höchstens drei Zeichen begrenzte Kurzformen.
Schrift und Werte werden gegenüber der bisherigen Fassung deutlich größer,
die Höhe der einzelnen Felder gleichzeitig etwas kleiner. In Untermenüs dürfen
die Achsen kontextabhängig anders belegt werden; die Felder müssen dies sofort
anzeigen.

Auf dem physischen 240-x-280-Display gilt die am Dateianfang festgelegte harte
Lesbarkeitsgrenze von mindestens 9 Pixel TrueType-Schriftgröße für ausnahmslos
jeden sichtbaren Text. Wichtige Werte wie der Batterie-Prozentwert werden
mindestens in dieser Größe und fett gesetzt. Mikroschrift nur zum Unterbringen
zusätzlicher Daten ist ausdrücklich unzulässig.

Die Uhr bleibt geometrisch auf der gesamten 240-Pixel-Breite zentriert und
darf nicht von der Breite der WLAN- oder Batterieanzeige verschoben werden.
Funktionskopf und Statuszeile werden so flach wie lesbar ausgeführt; auch der
Abstand zwischen Statuszeile und Diensttitel wird minimiert. Die dadurch
gewonnene Höhe gehört vollständig dem eigentlichen Menü-, Wetter- oder
Medieninhalt.

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
- Uhrzeit deutlich größer; das Datum wird nicht angezeigt,
- Batteriestand rechts; sobald die verifizierte PiSugar-3-Telemetrie aktiv ist,
  steht der ganzzahlige Prozentwert unmittelbar links neben dem Batteriesymbol.

Medien-/Dienstbereich:

- dienstabhängige Hauptinformationen,
- Sendername beziehungsweise Titel und Visualisierung,
- kein redundanter Dienstname über dem Radiosender,
- kein ausgeschriebener Playerzustand wie `PAUSED:`,
- großer interner Play-/Pause-Button rechts oben unter der Batterie,
- größeres Senderbild beziehungsweise Logo und größere Überschrift durch den
  frei gewordenen Raum,
- **keine künstliche Medien-Fortschrittsanzeige bei Live-Streams**,
- keine dauerhaft sichtbare Meldung „REC bereit“,
- kein permanenter Hinweis „Play halten Quick-Menü“.

Die bisherige untere Leiste mit `READY` links und `OpenR4d10` rechts entfällt
vollständig. Sie darf weder Text noch Ersatzstatus enthalten.

Wenn das lokalisierte Hauptmenü (`MAIN MENU`, `HAUPTMENÜ` beziehungsweise die
korrespondierende Übersetzung) geöffnet ist, wird der komplette Player- und
Medienbereich ausgeblendet. Direkt unter der großen, gut lesbaren Überschrift
stehen die zehn in Abschnitt 6 festgelegten Hauptbereiche untereinander. Der
rechte äußere Kanal-/Eintragsregler verschiebt die sichtbare Markierung und
scrollt die Liste; ein kurzer Druck auf den rechten Encoder beziehungsweise
Enter öffnet den markierten Bereich. Senderbild, Titel, Dienstname,
Playerstatus und Play/Pause-Schaltfläche sind dort nicht sichtbar.

In Menüs sitzt unterhalb der Batterie ein nach links gerichteter Pfeil in der
aktiven Akzentfarbe als sichtbarer Hinweis auf die PTT-Zurück-Funktion. Wird
PTT von einem tatsächlich bereiten Dienst verwendet und gerade gehalten,
ersetzt ihn ein rotes Feld mit weißem `PTT`: rechts bündig am Displayrand,
rechts eckig und links abgerundet. Außerhalb eines echten PTT-Kontexts wird
dieses rote Feld niemals angezeigt.

Der normale Zurück-Hinweis verwendet ein kleines, gefülltes Pfeil-Icon statt
aus einzelnen Linien zusammengesetzter Striche. Pfeil und Akzentrahmen bilden
gemeinsam ein rechts angedocktes PTT-Tastenfeld: links abgerundet, oben und
unten gerahmt, ohne sichtbaren rechten Rand und rechnerisch über den rechten
Displayrand hinauslaufend. Das rote aktive PTT-Feld verwendet dieselbe
Silhouette. Die orange linke Akzentlinie bleibt im Menü klar und scharf; im
normalen Player erhält sie einen deutlich sichtbaren, kräftigen weichen Glow.

Wegen der real abgerundeten Displayecken werden beide vertikalen
Drucktasterbeschriftungen im oberen Funktionskopf einige Pixel nach unten
versetzt. Die rechte Beschriftung wird gegenüber der bisherigen Fassung um
180 Grad gedreht, sodass die Randtexte einheitlich von unten beziehungsweise
von der rechten Geräteseite lesbar bleiben.

Der Funktionskopf muss optisch eindeutig vom Medienbereich getrennt bleiben.

## 6. Einstellungsmenü auf dem Gerät

Die Geräteeinstellungen enthalten genau diese Hauptbereiche:

1. **Display**
   - Displayhelligkeit von 0 bis 100 Prozent,
   - Änderungen werden sofort auf dem realen Whisplay sichtbar,
   - der Wert wird als nicht geheime UI-Einstellung dauerhaft in SQLite
     gespeichert und nach Dienst- oder Geräteneustart wieder angewendet,
   - die Raspberry-Pi-Zero-2-W-Umsetzung behält das verifizierte aktive-low
     Backlight BCM22, verlagert sämtliche PWM-Flanken aber in den
     Kernel-`pwm-gpio`-HRTimer. Die Anwendung übergibt ausschließlich einen
     atomaren, begrenzten Prozentwert an den festen Root-Helfer. Weder Python
     noch `lgpio` takten die Helligkeit, und kein neuer Pin wird erfunden.
2. **Akzentfarbe**
   - normaler Menüeintrag wie alle anderen,
   - öffnet beim Anwählen eine eigene Farbauswahl,
   - Farbton, Sättigung, Helligkeit und Preset werden mit den vier Drehachsen
     bedient,
   - Live-Vorschau der Akzentfarbe.
   - Standard ist das festgelegte warme Orange `#FDB813`; ein Marken- oder
     Quellenname erscheint weder in der Geräte- noch in der Weboberfläche.
   - Der normale Player hat dauerhaft einen weichen Akzent-Glow entlang der
     Displaykontur. Es gibt
     dafür keinen Schalter und keine feste Linie. Der Glow entsteht an der
     äußeren realen R5-Kontur und leuchtet nur weich nach innen; dadurch folgt
     er den abgerundeten Ecken, ohne dort abgeschnitten zu wirken. Unter der
     Uhr-/Statusleiste schließt eine gerade, ebenfalls ausschließlich weich
     leuchtende obere Kante den Playerbereich.
     Menümarkierung, PTT-Hinweis und funktionale Statusfarben bleiben davon
     unberührt.
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
   - nicht wörtlich, sondern funktions- und kontextgerecht übersetzen,
   - die Webauswahl ändert und persistiert dieselbe Gerätesprache; der Browser
     folgt dieser Auswahl ebenfalls. Die Sprache des physischen Whisplay hat
     dabei Vorrang vor einer rein lokalen Browserpräferenz.
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

Der Fallback-Hotspot wird vom bereits vorhandenen NetworkManager auf dem
festen Interface `wlan0` bereitgestellt; ein zweiter Netzwerk- oder DHCP-Stack
ist verboten. Nach einer Karenzzeit für gespeicherte Clientprofile startet ein
WPA2-geschützter Hotspot mit einer gerätespezifischen SSID. Das zufällig lokal
erzeugte Hotspotkennwort liegt ausschließlich in einer Secret-Datei mit Modus
0600 und im root-only NetworkManager-Profil. Das physische Display zeigt im
aktiven Einrichtungsmodus SSID, Kennwort und `http://10.42.0.1/`; öffentliche
JSON-Statusdaten, SQLite, Backups, Logs und Git enthalten das Kennwort niemals.
Der Hotspot bleibt stabil aktiv, bis eine neue Clientverbindung erfolgreich
hergestellt oder das Gerät neu gestartet wird; ein kurz instabiles WLAN darf
keinen ständigen Wechsel zwischen Client und Access Point auslösen.

Neben dem WLAN-Symbol steht immer die tatsächlich aktive SSID des
NetworkManager-Profils. Der generische Platzhalter `WLAN` ist an dieser Stelle
unzulässig. Ohne aktive Verbindung wird ehrlich `OFFLINE` angezeigt; im
Fallbackbetrieb ist die gerätespezifische Setup-SSID sichtbar.

Der Hotspot darf später auch manuell aktiviert werden.

Die lokale Weboberfläche erhält zusätzlich eine ausdrücklich zu bestätigende
WLAN-Reparatur. Sie nimmt SSID und Kennwort nur für diesen Vorgang entgegen,
speichert beides weder in SQLite noch im Status, in Backups oder Logs und
übergibt sie über eine kurzlebige Datei an einen festen root-eigenen
NetworkManager-Helfer. Auf dem bestätigten Debian-13-Zielsystem ist
NetworkManager mit `nmcli` der aktive Netzwerkbesitzer; es wird kein zweiter
`wpa_supplicant`- oder Netplan-Schreibpfad erfunden. Der Reparaturmodus legt
zuerst ein neues Profil an und aktiviert es. Erst nach erfolgreicher Verbindung
werden auf ausdrücklichen Wunsch die bisherigen WLAN-Profile ersetzt. Bei
falschen Zugangsdaten bleibt das vorherige Profil erhalten, soweit
NetworkManager es wieder aktivieren kann. Das Kennwort darf weder in einer
Prozessargumentliste noch in einer öffentlichen Antwort auftauchen. Wegen der
zunächst lokalen HTTP-Oberfläche muss die Eingabemaske deutlich darauf
hinweisen, diese Funktion nur im vertrauenswürdigen eigenen LAN zu verwenden.

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

**Globale Begriffsfestlegung:** Wenn Robert `PTT` sagt, meint er immer den
separaten physischen Whisplay-Hardwaretaster auf BCM17. Backspace ist nur die
Browser-Simulation genau dieses Tasters. Weder ein Encoder-Druck noch eine
gezeichnete Displayfläche darf als PTT bezeichnet oder behandelt werden.
Diese Definition ist in jeder späteren PTT-Anforderung mitzulesen.

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

Auch die heute noch im Core zusammengefassten eingebauten Dienste werden in
einer kontrollierten Architektur-Migration zu eigenständigen, im Git sichtbaren
Modulverzeichnissen überführt. **Jeder einzelne Dienst** erhält mindestens ein
eigenes Manifest, einen klaren Einstiegspunkt, Tests und eine eigene vollständige
`README.md` mit Zweck, Bedienung, Datenhaltung, Berechtigungen, Abhängigkeiten,
Sicherheitsgrenze und Diagnose. Die Migration darf keine zweite parallele
Implementierung erzeugen: zuerst werden bestehende Codepfade, APIs und Speicher-
verträge erfasst, dann wird ein Dienst nach dem anderen unter unverändertem
Core-Broker-Vertrag herausgelöst und durch Regressionstests abgesichert.

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
- Wetter als nativer Informationsdienst. Die Grundausstattung besteht aus drei
  sortierbaren Kanälen: Deutschland zeigt primär den offiziellen
  DWD-Regenradarfilm
  `https://www.wettergefahren.de/DWD/wetter/radar/Radarfilm_WEB_DL.gif` und
  zusätzlich weiterhin die METEOSAT-Satellitenbilder für Deutschland; der
  dritte Kanal zeigt METEOSAT für Europa. Beide Satellitenkanäle verwenden den
  offiziellen DWD-WMS-Layer
  `Satellite_meteosat_1km_euat_rgb_day_hrv_and_night_ir108_3h`. Die
  Quellenangabe nennt beim Radar DWD und beim Satellitenbild DWD / EUMETSAT.
  Beide Quellen werden höchstens alle fünf Minuten abgerufen. GIF- und
  WMS-Bilder werden begrenzt geladen, dekodiert und als lokale Einzel-JPEGs neu
  codiert; bei Netz- oder DWD-Ausfall bleiben sichere Cache-Frames verwendbar,
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
- aktivierte Dienste und deren benutzerdefinierte Priorität/Reihenfolge,
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

### Intelligente Radioaufzeichnung und Musikbibliothek

Die Radioaufnahme arbeitet mit einem begrenzten kontinuierlichen Ringspeicher.
Ein PTT-Druck im aktiven Radiodienst bedeutet ausdrücklich „dieses Lied
behalten“ und übernimmt auch den bereits im Ringspeicher vorhandenen
Liedanfang. Diese Radiobelegung ist keine Sprachübertragung. Zusätzlich kann
der Benutzer einen Daueraufnahmemodus aktivieren: Der Stream wird fortlaufend
zwischengespeichert, in einzelne Lieder zerlegt und erst nach erfolgreicher
Verarbeitung aus dem Rohpuffer entfernt.

Titelgrenzen, Interpret und Titel werden zuerst aus vorhandenen ICY-/Stream-
Metadaten abgeleitet. Senderansagen, Jingles oder kurze Einblendungen innerhalb
einer Aufnahme sind akzeptabel. Fehlende oder widersprüchliche Metadaten dürfen
nicht durch erfundene Angaben ersetzt werden; solche Stücke landen in einem
sichtbaren Prüfbereich. Eine spätere optionale Musikerkennung darf nur über
einen ausdrücklich konfigurierten Adapter erfolgen.

Dauerhaft gespeicherte Musik wird ausschließlich als `Interpret – Lied` nach
Interpret sortiert. Album und Radiosender gehören weder in den sichtbaren
Namen noch in den Dateinamen. Dateisystemnamen werden gegen Pfadtraversierung
und unzulässige Zeichen normalisiert. Dubletten werden vor dem dauerhaften
Speichern anhand normalisierter Metadaten und, soweit lokal verfügbar, eines
Audio-Fingerabdrucks beziehungsweise eines stabilen Inhaltsmerkmals erkannt.
Ein bereits vorhandenes Lied wird nicht erneut in die Bibliothek übernommen.

Der lokale Musikplayer ist bewusst sehr einfach und eigenständig bedienbar,
ohne eine fremde Produktoberfläche nachzubauen. Er bietet mindestens:

- Abspielen/Pause sowie vorheriges und nächstes Lied,
- Favorit setzen und wieder entfernen,
- `Mein Soundmix`: ausschließlich Favoriten, zufällige Reihenfolge und
  Endlosschleife,
- `Alle Aufnahmen`: normale Reihenfolge, Wiederholen und Shuffle,
- Löschen am Gerät und im Browser mit eindeutiger Bestätigung,
- Coveranzeige, wenn ein anhand von Interpret und Titel verifiziertes Bild
  sicher lokal zwischengespeichert werden kann; andernfalls ein neutrales
  lokales Ersatzbild.

Cover sind Komfortmetadaten und dürfen Aufnahme, Sortierung oder Wiedergabe nie
blockieren. Entfernte Cover werden wie andere fremde Bilder größenbegrenzt,
dekodiert und lokal neu erzeugt; externe Bild-URLs erscheinen nicht im
öffentlichen Status.

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

Sie ist keine endlose Einzelseite. Die großen Funktionsgruppen werden in klar
beschriftete Tabs beziehungsweise gleichwertige getrennte Ansichten gegliedert,
insbesondere Radio, Medien/Feeds, Gerät, System und Dienste. Ein Tabwechsel
verändert keine Wiedergabe und lädt die Anwendung nicht neu.

Der Wetterdienst besitzt einen eigenen Tab. Er spielt den ausgewählten Radar-
oder Satellitenkanal als Endlosschleife aus lokal begrenzt geladenen und neu
codierten Einzelbildern ab. Die drei Standardkanäle werden jeweils nur durch
eine einmalige, markierte Migration angelegt; ihre Reihenfolge und spätere Benutzeränderungen liegen wie die
Radiosender dauerhaft in SQLite und werden durch Updates nicht zurückgesetzt.
Im Dienst-Tab lassen sich alle Dienste aktivieren, deaktivieren und in ihrer
Priorität nach oben oder unten verschieben. Die Reihenfolge ist damit keine
fest verdrahtete Browserdarstellung.

Die Überschriften aller gleichrangigen Web-Tabs dürfen den verfügbaren
Inhaltsraum nicht dominieren. Radio, Wetter, Medien, Gerät, System und Dienste
verwenden deshalb dieselbe kompakte Titelklasse; die frühere isolierte
Verkleinerung nur von `Sender & Wiedergabe` ist aufgehoben.

Die persönliche Radiosenderbibliothek wird im Radio-Tab genau einmal als
platzsparende Liste dargestellt. Diese eine Liste ist gleichzeitig Schnellwahl
und Editor: sie zeigt Senderbild, Namen, Herkunft/Genre sowie Abspielen,
Verschieben und Löschen. Eine zweite Kartenansicht derselben persistenten
Sender ist unzulässig. Der Abspielen-Knopf der verbleibenden Liste verwendet
die gelbe Standard-Akzentfarbe, damit die primäre Aktion sofort erkennbar ist.

Wiederholte Sammlungen der Weboberfläche werden grundsätzlich als kompakte
Listen und nicht als großflächige Kartenraster dargestellt. Das gilt
insbesondere für Dienstmodule, Radiosender, Wetterkanäle und Medien. Einzelne
Statuszusammenfassungen und Bedienflächen sind davon nicht betroffen. Über der
Dienstliste steht ein Suchfeld, das alle vorhandenen Metadaten eines Dienstes
einschließlich Name, Beschreibung, Bereitschaft, Implementierung, Abhängigkeiten
und interner Kennung lokal filtert. Verifizierte, lokal mitgelieferte echte
Logos dürfen angezeigt werden; ohne geprüfte Bildquelle wird ein neutraler
Initialen-Platzhalter verwendet und niemals ein vermeintliches Logo erfunden.

Auf breiten Browserfenstern bleibt rechts oben eine nicht mitscrollende native
240-x-280-Liveansicht sichtbar. Sie zeigt die Pixel desselben Pillow-Renderers,
der das reale Whisplay versorgt, und keine separat nachgebaute Browsergrafik.
Auf kleinen Bildschirmen darf sie zur kollisionsfreien responsiven Ansicht in
den normalen Dokumentfluss wechseln. Die persönliche Senderverwaltung zeigt
für bekannte kuratierte Sender wieder deren vorhandenes lokales Senderbild;
eigene Sender erhalten ausschließlich den bestehenden Initialen-Platzhalter.
Die Liveansicht trägt nur die knappe Bereichsmarke `LIVE DISPLAY`; eine
zusätzliche Überschrift `Geräteansicht` beziehungsweise deren Übersetzung wird
nicht angezeigt.

Im Wetterbild liegt die Quellenangabe nicht über den Bildpixeln. `DWD` beim
Radar beziehungsweise `DWD / EUMETSAT` beim Satellitenkanal steht kompakt
rechts oberhalb der Bildfläche, sodass keine meteorologische Information
verdeckt wird.

Die Browseroberfläche besitzt eine direkt sichtbare Sprachumschaltung für die
fünf kuratierten Startsprachen English, Deutsch, Polski, Français und Español.
Die Auswahl gilt für statische und dynamisch erzeugte Browsertexte, wird als
nicht geheime Geräteeinstellung in SQLite dauerhaft gespeichert und sofort an
den physischen Whisplay-Renderer weitergegeben. Der Browser speichert dieselbe
Auswahl zusätzlich lokal für die frühe Ladephase und fällt bei fehlenden
Schlüsseln sauber auf Englisch zurück. Ohne gespeicherte Geräteauswahl darf
einmalig eine unterstützte Browsersprache übernommen werden; andernfalls ist
Englisch der Standard.

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
Der Root-Helfer ruft den Installer im Webupdatepfad ausdrücklich mit
`--no-reboot` auf, schreibt nach vollständigem Erfolg zuerst den Status
`rebooting` samt Boot-ID und löst erst danach selbst den Neustart aus. Ein beim
Neustart übrig gebliebener älterer `running`-Status mit abweichender Boot-ID
wird ehrlich als unterbrochener Lauf markiert und darf kein weiteres Update
dauerhaft blockieren.

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

### 2026-10-31 – Ambient-Sofortwechsel, Offline-Audio und HoseLine-Zugang

- Innerhalb von AmbientR4D10 spielt jede Kanaländerung die neu gewählte Szene
  unmittelbar ab. Die zuvor getrennte Vorwahl ohne Audioübernahme ist damit
  aufgehoben. Das bloße Öffnen des Dienstes bleibt ohne Audioseiteffekt.
- Die sechs geprüften eingebauten Ogg-Aufnahmen werden nicht bei jedem Play neu
  gestreamt. OpenR4d10 lädt sie im Hintergrund jeweils höchstens einmal in den
  geschützten lokalen Medienbereich, begrenzt die Einzeldatei auf 64 MiB,
  prüft die kuratierte SHA-256-Prüfsumme und veröffentlicht sie erst danach
  atomar als lokale Offline-Datei. Vorhandene gültige Dateien werden bei
  Neustart und Update wiederverwendet; bei noch nicht fertigem Cache bleibt die
  geprüfte öffentliche Quelle als Übergang verfügbar. Die Binärdateien werden
  nicht in jedes GitHub-Release eingebettet.
- Ein realer Pi-Test von 0.10.47 zeigte, dass die erste Fassung ihre
  Cache-Sperre fälschlich während des langsamen Netzdownloads hielt. Dadurch
  konnte Play auf die Hintergrundarbeit warten. Ab 0.10.48 liegt der gesamte
  Download ausdrücklich außerhalb der kurzen Dateisperre: Bedienung und
  URL-Fallback bleiben sofort verfügbar, während die Offline-Datei entsteht.
- Derselbe reale Lauf zeigte bei einer bestehenden Installation
  `Permission denied: /var/lib/openr4d10/media`: ältere, manuell oder als Root
  angelegte Medienverzeichnisse besitzen nicht zwingend den Dienstbenutzer.
  Der Installer stellt ab 0.10.49 deshalb ausschließlich die bekannten
  schreibbaren Laufzeitverzeichnisse `media`, `media/ambient`, `recordings` und
  `cache` mit Besitzer und Gruppe `openr4d10` sowie Modus 0750 her. Inhalte
  werden weder gelöscht noch rekursiv umgeschrieben.
- Robert verlangt echten BrandMeister-Hörempfang nach dem Vorbild der offiziellen
  HoseLine-Seite und übernimmt ausdrücklich die Verantwortung für die direkte
  Browserintegration. Der verifizierte Fallback-Pfad ist
  `https://hose.brandmeister.network/?subscribe=<talkgroup>`; Talkgroups müssen
  numerisch und größer als 90 sein. Die lokale Weboberfläche erhält dafür einen
  eigenen, klar als HoseLine-Empfang gekennzeichneten Bereich, ohne Passwort,
  Benutzer-Token oder nachgebauten angeblichen MP3-Link.
- Die aktuelle offizielle HoseLine-Webanwendung verwendet öffentlich
  `wss://hose.brandmeister.network/spotter/`, MessagePack-Steuernachrichten und
  8-kHz-G.711-µ-law-Audiopakete. OpenR4d10 implementiert diesen belegten Pfad
  deshalb direkt im Webbrowser: bis zu sechs numerische Talkgroups gleichzeitig
  über eine kompakte Quickliste mit Checkboxen und Länderflaggen abonnieren,
  µ-law-Dekodierung über Web Audio und Anzeige von Quelle, Ziel und Talker Alias.
  Sobald eine der abonnierten Gruppen spricht, erhält dieser aktive Ruf die
  sichtbare Priorität; die übrigen Gruppen bleiben abonniert.
  Der offizielle Komplettplayer bleibt als Fallback verlinkt. Diese Integration
  gibt Ton im bedienenden Browser aus; eine Ausgabe über den Whisplay-Lautsprecher
  darf erst nach einem separaten realen Pi-Audiotest behauptet werden. Senden/PTT
  ist ausdrücklich nicht Teil dieser Ausbaustufe.
- Robert stellt ausdrücklich klar, dass Browseraudio nur ein Zusatzweg ist und
  den Hauptzweck nicht erfüllt: BrandMeister muss nativ auf dem Raspberry Pi
  empfangen, über die reale ALSA-Karte `whisplaysound` wiedergegeben und auf dem
  physischen Whisplay bedient und angezeigt werden. Die Geräteansicht zeigt die
  ausgewählte Talkgroup samt Länderflagge sowie bei einem Ruf Ziel-Talkgroup,
  DMR-Quelle und verfügbaren Alias. Mehrere aktivierte Talkgroups bleiben
  gleichzeitig abonniert; der jeweils aktive Ruf erhält Anzeige- und
  Audiopriorität. Die Talkgroup-Liste und ihre Aktivierung sind nicht nur
  Browser-LocalStorage, sondern nicht geheim und updatefest in der bestehenden
  SQLite-Gerätekonfiguration gespeichert. Erst nach einem realen Empfangs- und
  Lautsprechertest auf dem Pi darf dieser native Pfad als funktionsfähig gelten.
- Die Talkgroup-Verwaltung zeigt zusätzlich den vollständigen, durchsuchbaren
  öffentlichen Katalog vom festen offiziellen Endpunkt
  `https://api.brandmeister.network/v2/talkgroup`. Nummer, Name und abgeleitete
  Länderkennung werden begrenzt und lokal zwischengespeichert; eine numerische
  eigene Talkgroup bleibt ergänzend möglich. Das Anhaken legt die Talkgroup in
  der updatefesten Geräte-Quickliste an beziehungsweise aktiviert sie dort.
  Der öffentliche Katalog benötigt keinen Benutzer-API-Schlüssel; persönliche
  Hotspot- oder SelfCare-Konfiguration bleibt ausdrücklich außerhalb dieses
  Receive-only-Pfads.
- BrandMeister muss auch ohne Browser vollständig am Gerät konfigurierbar sein.
  In der DMR-Ansicht blättert die rechte äußere Achse einzeln durch den
  offiziellen Talkgroup-Katalog; die linke innere, dort nicht als Squelch
  benötigte Achse springt pro Rastung 25 Katalogeinträge vor oder zurück. Ein
  PTT-Druck aktiviert beziehungsweise deaktiviert die ausgewählte Talkgroup in
  der persistenten Quickliste; nur die Druckflanke schaltet, die Loslassflanke
  bleibt wirkungslos. Der bisherige kurze rechte Druck bleibt als kompatible
  Zweitbedienung erhalten. Diese PTT-Belegung ist ausschließlich eine lokale
  Listenaktion und sendet weder Sprache noch eine BrandMeister-PTT-Nachricht.
  Linke äußere Achse bleibt Lautstärke, rechte innere Achse bleibt Dienstwahl.
  Der Funktionskopf muss dienstabhängig stets die wirkliche Belegung aller vier
  Achsen anzeigen; in BrandMeister sind deshalb eine lokalisierte
  Sprungfunktion und `TG` statt eines sachlich falschen `SQL`/Kanal-Schemas
  sichtbar.
- Die BrandMeister-Geräteansicht ist keine einzelne TG-Karte und verwendet kein
  dekoratives TG- oder Länderbild. Eine gerade sprechende abonnierte Talkgroup
  darf nicht noch einmal in einer eigenen Kopfzeile dupliziert werden. Stattdessen
  erhält genau ihr normaler Katalogeintrag einen deutlich sichtbaren grünen
  Zeilen-Glow. Der dadurch freigegebene Platz gehört einem sechsten sichtbaren
  Eintrag. Das virtuell scrollbare Fenster des vollständigen offiziellen
  Talkgroup-Katalogs zeigt aktivierte Einträge zuerst, danach alle inaktiven
  Einträge. Markierung, An/Aus-Zustand und Position im Gesamtkatalog müssen ohne
  Browser erkennbar bleiben.
- Am 2026-10-31 bestätigt Robert während eines realen abonnierten HoseLine-Rufs
  hörbaren Ton aus dem montierten Whisplay-Lautsprecher. Damit ist der native
  WebSocket-/MessagePack-/G.711-µ-law-/PCM-/ALSA-Pfad bis zur realen Hardware
  erstmals akustisch bestätigt; Browseraudio bleibt nur der optionale Zusatz.

### 2026-10-31 – Einheitliche Web-Pfeilrichtung und direkt geladene Ambient-Bilder

- Robert korrigiert die Browser-Kanalrichtung: Pfeil hoch muss stets den
  vorherigen beziehungsweise oberen Eintrag wählen, Pfeil runter stets den
  nächsten beziehungsweise unteren. Die bisherige Grundbelegung war außerhalb
  des Menüs vertauscht und wurde im Menü durch eine zweite Umkehr kaschiert.
  Die Grundbelegung lautet nun `ArrowUp = -1`, `ArrowDown = +1`; eine
  Menü-Sonderumkehr entfällt.
- Die sechs kuratierten Ambient-Grafiken werden in der Webliste unmittelbar als
  lokale `<img>`-Inhalte aus den bereits begrenzten
  `/api/ambient-art/<preset>`-Endpunkten geladen. Lazy-Loading darf die direkte
  Sichtbarkeit nach dem Öffnen des Ambient-Tabs nicht verzögern. Fremde
  Bildadressen oder ein zweiter Bildpfad werden nicht eingeführt.

### 2026-10-31 – Reale Ambient-Wiedergabe und Wikimedia-HTTP-Kennung

- Der erste reale AmbientR4D10-Test auf dem Pi zeigt: Wikimedia liefert dem
  unveränderten ffmpeg/mpv-Standardclient HTTP 429, obwohl derselbe öffentliche
  Ogg-Inhalt per Browser beziehungsweise `curl` erreichbar ist. Das ist kein
  ALSA- oder Whisplay-Fehler; die Karte `whisplaysound` ist aktiv.
- Wikimedia akzeptiert die Wiedergabe mit einer eindeutigen, kontaktierbaren
  HTTP-Kennung `OpenR4d10 (+https://github.com/p1337/OpenR4d10)`. Der einzige
  vorhandene `MpvEngine` setzt diese Kennung deshalb zentral. Es entsteht kein
  zweiter Player und kein unbeschränkter Downloadhelfer.
- Die sechs eingebauten Szenen verwenden die stabilen, queryfreien
  `upload.wikimedia.org`-Originaladressen statt der zusätzlichen
  `Special:Redirect`-Stufe. Quellen-, Lizenz- und Urheberseiten bleiben
  unverändert sichtbar. Eigene Szenen durchlaufen weiter die vorhandene
  credential- und queryfreie Medienvalidierung.
- Die reale Wiedergabe muss nach jeder Änderung auf dem Pi gestartet, über den
  öffentlichen Status als aktiver Ambient-Dienst bestätigt und anschließend
  wieder sauber gestoppt werden. Ein bloß grüner Unit-Test genügt hierfür nicht.
- Der zweite reale Test bestätigt die neue HTTP-Kennung im laufenden
  mpv-Prozess, zeigt bei der 20-Minuten-Cafédatei jedoch eine zweite Grenze:
  Das Öffnen benötigt länger als das bisherige Drei-Sekunden-IPC-Fenster. Das
  begrenzte Antwortfenster des einzigen Players wird auf 15 Sekunden erhöht.
  URL-Validierung, Prozessisolation und die übrigen Content-Grenzen bleiben
  unverändert; ein unbegrenztes Warten ist weiterhin verboten.

### 2026-10-31 – Eigener AmbientR4D10-Klanglandschaftsdienst

- Robert legt einen eigenständigen Audiodienst mit dem sichtbaren Namen
  **AmbientR4D10** fest. Er ist weder Webradio noch Teil der normalen
  Musikbibliothek und verwendet keine fremde Marke wie Noisli/Noisly.
- Die erste Szenenauswahl umfasst mindestens Café/Cafeteria, Wald,
  Meer/Strand, Bach beziehungsweise Regen und ein nächtliches Feld mit
  Grillen. Die Bezeichnungen werden in allen fünf kuratierten Gerätesprachen
  sinngemäß übersetzt.
- AmbientR4D10 folgt der vorhandenen Audio-Ownership: Das bloße Öffnen des
  Dienstes verändert laufendes Radio nicht. Das Drehen der Kanalachse innerhalb
  von AmbientR4D10 startet dagegen sofort die neu gewählte Klanglandschaft und
  ersetzt die bisherige Audioquelle; ein zusätzlicher Play-Druck ist nicht
  mehr erforderlich. Danach läuft sie beim Wechsel zu Wetter oder anderen
  visuellen Diensten im Hintergrund endlos weiter, bis Pause, Stopp oder Play
  eines anderen Audiodienstes erfolgt. Diese spätere Bedienentscheidung ersetzt
  die frühere reine Vorwahl beim Durchblättern.
- Szenen sind persistent sortierbar, aktivierbar und erweiterbar. Eigene
  Klangdateien beziehungsweise später geprüfte Downloadpakete werden im
  geschützten Mediendatenbereich gespeichert und durch Updates nicht ersetzt.
  Das Repository enthält keine erfundenen, ungeprüften oder lizenzrechtlich
  unklaren Binärklänge. Jeder mitgelieferte oder automatisch geladene Klang
  benötigt dokumentierte Quelle, Lizenz, Urheberhinweis und Prüfsumme.
- Die Wiedergabe verwendet den vorhandenen isolierten Medienplayer mit echter
  Endlosschleife. Es entsteht weder ein zweiter Audio-Stack noch eine
  dekorative Fake-Wiedergabe. Auf dem Gerät zeigt der Dienst Szenenname,
  verständliches lokales Motiv und Play/Pause; technische Pfade oder
  Prozessmeldungen bleiben verborgen.

### 2026-10-31 – Solix-Energie, freie Kameras, VPN und großer Dienstideen-Katalog

- Robert verlangt zusätzlich zur bisherigen kurzen Kandidatenauswahl eine
  dauerhaft versionierte, priorisierte Liste mit mindestens 50 weiteren
  realistischen Diensten beziehungsweise Geräteprojekten. Sie soll bewusst
  auch Ideen enthalten, die bisher nicht genannt wurden, insbesondere
  Push-to-Talk, weltweite öffentliche Kameras, Netzwerk-/VPN-Funktionen,
  lokale Automatisierung, Energie, Mobilität, Sicherheit und sinnvolle
  standortabhängige Funktionen. Jeder Eintrag benennt Nutzen, vorhandenen
  Integrationsweg, Pi-Zero-2-W-Tauglichkeit, Zugangsdatenbedarf, Datenschutz
  und technische beziehungsweise rechtliche Grenzen; eine Idee gilt dadurch
  noch nicht als implementiert.
- Anker SOLIX wird als konkreter Energiedienst eingeplant. Vor Neuentwicklung
  wird Roberts vorhandenes Cheap-Yellow-Display-/Arduino-Projekt auf diesem
  Rechner gesucht und dessen nachweislich funktionierender Datenweg geprüft.
  Die Geräteansicht soll mindestens aktuelle PV-Erzeugung, Haus-/Verbrauchs-
  leistung, Akku-Ladezustand, Laden/Entladen und Netzfluss darstellen, soweit
  diese Werte die vorhandene Schnittstelle tatsächlich liefert. Login,
  Cookies und Tokens bleiben ausschließlich in einem dienstbezogenen lokalen
  Secret-Speicher, niemals in Git, Core-SQLite, Status, Logs oder Backups. Ein
  inoffizieller Cloudpfad wird sichtbar als solcher gekennzeichnet und darf
  nicht als stabile offizielle Anker-API ausgegeben werden.
- Der Webcam-Dienst wird von zwei festen Snapshot-Slots zu einer persistenten,
  sortierbaren Benutzerbibliothek erweitert. Eigene öffentliche HTTP(S)-
  Quellen können als begrenztes Standbild oder als MJPEG-Stream angelegt,
  getestet, aktiviert und gelöscht werden. Fremde Bytes werden nicht blind
  weitergereicht: Einzelbilder werden dekodiert, dimensions-/größenbegrenzt
  und lokal neu codiert; MJPEG erhält Zeit-, Bildgrößen- und Framerategrenzen.
  Zugangsdaten in URLs sowie private Netzbereiche sind ohne ausdrücklich
  isolierten lokalen Modus verboten.
- Ein VPN-Dienst darf ausschließlich vorhandene, gepflegte Linux-Backends wie
  WireGuard oder NetworkManager-Profile steuern. Schlüssel und Konfigurationen
  bleiben root-only und außerhalb des Core; die UI sieht nur Profilname,
  verbunden/getrennt, sichere Gegenstelle, Tunneladresse und Datenzähler.
  Import, Aktivierung und Abschaltung benötigen einen festen privilegierten
  Helfer statt allgemeiner Shell- oder sudo-Rechte.
- Standortschätzung über sichtbare WLAN-SSIDs/BSSIDs ist nur nach ausdrücklicher
  Einwilligung zulässig. Eine rein lokale Wiedererkennung selbst benannter Orte
  wird gegenüber externen BSSID-Geolocation-Diensten bevorzugt. Rohscans und
  Nachbar-BSSIDs dürfen weder öffentlich ausgegeben noch ungefragt an Dritte
  gesendet werden; GPS oder präziser Standort werden nicht vorgetäuscht.
- Die lokale Suche fand kein Anker-/SOLIX-Projekt und insbesondere keinen
  belastbaren früheren CYD-SOLIX-Datenweg. Der zuletzt von PlatformIO bekannte
  CYD-Pfad ist ein Crypto-Dashboard und wird nicht als SOLIX-Quelle ausgegeben.
- Version 0.10.39 setzt deshalb den ehrlichen ersten SOLIX-Schritt um:
  `anker_solix` ist ein standardmäßig deaktivierter externer Energiedienst,
  erscheint im Dienstkatalog und übernimmt nach einem erfolgreichen isolierten
  Adapter-Handshake ausschließlich die sechs begrenzten öffentlichen Messwerte
  `solar_w`, `home_w`, `grid_w`, `battery_w`, `battery_percent` und
  `energy_today_kwh`. Seriennummern, Site-/Device-IDs und Zugangsdaten bleiben
  ausgeschlossen. Unterstützte Geräte sollen Ankers lokale Modbus-TCP-
  Integration verwenden; ein Community-Cloudadapter bleibt ausdrücklich
  inoffiziell und getrennt.
- `docs/SERVICE_CANDIDATES.md` enthält nun 88 nummerierte Vorschläge in den
  Bereichen Energie/Smart Home, PTT/Kommunikation, Kameras/Weltbilder,
  Netzwerk/VPN, Standort/Mobilität, Sensorik, Medien und Betrieb. Die Liste
  trennt technische Eignung und Voraussetzungen von tatsächlicher
  Implementierung und nennt eine konkrete empfohlene Reihenfolge.

### 2026-10-31 – Verbindliches großes Dienst-Ausbaupaket

- Robert beauftragt die tatsächliche schrittweise Implementierung folgender
  Dienstfamilien: Anker SOLIX, MQTT, privates OpenR4d10-PTT, Mumble,
  SIP-Intercom, Meshtastic über einen vorhandenen LAN-/Bluetooth-/USB-Knoten,
  TeamSpeak, Discord, Telegram/TDLib, ntfy und Gotify; eigene Snapshot-,
  MJPEG-, RTSP- und ONVIF-Kameras einschließlich Windy- und kuratierten
  öffentlichen Welt-/Verkehrs-/Hafen-/Bahnsteigkameras; ISS, NASA EPIC, NOAA
  Space Weather, zulässige Blitzdaten und lokale/Immich-Fotodiashows;
  WireGuard, OpenVPN, Tailscale, ZeroTier und Tor-Clientstatus; DNS-Filter-,
  Uptime-, Metrik-, Wake-on-LAN- und NAS-Status; lokale Ortsprofile und nur
  ausdrücklich bestätigte externe WLAN-Geolokalisierung; amtliche Warnungen;
  OpenSubsonic/Navidrome, Jellyfin Audio, Audiobookshelf, MPD, Snapcast, Music
  Assistant, DLNA/OpenHome, AirPlay, Internet Archive Audio, CalDAV/ICS,
  Nextcloud und eine kleine Offline-Sprachsteuerung.
- Bereits vorhandene Katalogeinträge oder Adapterverträge sind nicht mit einer
  fertigen Integration gleichzusetzen. Zum Zeitpunkt der Beauftragung besitzen
  SOLIX, Private PTT, Mumble, Discord, Telegram und TeamSpeak nur ehrliche
  isolierte Dienstverträge; sie dürfen erst nach realem Adapter-Handshake und
  End-to-End-Test als funktionsfähig erscheinen.
- Meshtastic benötigt weiterhin einen echten Meshtastic-LoRa-Knoten. Der Pi
  Zero 2 W kann diesen offiziell per TCP im LAN (Port 4403), Bluetooth oder USB
  bedienen, wird ohne zusätzliche Funkhardware aber nicht selbst zum
  LoRa-Empfänger.
- Jami ist ein dezentrales verschlüsseltes Kommunikationssystem; ein geeigneter
  headless ARM64-Client ist vor Integration zu verifizieren. Ein
  Jitsi-Audioraum ist eine WebRTC-Konferenz; dessen Audio-/AEC-Last ist auf dem
  Zero 2 W voraussichtlich hoch und bleibt bis zu einem realen Lasttest Klasse
  C. Weder Dienst darf als bloßer Weblink als implementiert gelten.
- ntfy und Gotify sind Push-Nachrichtendienste. ntfy kann per HTTP/SSE/JSON auf
  öffentlichen oder eigenen Topics arbeiten; Gotify benötigt einen eigenen
  Server und einen isoliert gespeicherten Client-/App-Token. Topics, Tokens und
  Serverzugänge bleiben außerhalb von Core-SQLite, Status, Logs und Backups.
- NASA EPIC liefert aktuelle Vollscheibenbilder der Erde von DSCOVR; NOAA Space
  Weather liefert Sonnenwind-, Kp-/Geomagnetik-, Aurora- und Warnprodukte.
  Beide verwenden ausschließlich feste offizielle, begrenzte und gecachte
  Datenquellen. Blitzortung wird nur über eine ausdrücklich erlaubte API oder
  Lizenz umgesetzt; HTML-Scraping ist verboten.
- Tailscale ist ein koordiniertes WireGuard-basiertes Mesh-VPN, ZeroTier ein
  virtuelles Layer-2/Layer-3-Netz. Tor wird höchstens als lokaler Client/SOCKS-
  Status beziehungsweise expliziter Proxy einzelner kompatibler Dienste
  unterstützt; OpenR4d10 wird weder Exit-Relay noch ungefragt vollständig über
  Tor umgeroutet. Schlüssel und Identitäten bleiben in den jeweiligen
  root-eigenen Backends.
- Pi-hole/AdGuard Home, Uptime Kuma, Prometheus und Netdata werden primär als
  Statusquellen vorhandener Instanzen integriert. Prometheus und Netdata sind
  keine Netzwerkscanner. Ein eigener begrenzter LAN-Gerätestatus und
  Wake-on-LAN verwenden feste gespeicherte Ziele statt frei eingebbarer
  Paketziele oder Scans.
- Lokale SSID-Ortsprofile ordnen ausschließlich auf dem Gerät bekannte
  WLAN-Fingerprints Namen wie Zuhause oder Werkstatt zu. Externe
  WLAN-Geolokalisierung überträgt BSSIDs an Dritte, ist deshalb strikt opt-in
  und benötigt eine vom Benutzer gewählte Quelle. Geofencing bedeutet hier
  feste Aktionen beim Betreten/Verlassen eines solchen lokalen Profils; keine
  Position wird erfunden.
- OpenSubsonic/Navidrome, Jellyfin und Audiobookshelf sind Clients für eigene
  Medienserver; MPD steuert einen Music Player Daemon, Snapcast verteilt Audio
  synchron in mehrere Räume, Music Assistant bündelt Musikquellen/Player und
  DLNA/OpenHome entdeckt beziehungsweise steuert LAN-Renderer. Internet
  Archive Audio erschließt frei zugängliche Sammlungen unter Beachtung der
  Objektlizenzen. Immich dient als eigener Fotoarchiv-/Fotorahmen-Server.
- Die Umsetzung erfolgt in überprüfbaren Releases. Ein Modul gilt nur dann als
  fertig, wenn Backend, persistente nicht geheime Konfiguration, isolierter
  Secret-Pfad soweit nötig, Web- und Gerätebedienung, Fehlerzustand,
  Tests, Dokumentation, Installation und Deinstallation zusammen vorhanden
  sind. Bloße Schalter, Links und erfundene Demo-Daten sind verboten.

### 2026-10-31 – Lastabhängiges Restflackern ausschließlich im Akkubetrieb

- Robert korrigiert die bisherige Einstufung des seltenen Restflackerns: Bei
  Zwischenhelligkeiten tritt es im PiSugar-Akkubetrieb erneut und erkennbar
  besonders dann auf, wenn der Raspberry Pi Rechenlast erzeugt. Bei externer
  Stromversorgung bleibt dieselbe Anzeige stabil. Die Helligkeit springt dabei
  nicht nur kurz nach unten, sondern gelegentlich auch nach oben.
- Ein kontrollierter Akkulasttest mit vier Rechenprozessen hielt
  `get_throttled=0x0`, 1 GHz CPU-Takt und normale Temperatur. Damit ist weder
  eine Firmware-Unterspannung noch thermisches Drosseln belegt. Kleine
  Versorgungsschwankungen unterhalb der Pi-Schwelle bleiben ohne Messgerät
  messbar offen, erklären aber das Springen in beide Richtungen schlechter.
- Quellprüfung von `lgpio` zeigt: `tx_pwm` wird trotz C-Implementierung durch
  einen normalen Userspace-Thread mit absoluten Sleeps getaktet. Rechenlast
  kann deshalb sowohl Ein- als auch Ausschaltflanke verspäten. Eine bloße neue
  Frequenz wäre kein belastbarer Fix.
- OpenR4d10 verwendet ab 0.10.38 deshalb den auf dem Zielkernel vorhandenen
  `pwm-gpio`-Treiber auf BCM22. Dessen HRTimer erzeugt die 1-kHz-Flanken im
  Kernel. Ein fester Root-Helfer prüft nur atomare Werte von 0 bis 100 aus
  `/run/openr4d10-backlight`; die Anwendung erhält keinen Sysfs-Schreibzugriff.
- Der Boot-Handoff ist angepasst: Der Kernel besitzt BCM22 durchgehend, die
  frühe Initialisierung hält das aktive-low Backlight zunächst aus, der native
  Player besitzt nur Reset/DC und schaltet erst nach seinem ersten vollständigen
  Frame über denselben begrenzten Request auf 100 Prozent. Danach stellt die
  Anwendung den persistenten SQLite-Wert wieder her. Der neue Overlay-Zustand
  benötigt den ohnehin automatischen Neustart des Installers.

### 2026-10-31 – Mehrsprachiger Radiokatalog und abonnierbarer Podcast-Dienst

- Die unveränderliche, vorinstallierte Radioauswahl wird zu einem kuratierten
  Katalog mit mindestens fünf verifizierten Sendern je Hauptsprache erweitert.
  Startumfang: Deutsch, Englisch, Polnisch, Französisch, Spanisch, Italienisch,
  Niederländisch und Portugiesisch. Jeder Eintrag besitzt Sprache, Land,
  Kategorien, geprüfte öffentliche Streamquelle, Homepage und ein geprüftes
  Logo. Technische oder wissenschaftliche Inhalte sind als eigene Kategorie
  auffindbar. Nicht verifizierte Adressen oder erfundene Logos sind verboten.
- Die bisherige persönliche Liste mit zehn Sendern bleibt bei Neuinstallation
  aktiv. Alle neu hinzukommenden Katalogsender sind zunächst deaktiviert und
  werden durch Updates niemals ungefragt in eine bestehende persönliche Liste
  kopiert. Der aktive Bereich steht im Web oben, der deaktivierte Katalog
  darunter. Aktivieren kopiert einen Katalogeintrag in die persistente
  persönliche SQLite-Liste und verschiebt ihn damit nach oben; Deaktivieren
  entfernt nur die persönliche Zuordnung, nicht den Katalogeintrag.
- Suche, Sprachfilter und Kategorienfilter arbeiten über Namen, Sprache, Land,
  Kategorien und redaktionelle Beschreibung. Die persönliche Reihenfolge bleibt
  unabhängig davon persistent. Senderlogos werden weiterhin ausschließlich
  über den vorhandenen begrenzten Download-, Prüf- und lokalen
  Re-Encoding-Pfad ausgeliefert; fremde Bild-URLs erscheinen nicht im Browser.
- Podcasts werden als echter lokaler Dienst ergänzt, nicht als bloßer Link zum
  vorhandenen RSS-Textleser. Nutzer können öffentliche RSS-/Atom-Podcastfeeds
  abonnieren, aktualisieren, durchsuchen, Episoden abspielen und Abonnements
  wieder entfernen. Abonnements bleiben in SQLite erhalten; Episodenlisten
  werden begrenzt aus dem Feed gelesen. Audio-Enclosures laufen über den
  vorhandenen mpv-Player und übernehmen bei explizitem Play die Audioquelle.
- Feed- und Enclosure-URLs müssen HTTP(S), öffentlich und ohne eingebettete
  Zugangsdaten sein. Es werden weder Tokens noch private Feed-Adressen aus Git
  geladen oder in öffentliche Statusdaten geschrieben. Downloads, XML-Größe,
  Episodenzahl, Zeitüberschreitung und Bildverarbeitung bleiben begrenzt.

### 2026-10-31 – Symmetrischer Funktionskopf und Glow-Faktor 1,3

- Der zweizeilige Funktionskopf wird als gespiegeltes Raster aufgeräumt. Links
  stehen weiterhin Bezeichnung und Wert (`LAU 30%`, `SQL 5`). Rechts stehen
  Wert und Bezeichnung (`001 KAN`, `RADIO DST`), sodass alle Werte zur
  Displaymitte und alle Bezeichnungen zu den äußeren Bedienseiten orientiert
  sind.
- Zeilenhöhe, sichtbare Glyphenoberkante, Innenabstand zum Mittelsteg und
  Außenabstand werden aus gemeinsamen Layoutkonstanten erzeugt und getestet.
- Die Alpha-Intensität des vorhandenen permanenten Player-Glows wird mit Faktor
  `1,3` verstärkt. Form, weicher Verlauf, fehlende harte Linie und die gezielte
  Abschwächung der unteren Eckbereiche bleiben erhalten.

### 2026-10-31 – Kopfzeilenkürzel und Werte exakt ausgerichtet

- Die lokalisierten Kürzel `LAU`, `SQL`, `KAN`, `DST` beziehungsweise ihre
  Sprachvarianten und die zugehörigen gelben Werte beginnen innerhalb jeder
  Zeile auf exakt derselben sichtbaren Glyphenhöhe. Die Ausrichtung verwendet
  die tatsächlichen Font-Bounding-Boxen statt eines geratenen festen
  Zwei-Pixel-Versatzes und wird für beide Kopfzeilen getestet.

### 2026-10-31 – Play/Pause-Kreis bündig in der Player-Ecke

- Der runde Play/Pause-Bedienknopf erhält im normalen Player denselben Abstand
  zur oberen und zur rechten Playerkante. Kreis und inneres Play-/Pause-Symbol
  werden gemeinsam nach rechts verschoben; Größe, Metadatenhöhe und
  Touch-/Encoderfunktion bleiben unverändert.

### 2026-10-31 – Reale PWM-Nachprüfung und geplanter LED-Messversuch

- Die 60-Prozent-Helligkeit ist nach dem PWM-Caching im normalen Betrieb
  weitgehend stabil. Ein einzelnes kurzes Flackern wurde im Batteriebetrieb
  vermutlich während höherer Rechenlast beobachtet; Robert bewertet diese
  sehr seltene Resterscheinung aktuell als akzeptabel. Die Korrektur wird daher
  als deutlich wirksam, aber nicht als physikalisch absolut flackerfrei
  dokumentiert.
- Ein beaufsichtigter Messversuch mit ausgeschalteter RGB-LED, wechselndem
  Umgebungslicht und Abdecken per Hand ist für später vorgesehen. Ein Raspberry
  Pi kann am Digital-GPIO keinen Widerstand direkt messen. Denkbar wäre nur eine
  zeitbasierte Photodioden-/Kapazitätsmessung nach vorheriger Verifikation von
  Schaltung, GPIO-Richtung, gemeinsamer LED-Elektrode, Vorwiderstand und sicheren
  Pegeln. Vor dieser Prüfung wird kein Pin rückwärts oder gegen einen Ausgang
  getrieben.

### 2026-10-31 – Glow-Eckbalance, Randbeschriftung und Dienstkandidaten

- Das reale Vorschaubild bestätigt den kräftigen Player-Glow und seinen
  gewünschten 3D-Eindruck. Nur die Lichtkonzentration in den beiden unteren
  Rundungen wird reduziert; gerade Seiten, Unterkante und obere Glowkante
  behalten ihre deutlich sichtbare Intensität.
- Die gedrehten Randbeschriftungen `MENÜ` und `PLAY` werden einige weitere
  Pixel nach innen gerückt, damit sie innerhalb der realen Rundung sicher
  lesbar bleiben.
- Weitere mögliche Anwendungen werden in einer priorisierten, unverbindlichen
  Dienstkandidatenliste dokumentiert. Für jeden Kandidaten sind Nutzen,
  vorhandener offizieller Integrationsweg, Pi-Zero-2-W-Tauglichkeit,
  Zugangsdatenbedarf und wesentliche rechtliche beziehungsweise technische
  Grenzen sichtbar. Die Liste installiert oder aktiviert noch keinen Dienst.

### 2026-10-31 – Radio-Metadaten vor Play und pixelgenaue Medienfläche

- In der Radioansicht werden Interpret und Titel nach Möglichkeit schon vor
  dem Start der hörbaren Wiedergabe ermittelt. Dafür wird der bereits
  vorhandene ICY-Ringspeicher beim Öffnen der Radioansicht auf den sichtbaren
  Sender abgestimmt; er liefert Metadaten und den gewünschten Vorlauf, ohne
  Audio an den Lautsprecher auszugeben. Es entsteht kein paralleler zweiter
  Metadatenadapter.
- Wenn ein Sender keine ICY-Titelinformation liefert, zeigt das Gerät einen
  kurzen lokalisierten Endnutzertext. Technische Player-, ALSA-, `aplay`- oder
  Backendmeldungen dürfen in dieser Zeile nicht erscheinen.
- Der reale SWR3-Stream liefert ICY aktuell als `Titel / Interpret`. Dieses
  belegte Format wird beim Einlesen in die einheitliche Anzeige und Ablage
  `Interpret – Titel` gedreht; unbekannte Formate bleiben unverändert statt
  geraten zu werden.
- Die gemeinsame Medienmaske für Senderlogos, Wetter-, Kamera- und andere
  Medienflächen erhält oben kleine Radien und unten weiterhin die große reale
  Displayrundung. So wirkt nur die Unterkante durch das runde Display
  beschnitten.
- Seiten- und Unterabstand der Medienfläche sind identisch und werden auf das
  für die reale Rundung nötige Minimum reduziert. Logos nutzen dadurch mehr
  Breite; Einzelimplementierungen pro Sender oder Dienst sind nicht zulässig.

### 2026-10-31 – Player-Rahmen-Glow deutlich verstärkt

- Die reale Anzeige zeigt, dass der bisherige permanente Player-Glow trotz
  korrekter Kontur kaum wahrnehmbar ist. Er wird deshalb deutlich leuchtender
  und klar sichtbar ausgeführt.
- Die bestehende Form bleibt unverändert: geschlossene Kontur entlang der real
  abgerundeten Displaykante und gerader oberer Glow unter der Statusleiste.
  Weiterhin gibt es weder eine harte Akzentlinie noch einen Abschalter.
- Der Effekt besteht aus einem breiten weichen Lichtschein und einem engeren,
  kräftigeren Lichtschein. Ein Regressionstest fordert eine messbare
  Mindesthelligkeit an Seiten-, Ober- und Unterkante, ohne reine
  Akzentfarbpixel zuzulassen.

### 2026-10-31 – Gerätesprache, verbleibendes Flackern und Lichtsensor-Prüfung

- Die Sprachwahl im Web darf nicht nur den Browser übersetzen. Sie setzt und
  persistiert primär die Sprache des physischen Geräts und synchronisiert den
  Browser damit. Die bestehende gegenteilige Festlegung ist aufgehoben. Auch
  feste Hilfs-, Bereitschafts- und Playertexte im Geräteinhalt werden durch den
  kuratierten Gerätekatalog übersetzt; nur echte Sender-, Titel- und
  Inhaltsmetadaten bleiben unverändert.
- Der reale Stack flackert bei Zwischenhelligkeiten trotz `lgpio` seltener
  weiter. Codeprüfung identifiziert das erneute Starten derselben PWM-Welle nach
  jedem UI-Frame als konkrete Ursache; `_LgpioPwm` merkt sich deshalb den
  Tastgrad und ändert die laufende Welle nur bei einer echten Wertänderung. Der
  vorhandene Kernel-`pwm-gpio`-Treiber wird nicht parallel per Boot-Overlay
  aktiviert, weil er BCM22 vor dem nativen Bootplayer beanspruchen würde.
  **Historischer Stand bis 0.10.37:** Der oben dokumentierte 0.10.38-Handoff
  löst genau diesen Eigentümerkonflikt und ersetzt diese Zwischenlösung.
- Eine LED kann wissenschaftlich als Photodiode über Photostrom oder die
  lichtabhängige Entladezeit ihrer Sperrschichtkapazität verwendet werden; es
  handelt sich nicht um eine Widerstandsmessung. Beim Whisplay sind jedoch nur
  je eine aktive-low GPIO-Leitung der drei LED-Farben, kein ADC und kein
  verifizierter Schaltplan für gemeinsamen Anschluss, Vorwiderstände und
  Sperrspannung verfügbar. Die Onboard-RGB-LED ist daher aktuell kein sicherer,
  kalibrierbarer Helligkeitssensor und wird weder rückwärts betrieben noch
  experimentell umverdrahtet. Automatik erfordert einen dokumentierten externen
  Sensor beziehungsweise einen nachgemessenen, geschützten Messpfad.

### 2026-10-31 – Flacher Kopf, lesbare Mindestschrift und geschlossener Glow

- Die beiden Zeilen der Knob-Statusanzeige werden in der Höhe weiter reduziert;
  Statusleiste und Inhalt rücken entsprechend nach oben, damit der
  Medienbereich mehr nutzbare Höhe erhält und unten kein unnötiger Leerraum
  verbleibt.
- Der permanente Player-Glow erhält direkt unter der Uhr-/Statusleiste eine
  gerade obere Lichtkante. Auch dort darf ausschließlich weiches Streulicht,
  niemals eine feste Linie sichtbar sein.
- Medienbilder, Senderlogos, Webcam- und Wetterinhalte verwenden denselben
  43-Pixel-Radius wie die reale Displaykontur.
- Neue Displaytexte dürfen nicht kleiner als der SSID-/WLAN-Text sein. Der
  Batterie-Prozentwert wird von der unlesbaren 6-Pixel-Schrift auf mindestens
  diese Größe angehoben und fett gezeichnet.
- Die beiden gedrehten Randbeschriftungen für Menü und Play werden zusätzlich
  horizontal nach innen versetzt, damit die reale Rundung der oberen
  Displayecken keinen Buchstaben abschneidet.

### 2026-10-31 – Keine Rahmenlinie und kein Abschalter, nur permanenter Rand-Glow

- Robert verwirft die gerade Linie und die Abschaltmöglichkeit ausdrücklich.
  Diese Entscheidung ersetzt die zuvor festgelegte optionale innenliegende
  U-Rahmenlinie.
- Der normale Player zeigt immer einen weichen Glow in der gewählten
  Akzentfarbe. Der Ursprung verläuft an der äußeren, real abgerundeten
  Displaykontur; die zunächst offene obere Kante wurde mit der nachfolgenden
  Festlegung durch einen geraden Glow unter der Statusleiste geschlossen. Es
  darf kein scharf gezeichneter Linienkern sichtbar sein.
- In den Webeinstellungen bleibt nur die Akzentfarbe. Der Schalter
  `Bildschirmumrandung aktivieren`, das öffentliche Feld
  `screen_border_enabled` und dessen aktiver Persistenzpfad entfallen. Ein aus
  älteren Versionen eventuell noch vorhandener SQLite-Wert wird ignoriert.

### 2026-10-31 – Playerumrandung folgt den realen Displayrundungen

- Robert weist anhand der Live-Anzeige darauf hin, dass die bisher bis an die
  rechteckigen Pixelkanten gezeichnete Playerumrandung in den real
  abgerundeten Ecken des Whisplay abgeschnitten wird.
- Das offizielle Whisplay-Datenpaket benennt das 240-x-280-Panel als
  `ZJY169TP-IF95` mit 0,11655 mm Pixelabstand; die dokumentierte Geometrie
  dieser 1,69-Zoll-Panelfamilie hat vier R5-mm-Ecken, entsprechend rund
  43 Pixeln Radius.
- Der damals daraus abgeleitete innenliegende U-Rahmen wurde unmittelbar
  danach wieder verworfen. Verbindlich bleibt nur die 43-Pixel-Panelausschnitt-
  Geometrie für die Browser-Livevorschau und den permanenten weichen Glow.

### 2026-10-31 – Optionale Playerumrandung und echte PiSugar-3-Anzeige

- Robert ordnet den bisherigen gelben Balken als Player-Akzent ein und verlangt
  zunächst eine dauerhafte Option für eine Umrandung. Diese Zwischenforderung
  ist durch die spätere Festlegung „permanenter Glow ohne Linie und ohne
  Abschalter“ aufgehoben.
- Der PiSugar 3 mit 1200-mAh-Akku ist bereits als reale Hardware bestätigt.
  Die Batterietelemetrie wird nun gegen die offizielle PiSugar-3-I2C-
  Dokumentation und das reale Zielgerät geprüft und danach ohne geratenes
  Register aktiviert. Der Ladestand erscheint als Prozentzahl unmittelbar
  links neben dem Batteriesymbol; ungültige oder nicht eindeutig als
  PiSugar 3 erkannte Werte werden nicht angezeigt.
- Die Telemetrieintegration darf ausschließlich lesend auf den dokumentierten
  PiSugar-3-Pfad zugreifen. Sie darf weder Ladeparameter, RTC, Abschaltung noch
  andere Register verändern und keinen fremden Webserver mit
  Standardzugangsdaten installieren.
- Reale Zielmessung am 31.10.2026: Ein getrennter I²C-Write/Read-Zugriff liefert
  bei diesem PiSugar für jedes Register erneut das Versionsbyte `0x03` und ist
  deshalb ausdrücklich ungeeignet. Wie der Hersteller-Kerneltreiber muss
  OpenR4d10 `I2C_SMBUS_BYTE_DATA` verwenden. Damit antwortet das reale Gerät
  reproduzierbar mit Version `0x03`, Anwendungsmodus `0x0F` und Kapazität
  `0x5A` beziehungsweise 90 Prozent. Dieser SMBus-Ablauf ist als
  Regressionstest festzuhalten.

### 2026-10-31 – Intelligente Radioaufnahme und einfacher Musikplayer

- Robert verlangt einen kontinuierlichen, begrenzten Radio-Ringspeicher. PTT
  bedeutet im Radiodienst „dieses Lied behalten“; auch ein bereits gespielter
  Liedanfang wird aus dem Vorpuffer übernommen. Daneben gibt es einen
  Daueraufnahmemodus, der den gesamten Stream zunächst aufnimmt und daraus
  einzelne Lieder extrahiert.
- ICY-/Stream-Metadaten liefern bevorzugt Titelgrenzen, Interpret und Titel.
  Senderansagen und Jingles dürfen Bestandteil der Datei bleiben. Unklare
  Stücke werden nicht erfunden benannt, sondern zur Prüfung abgelegt.
- Dauerhafte Namen lauten ausschließlich `Interpret – Lied`; Album und
  Radiosender werden weder angezeigt noch in Dateinamen übernommen. Dubletten
  werden über normalisierte Metadaten und lokale Audio-/Inhaltsmerkmale
  unterdrückt.
- Der Musikplayer erhält Favoriten, `Mein Soundmix` als Favoriten-Shuffle im
  Endlosloop, Shuffle für alle Aufnahmen, Löschen mit Bestätigung sowie sicher
  lokal zwischengespeicherte Cover mit neutralem Fallback.
- Vier weitere kuratierte Radios werden nach Quellenprüfung ergänzt: 107.7,
  AFN The Eagle, Rock Antenne und Rock FM.
- Alle gleichrangigen Browser-Tabs verwenden denselben kompakten Titel. Die
  DWD-/EUMETSAT-Quellenzeile steht rechts oberhalb statt über dem Wetterbild.
- Die Startlautstärke beträgt 30 Prozent. System- und Einstellungsansichten
  zeigen keine Mediengrafik und keinen Play-Knopf. Die letzte sinnvolle
  Dienstansicht darf wiederkehren, `SYSTEM` ist aber kein Medien-Fallback.
- Der Menübaum ist ausschließlich eine interne Debug-/Entwicklerübersicht für
  Robert und die Implementierung. Er darf weder als Produktseite noch als
  sichtbarer Menüpunkt in Display oder Weboberfläche erscheinen. Navigation,
  Unterseiten und Eingabeaktionen werden dennoch versioniert dokumentiert und
  gegen die Implementierung getestet.
- `VOL SQL CH SRV` und deren Werte sowie WLAN-AP-Name und IP-Adresse werden
  gegenüber 0.10.24 mit Faktor 1,2 gezeichnet, ohne die zentrierte Uhr zu
  verschieben.
- Die Radioansicht verwendet das Senderbild über die verfügbare Inhaltsbreite
  und beschneidet es unten kontrolliert. Unter dem Sendernamen steht, soweit
  per Stream-Metadaten verfügbar, ausschließlich `Interpret – Lied`.
- Der Play/Pause-Knopf ist höchstens so hoch wie Sendername und Liedzeile
  zusammen und darf weder Bild noch Metadaten verdrängen.

### 2026-10-31 – Reale Displayhelligkeit, kompakter Kopf und präziser Status

- Robert meldet auf dem realen Pi Zero 2 W: Bei 100 Prozent ist die
  Whisplay-Beleuchtung stabil, jeder niedrigere Wert führt jedoch zu sichtbarem
  Wechsel zwischen hell und dunkel. Ursache ist der bisherige 1-kHz-PWM-Thread
  in Python auf dem verifizierten Backlight-Pin BCM22. Auch der Herstellerpfad
  verwendet dort Software-PWM; dessen Existenz ist kein Nachweis für eine auf
  diesem System flackerfreie Zeitsteuerung. Die dauerhafte Lösung muss deshalb
  einen zeitstabilen vorhandenen Systempfad verwenden und darf weder eine neue
  Pinbelegung noch angebliches Hardware-PWM auf BCM22 erfinden.
- Die Zielinstallation bestätigt `python3-lgpio` 0.2.2 aus dem Raspberry-Pi-
  Trixie-Repository. OpenR4d10 beansprucht BCM22 deshalb innerhalb desselben
  `WhisplayPanel` über `lgpio` und verwendet dessen C-getaktetes `tx_pwm` für
  Zwischenwerte; 0 und 100 Prozent sind feste Pegel. Der Python-Timingthread
  entfällt vollständig.
- Der erste reale 0.10.22-Start zeigte dabei eine harte Systemintegration:
  `lgpio` legt beim Modulimport seine interne `.lgd-nfy*`-Pipe im aktuellen
  Arbeitsverzeichnis an. Der gehärtete Dienst startete in `/` und durfte dort
  zurecht nicht schreiben; der Displayadapter fiel deshalb sichtbar und
  protokolliert aus. Der Dienst arbeitet nun in seinem bereits vorhandenen,
  privaten und beschreibbaren `RuntimeDirectory=/run/openr4d10`. `ProtectSystem`
  bleibt `strict`, und es wird kein zusätzlicher Schreibpfad freigegeben.
- Der anschließende reale 0.10.23-Start deckte eine zweite versionsspezifische
  Kante auf: Die installierte `lgpio`-Bindung dokumentiert Frequenz `0` als
  Stop, antwortet ohne laufende PWM jedoch mit `bad PWM micros`. OpenR4d10
  merkt sich deshalb, ob auf BCM22 tatsächlich PWM aktiv ist. Ein Stopbefehl
  wird nur dann gesendet; bei einem festen 0-/100-Prozent-Pegel wird direkt
  geschrieben. Damit bleibt auch das Schließen nach einem frühen Fehler
  ausnahmefrei. **Historischer Zwischenstand:** Seit 0.10.38 taktet nicht mehr
  `lgpio`, sondern der oben beschriebene Kernel-`pwm-gpio`-Pfad.
- Der Displaykopf wird flacher, die Uhr exakt auf der Gesamtbreite zentriert
  und der Abstand zum Diensttitel verkleinert. Der frei werdende Platz wird dem
  unteren Inhalt zugeschlagen.
- Der allgemeine Text `Hardwarekonfiguration erforderlich` ist auf dem realen
  Stack irreführend: Pi Zero 2 W, Whisplay und PiSugar sind physisch vorhanden.
  Solange nur die Energiedaten fehlen, lautet der Status präzise
  `PiSugar-Telemetrie ist nicht konfiguriert`.
- Am realen Whisplay wurde die `whisplaysound`-Karte als WM8960 mit Aufnahme-
  und Wiedergabepfad bestätigt. Herstellerseitig dokumentiert sind das
  240×280-ST7789-Display mit regelbarer Beleuchtung, zwei Mikrofone, ein
  8-Ohm-/1-Watt-Lautsprecher, ein PH2.0-Anschluss für einen externen
  Mono-Lautsprecher, eine RGB-LED und eine programmierbare Taste. Touch,
  Kamera, IMU, Encoder oder weitere Tasten werden nicht vorgetäuscht.

### 2026-10-31 – Sicherer WLAN-Fallback-Hotspot und echte SSID im Display

- Robert übernimmt das beim OpenFlexure-Mikroskop bewährte Bedienprinzip: Ist
  kein gespeichertes WLAN erreichbar, öffnet OpenR4d10 automatisch einen
  eigenen Einrichtungs-Hotspot, damit die WLAN-Reparatur vom Handy erreichbar
  bleibt.
- Die reale Zielinstallation bestätigt NetworkManager 1.52.1 auf `wlan0` sowie
  AP-, WPA2- und 2,4-GHz-Unterstützung. Der Fallback verwendet deshalb
  ausschließlich diesen vorhandenen Netzwerkbesitzer und dessen
  `ipv4.method=shared`; kein paralleles `hostapd`, `dnsmasq` oder
  `wpa_supplicant` wird eingeführt.
- Der Hotspot ist WPA2-geschützt. SSID und Kennwort werden gerätespezifisch
  lokal erzeugt und während des Setupmodus auf dem realen Whisplay angezeigt;
  das Kennwort bleibt aus Status-JSON, SQLite, Backups, Logs und Repository
  ausgeschlossen.
- Der bisher feste Text `WLAN` neben dem WLAN-Symbol wird durch die tatsächlich
  aktive SSID ersetzt. Ohne Verbindung steht dort `OFFLINE`, im Setupmodus die
  Hotspot-SSID.

### 2026-10-31 – Update-Recovery nach Reboot und geschützte WLAN-Reparatur

- Robert verlangt, dass ein alter Updatezustand nach einem Neustart niemals den
  Updateknopf blockiert. Ein früheres `queued` oder `running` wird beim neuen
  Boot automatisch als unterbrochen beendet; `rebooting` wird als abgeschlossen
  markiert. Danach ist die Schaltfläche wieder anklickbar und darf einen neuen,
  weiterhin serialisierten Lauf starten. Ein tatsächlich noch laufender
  Installer im selben Boot wird nicht während Paket- oder Dateischreibvorgängen
  abgebrochen; nach einem echten Neustart existiert dieser Prozess ohnehin
  nicht mehr.
- Zusätzlich verlangt Robert in den Einstellungen eine WLAN-Reparatur, die
  eigene SSID und eigenes Kennwort setzt und auf ausdrückliche Bestätigung
  bestehende WLAN-Profile ersetzt. Die reale Zielinstallation verwendet
  NetworkManager 1.52.1 auf `wlan0`; der neue feste Root-Helfer nutzt deshalb
  ausschließlich diesen vorhandenen Besitzer. Er testet das neue Profil vor
  dem Löschen alter Profile. Die kurzlebige Webübergabe und das von
  NetworkManager dauerhaft benötigte root-only Profil legen das Kennwort nie
  in eine Prozessargumentliste.
- WLAN-Zugangsdaten bleiben ausschließlich auf dem Gerät und werden weder in
  Git, SQLite, Statusdaten, Backups noch Protokollen gespeichert. Die
  unverschlüsselte lokale HTTP-Eingabe ist nur für ein vertrauenswürdiges LAN
  vorgesehen und wird in der Oberfläche entsprechend gekennzeichnet.

### 2026-10-31 – EUMETSAT bleibt zusätzlich zum Regenradar erhalten

- Robert entscheidet ausdrücklich, die EUMETSAT-Satellitenbilder trotz des
  neuen DWD-Regenradars zu behalten. Wetter enthält deshalb drei eigenständige
  Kanäle: Regenradar Deutschland, Satellit Deutschland und Satellit Europa.
- Bestehende Europa-Satellitenkanäle bleiben unverändert. Der neue
  Deutschland-Satellitenkanal wird über eine eigene einmalige Markierung
  ergänzt; nach einer späteren absichtlichen Löschung wird er nicht erneut
  angelegt und vorhandene Benutzerreihenfolgen werden nicht zurückgesetzt.

### 2026-10-31 – Web-Updater schreibt Status vor dem Neustart

- Der reale Pi zeigte nach einem Webupdate weiterhin `running`, obwohl der
  systemd-Helfer nicht mehr lief. Ursache: Der vom Helfer gestartete normale
  Installer löste seinen automatischen Neustart aus und beendete damit den
  Helfer, bevor dieser `rebooting` schreiben konnte.
- Im festen Webupdatepfad wird der einzige Bootstrap künftig mit
  `--no-reboot` aufgerufen. Nach erfolgreicher Installation liest der
  Root-Helfer die installierte Version, schreibt atomar `rebooting`,
  synchronisiert und startet dann selbst neu. Fehler vor diesem Punkt bleiben
  weiterhin `failed` und lösen keinen Neustart aus.
- Als Rückwärtskompatibilität erkennt der unprivilegierte Statusleser auch
  einen `running`-Eintrag aus einer früheren Boot-ID als unterbrochen und zeigt
  ihn als `failed`. Dadurch blockiert ein älterer Webupdate-Neustart keine
  späteren Updates mehr, ohne einen unbestätigten Erfolg zu behaupten.

### 2026-10-31 – Dienstansicht von Hintergrundaudio getrennt; DWD-Regenradar

- Robert stellt klar, dass ein Dienstwechsel nur die Ansicht wechselt. Der
  laufende Audiodienst spielt im Hintergrund weiter; erst Play in einem anderen
  audiofähigen Dienst ersetzt ihn. Wetter und andere visuelle Dienste dürfen
  Audio weder beim Öffnen noch beim Kanalwechsel oder Refresh verändern.
- Der wiederholte Sprung zur Wetteransicht entsteht durch den bisher gemeinsam
  verwendeten `active_service`-Zustand für Ansicht und Medienquelle. Diese
  Zustände werden getrennt; Kanal- und Play-Routing richten sich nach der
  sichtbaren Geräteansicht, der Player behält seinen eigenen Audioeigentümer.
- Der Deutschland-Wetterkanal verwendet künftig primär Roberts offiziellen
  DWD-Regenradarfilm. Die GIF-Frames werden wie die WMS-Bilder begrenzt geladen,
  lokal dekodiert und als sichere JPEG-Sequenz gecacht. Europa bleibt vorerst
  der bestehende METEOSAT-Kanal.

### 2026-10-31 – Einzelne kompakte Radiosenderliste

- Die Senderbibliothek wurde bisher zweimal aus demselben SQLite-Zustand
  dargestellt: oben als große Schnellwahlkarten und darunter als sortierbare
  Verwaltungsliste. Robert entfernt die redundante obere Kartenansicht.
- Im Browser bleibt ausschließlich die kompakte Liste mit Senderbildern,
  Namen, Metadaten, Sortierung und Löschen erhalten. Ihre Abspielen-Knöpfe
  verwenden die gelbe Standard-Akzentfarbe.

### 2026-10-31 – Kompakte Dienstliste mit Metadatensuche

- Die großflächigen Dienstkarten werden durch eine einspaltige, responsive
  Liste ersetzt. Jede Zeile behält Status, Beschreibung, Adapterhinweis,
  Sortierung und Aktivierung, benötigt aber deutlich weniger Platz.
- Ein Suchfeld oberhalb der Liste filtert lokal über sämtliche Dienstmetadaten,
  nicht nur über den Anzeigenamen. Echte Logos werden nur aus verifizierten
  lokalen Projektdateien verwendet; andernfalls bleibt die Darstellung neutral.

### 2026-10-31 – Menü-Scrollrichtung, PTT-Randfeld und Displayecken

- Robert korrigiert die Browsernavigation im geöffneten Gerätemenü: Pfeil hoch
  bewegt die Auswahl nach oben, Pfeil runter nach unten. Der bestehende
  gemeinsame `right_outer`-Pfad bleibt erhalten.
- Die bisherige Browser-PTT-Taste `Q` wird vollständig durch gehaltenes
  Backspace ersetzt. Außerhalb bearbeitbarer Felder aktiviert `keydown` PTT
  beziehungsweise Menü-Zurück; `keyup`, Fokusverlust und ein ausgeblendeter
  Tab geben den Zustand sicher frei. In Eingabefeldern löscht Backspace normal.
- Der bisher aus zwei dicken Linien gezeichnete Zurück-Pfeil entfällt. Ein
  kleines gefülltes Pfeil-Icon sitzt nun in einem links abgerundeten,
  rechts offenen und über den Displayrand hinauslaufenden Akzentrahmen, der die
  Zugehörigkeit zur PTT-Taste sichtbar macht. Aktives PTT nutzt dieselbe Form
  als rotes Feld mit weißer Schrift.
- Die linke Akzentlinie leuchtet im Player weich, bleibt im Menü aber scharf.
  Beide vertikalen Kopftexte rücken aus den abgerundeten oberen Displayecken;
  der rechte Text wird um 180 Grad gedreht.

### 2026-10-31 – Browser-Sprachumschaltung und kompakter Live-Display-Kopf

- Robert entfernt die redundante Überschrift `Geräteansicht` aus der festen
  Live-Display-Karte; die kurze Bereichsmarke bleibt erhalten.
- Die Browseroberfläche erhält eine lokal gespeicherte Sprachwahl für English,
  Deutsch, Polski, Français und Español. Statische Beschriftungen sowie
  dynamisch erzeugte Status-, Bedien- und Listenmeldungen verwenden denselben
  kuratierten Übersetzungskatalog mit englischem Fallback.
- Die Browsersprache bleibt eine Webpräferenz und ändert nicht ungefragt die
  Sprache der physischen Geräteansicht.

### 2026-10-31 – Radioüberschrift auf halbe Größe reduziert

- Robert bewertet die Browserüberschrift `Sender & Wiedergabe` als deutlich zu
  groß. Ausschließlich dieser Titel wird auf ungefähr 50 Prozent der bisherigen
  responsiven `h1`-Größe verkleinert. Andere Überschriften und das Kartenlayout
  bleiben unverändert.

### 2026-10-31 – DWD-Satellitenwetter und persistente Dienstpriorität

- Robert verlangt einen konfigurierbaren Wetterdienst. Die erste Ausbaustufe
  besteht aus den beiden DWD-METEOSAT-Bildkanälen Deutschland und Europa; die
  jüngsten verfügbaren 3-Stunden-Frames laufen jeweils in einer Endlosschleife.
- Die Anwendung verwendet den offiziellen DWD-WMS-Dienst, hält mindestens fünf
  Minuten Abstand zwischen Aktualitätsabfragen, validiert und codiert jedes
  Bild lokal neu und zeigt bei einem Ausfall weiterhin den letzten sicheren
  Cache. Sichtbar bleibt der Quellenvermerk `DWD / EUMETSAT`.
- Wetterkanäle und Dienste erhalten eine dauerhafte Reihenfolge in der
  versionierten SQLite-Datenbank. Benutzer dürfen sie verschieben,
  priorisieren und konfigurieren; ein Softwareupdate stellt absichtlich
  geänderte Reihenfolgen oder gelöschte Standardkanäle nicht wieder her.
- Der rechte äußere Regler wechselt im aktiven Wetterdienst zyklisch zwischen
  den Wetterkanälen. Der Browser erhält einen eigenen Wetter-Tab; die native
  Geräteansicht verwendet dieselben lokal gecachten Frames.

### 2026-10-31 – Scrollbares Hauptmenü, PTT-Zurück und oranges Grundthema

- Die bisherige alleinstehende Hauptmenüüberschrift war nicht bedienbar. Direkt
  darunter stehen künftig die zehn bereits festgelegten Hauptbereiche als
  vertikale, scrollbare Liste. Der rechte äußere Kanal-/Eintragsregler navigiert
  ausschließlich in dieser Liste; Enter beziehungsweise der rechte Klick
  öffnet den markierten Punkt und darf dabei weder Sender noch Player ändern.
- PTT ist in jeder geöffneten Menüebene die Zurück-Taste. Nur ein tatsächlich
  bereiter, aktuell PTT verwendender Dienst darf diese Navigation übernehmen.
  Ohne einen solchen Dienst gibt es keine rote PTT-Anzeige und keine behauptete
  Sprachübertragung.
- Unterhalb der Batterie zeigt ein Menü deshalb normalerweise einen Pfeil nach
  links in der Akzentfarbe. Bei real aktivem PTT erscheint an derselben Stelle
  ein rotes Feld mit weißem `PTT`, rechts bündig und rechts eckig sowie links
  abgerundet.
- Die Standard-Akzentfarbe wird auf das vom Nutzer festgelegte Orange
  `#FDB813` gesetzt. Ein fremder Marken- oder Quellenname wird in keiner
  sichtbaren Oberfläche ausgegeben.
- Die Browseroberfläche wird gleichzeitig von der langen Einzelseite auf
  getrennte Funktions-Tabs umgestellt. Rechts oben bleibt auf Desktopbreite die
  exakte native 240-x-280-Geräteansicht stehen; sie wird serverseitig mit dem
  vorhandenen Displayrenderer erzeugt. Die Senderverwaltung zeigt die bereits
  vorhandenen Senderbilder wieder neben den jeweiligen bekannten Sendern.

### 2026-10-31 – Kompakter Funktionskopf und aufgeräumte Geräteansicht

- Robert verkürzt die vier normalen Funktionsbezeichnungen verbindlich auf
  `VOL`, `SQL`, `CH` und `SRV`; andere Sprachen verwenden korrespondierende,
  maximal dreistellige Kurzformen. Die Schrift und die Uhr werden größer,
  während die vier Kopffelder weniger Höhe beanspruchen. Das Datum entfällt.
- Im geöffneten lokalisierten Hauptmenü wird der komplette Player ausgeblendet;
  der Inhaltsbereich zeigt ausschließlich das Menü in großen Buchstaben.
- Die untere Leiste mit `READY` und `OpenR4d10`, der redundante Dienstname über
  dem Radiosender sowie ausgeschriebene Playerzustände wie `PAUSED:` entfallen.
- Der Play/Pause-Button sitzt rechts oben unter der Batterie. Der gewonnene
  Raum gehört dem größeren Senderbild beziehungsweise Logo und der größeren
  Senderüberschrift; es werden keine anderen Inhalte ergänzt.

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
- Die zehn kuratierten Standardsender werden einmalig in die dauerhafte
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

- Die virtuelle Encoderbedienung erhielt zunächst `WASD`, Pfeiltasten,
  Leertaste, Enter und `Q` für PTT. Die spätere Entscheidung vom 2026-10-31
  ersetzt ausschließlich `Q` durch Backspace; alle Tasten verwenden weiterhin
  die bestehende logische Eingabeschnittstelle und keine parallele Navigation.
- Backspace ist ein gehaltenes Signal: `keydown` aktiviert PTT, `keyup`,
  Fokusverlust oder ausgeblendeter Tab deaktiviert es. Damit darf PTT nicht
  durch einen verlorenen Tastaturzustand eingeschaltet bleiben.
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
- Umgesetzt sind zehn Radios (SWR3, sunshine live, Deutschlandfunk, RMF FM,
  Radio ZET, BBC World Service, DIE NEUE 107.7, AFN The Eagle, ROCK ANTENNE
  und ROCK FM) sowie vier Nachrichtenfeeds (tagesschau,
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

### 2026-10-31 – Reale Offline-Ursache nach Reboot nachgewiesen

- Nach dem erneuten Erscheinen des Geräts wurden die laufende Installation und
  das aktuelle Bootjournal ausschließlich lesend untersucht. Installiert sind
  Raspberry Pi Zero 2 W, Debian 13/Trixie, Kernel `6.18.50+rpt-rpi-v8`,
  `network-manager 1.52.1-1+rpt4`, `wpasupplicant 2:2.10-24+rpt3` und
  `firmware-brcm80211 1:20260519-1~bpo13+1+rpt1`.
- NetworkManager übergibt für das bestehende `wpa-psk`-Profil fälschlich auch
  `SAE FT-SAE`. Beim realen Boot scheiterte die Anmeldung am BSSID
  `D4:24:DD:FE:8F:72`, das WPA2 und WPA3 anbietet, nach zehn Sekunden mit
  `Authentication ... timed out`. Unmittelbar danach gelang die Verbindung zum
  BSSID `2C:91:AB:94:F3:45`, das nur WPA2 anbietet, samt DHCP-Adresse
  `192.168.1.64`. Das entspricht der bekannten Trixie-/`brcmfmac`-/SAE-
  Regression für den BCM43430/1 und erklärt, warum derselbe Pi nach manchen
  Reboots offline bleibt und nach einem weiteren Reboot wieder erscheint.
- Die APT-Historie des OpenR4d10-Laufs am 31. Oktober um 12:17 zeigt nur die
  Neuinstallation von `libchromaprint-tools`; NetworkManager, WLAN-Firmware und
  `wpasupplicant` wurden dabei nicht geändert. Der fehlerhafte
  `wpasupplicant` war bereits installiert. Der Reboot hat den vorhandenen
  Fehler ausgelöst, nicht erst ein in diesem Lauf installiertes WLAN-Paket.
- Das Journal ist derzeit nicht bootübergreifend persistent; `journalctl
  --list-boots` enthielt nach dem Wiedererscheinen nur den aktuellen Boot. Ein
  erneutes Flashen würde deshalb zusätzlich die noch vorhandenen APT- und
  Dateisystemspuren vernichten.
- Der erste Start von `openr4d10-hotspot.service` schlug im selben Boot mit
  `status=226/NAMESPACE` fehl, weil `/run/openr4d10` für `ReadWritePaths` noch
  nicht existierte. Spätere Timerläufe funktionierten. Außerdem darf der
  Helfer eine lediglich aktivierende Infrastrukturverbindung nicht anhand von
  UUID und Modus bereits als verbunden einstufen; der tatsächliche
  NetworkManager-Gerätestatus muss Bestandteil der Fallback-Entscheidung sein.
- Die linken Kopfzeilenbeschriftungen (`LAU`/`SQL` beziehungsweise ihre
  Übersetzungen) stehen drei Pixel weiter rechts. Die Werte behalten ihre
  bisherige Position, damit im 240-Pixel-Header kein zusätzlicher Platz
  verloren geht.
- Version 0.10.43 härtet den Fallback gegen genau den beobachteten Ausfall:
  systemd legt `/run/openr4d10` vor dem Sandbox-Aufbau an; ausschließlich
  NetworkManagers vollständig aktivierter Gerätestatus `100` zählt als
  verbundener Client oder Access Point. Nach 60 Sekunden beendet der Helfer
  einen festhängenden WPA-/SAE-Verbindungsversuch, schaltet das Software-WLAN
  ein und versucht den sichtbaren, gerätespezifischen WPA2-Hotspot bis zu
  dreimal. Fehlende Hardware, ein noch nicht bereiter NetworkManager und ein
  fehlgeschlagener AP-Start werden ohne Zugangsdaten im Status festgehalten;
  der 30-Sekunden-Timer versucht die Wiederherstellung weiter.

### 2026-10-31 – Einheitliche AmbientR4D10-Bildserie

- Alle sechs eingebauten Ambient-Szenen besitzen lokale, textfreie
  Quadratgrafiken: Café, Wald, Meer/Strand, Waldbach, sanfter Regen sowie
  Nachtfeld/Grillen.
- Verbindliche Bildsprache ist eine ruhige, hochwertige, filmische
  Miniaturwelt mit dunklen Anthrazit-/Petroltönen und zurückhaltenden
  `#FDB813`-Lichtakzenten. Hauptmotive bleiben im zentralen Bildbereich, damit
  die Grafik sowohl als 46-Pixel-Web-Thumbnail als auch im zugeschnittenen
  240-x-280-Geräteplayer lesbar bleibt.
- Die Grafiken liegen unter `assets/ambient/`, werden offline aus dem Release
  ausgeliefert und erscheinen sowohl in der Webliste als auch auf dem echten
  Whisplay. Die API akzeptiert ausschließlich IDs aus dem kuratierten
  Ambient-Katalog; benutzerdefinierte Szenen verwenden weiterhin den
  Initialen-Fallback.

### 2026-10-31 – Ambient-Kanalwahl bleibt sichtbar; ruhigeres Café

- Ein realer Test zeigt: Läuft bereits Ambient-Kanal 01, springt die Anzeige
  nach dem Blättern auf einen anderen Ambient-Kanal wieder auf 01 zurück.
  Ursache ist die erneute Darstellung des aktiven Audioeigentümers statt der
  separat ausgewählten Szene. In der sichtbaren Ambient-Ansicht haben deshalb
  Szenenauswahl und Kanalnummer Vorrang; der bisherige Klang läuft im
  Hintergrund weiter, bis Play den neu ausgewählten Klang startet. Play/Pause
  pausiert nur dann, wenn ausgewählte und tatsächlich aktive Szene identisch
  sind.
- Die bisherige Caféaufnahme mit dichter, hektischer Menschenmenge wird durch
  eine deutlich ruhigere Coffeehouse-Aufnahme mit kleiner, leise sprechender
  Gruppe ersetzt. Quelle ist `0105coffeehouse.wav` von `moxobna` auf
  Freesound, veröffentlicht unter CC0. Verwendet wird die öffentliche,
  queryfreie Ogg-Vorschau; deren SHA-256 lautet
  `86c51e4fa5001c4fbf597c8725b50e36a347c31fbc0c499cad0a1bc27e9bb072`.
  Die vorhandene Café-Grafik bleibt unverändert.
- Eine einmalige Migration ändert ausschließlich die noch unveränderte alte
  eingebaute Caféquelle. Gelöschte Szenen werden nicht wiederhergestellt und
  benutzerdefinierte Quellen werden nicht überschrieben.

### 2026-10-31 – Native BrandMeister-Audio bestätigt und geräteinterne TG-Wahl

- Ein realer abonnierten HoseLine-Ruf war hörbar über den montierten
  Whisplay-Lautsprecher. Der native Empfangspfad ist damit bis zur Zielhardware
  bestätigt; Browseraudio bleibt eine optionale zweite Ausgabe.
- Die DMR-Ansicht verwendet den lokal gecachten vollständigen offiziellen
  Talkgroup-Katalog auch ohne Webbrowser. Rechts außen blättert pro Rastung
  genau eine Talkgroup, links innen springt pro Rastung 25 Einträge und ein
  kurzer rechter Druck übernimmt die markierte Talkgroup in die persistente
  Quickliste beziehungsweise schaltet sie dort ab.
- Der physische Funktionskopf zeigt in DMR lokalisierte tatsächliche
  Achsenfunktionen (`SPR`/`TG` auf Deutsch) sowie den Sprungwert `25` und die
  wirkliche Talkgroup-Nummer. Das fachlich falsche `SQL`/`KAN` erscheint in
  dieser Ansicht nicht mehr.

### 2026-10-31 – Persistente Kamera-Bibliothek als erstes Dienstpaket

- Der bisherige flüchtige Zwei-Slot-Kameratest wird durch eine updatefeste,
  sortierbare SQLite-Bibliothek mit bis zu 100 Kameras ersetzt. Name, Typ,
  Reihenfolge, Aktivierung und credential-freie Quelle bleiben erhalten;
  löschen entfernt auch den lokal erzeugten Cacheframe.
- `snapshot` lädt ein begrenztes Einzelbild. `mjpeg` liest höchstens fünf MiB
  bis zum ersten vollständigen JPEG und beendet die Fremdverbindung danach.
  `rtsp` ruft über einen festen argument-only-`ffmpeg`-Pfad genau einen Frame
  mit 15-Sekunden-Zeitgrenze und Ausgabelimit ab. Alle Varianten werden
  dekodiert, dimensionsgeprüft, auf höchstens 640 × 480 verkleinert und als
  lokales JPEG neu codiert; Remote-Bytes werden nie blind an den Browser
  weitergereicht.
- Persistente Kamera-URLs mit Benutzer/Passwort oder Querystring sind verboten.
  Authentifizierte private RTSP-/ONVIF-Kameras benötigen den nachfolgenden
  isolierten Adapter mit eigener 0600-Secret-Datei. Diese Grenze ist sichtbar
  dokumentiert und darf nicht durch Zugangsdaten in SQLite umgangen werden.

### 2026-10-31 – BrandMeister-Aktivitäts- und Teilnehmerliste

- Die BrandMeister-Geräteansicht verwendet die bisherige große Bildfläche nicht
  mehr für eine dekorative Länderflagge. Stattdessen zeigt sie bis zu sechs
  kompakte Talkgroup-Zeilen mit Statussymbol, Nummer, Name und – ausschließlich
  soweit im empfangenen HoseLine-Paket vorhanden – DMR-Quell-ID und Talker
  Alias. Der Browser verwendet dieselbe Information in seiner Quickliste.
- Aktuell sprechende Talkgroups erhalten in ihrem normalen Listeneintrag einen
  klaren grünen Glow, werden aber nicht in einer eigenen Kopfzeile dupliziert.
  Nach Rufende bleibt der letzte beobachtete Teilnehmer als
  „zuletzt gehört“ sichtbar, bis eine neue Empfangssitzung beginnt. Die Liste
  behauptet ausdrücklich nicht, alle stillen Mitglieder einer Talkgroup oder
  deren Anwesenheit zu kennen.
- Eine geografische oder personenbezogene Anreicherung über RadioID wird nicht
  ungefragt eingebaut. Dessen öffentliche API erlaubt normale Einzelabfragen,
  weist für öffentliche Integrationen aber auf Genehmigung beziehungsweise
  API-Key und Nutzungsregeln hin. OpenR4d10 zeigt daher zunächst nur die real
  aus HoseLine empfangenen Identitäten.
- Die Talkgroup-Umschaltung muss ohne Anleitung verständlich sein. Die rechte
  vertikale Gerätebeschriftung zeigt deshalb aktionsbezogen `AN`, wenn ein
  kurzer Druck die ausgewählte TG aktiviert, und `AUS`, wenn er sie
  deaktiviert. Der Browser behält die Checkbox und schreibt zusätzlich den
  übersetzten Zustand An/Aus in dieselbe kompakte Zeile.

### 2026-10-31 – Vollständige TG-Liste am Gerät und PTT-Umschaltung

- Robert stellt klar, dass die DMR-Geräteansicht nicht nur eine einzelne
  TG-Karte und auch nicht nur die bis zu sechs aktivierten Gruppen zeigen darf.
  Der gesamte offizielle Katalog ist als begrenztes sichtbares Scrollfenster
  bedienbar; die aktive abonnierte TG glüht direkt in ihrem normalen Eintrag.
- Aktivierte TGs stehen im Geräte-Browsepfad zuerst, alle inaktiven folgen
  darunter. Es werden sechs Zeilen je Frame veröffentlicht und
  gezeichnet; Drehen verschiebt dieses Fenster über den vollständigen lokalen
  Katalog, damit Status und 240-x-280-Renderer begrenzt bleiben.
- In der DMR-Ansicht schaltet die PTT-Druckflanke die markierte TG an oder aus.
  Loslassen schaltet nicht erneut. Der bisherige rechte Kurzdruck bleibt als
  kompatible Zweitbedienung. Beide Aktionen ändern nur die lokale Empfangsliste
  und erzeugen ausdrücklich keine Sendung oder BrandMeister-PTT-Nachricht.

### 2026-10-31 – Eindeutige BrandMeister-Klickbelegung

- Robert hebt die doppelte Umschaltung durch PTT und rechten Kurzdruck wieder
  auf. In der normalen DMR-Katalogansicht aktiviert beziehungsweise deaktiviert
  ausschließlich der kurze rechte Druck die markierte Talkgroup.
- Eine PTT-Druckflanke springt stattdessen zum Anfang des aktuell gültigen
  enabled-first Katalogs; die Loslassflanke bleibt wirkungslos. In geöffneten
  Menüs behält PTT seine allgemeine Bedeutung Zurück beziehungsweise Abbrechen.
- Ein mindestens zwei Sekunden gehaltener rechter Druck bleibt das
  BrandMeister-Schnellmenü. Keine dieser Belegungen sendet Sprache oder eine
  BrandMeister-PTT-Nachricht.

### 2026-10-31 – Physischer Whisplay-Taster speist den PTT-Pfad

- Roberts realer Druck auf den Whisplay-Taster neben dem gezeichneten
  Zurück-Pfeil blieb ohne Wirkung, weil bisher ausschließlich Web/Backspace ein
  logisches PTT-Ereignis erzeugten. Das Panel besitzt kein Touchscreen; die
  gezeichnete Schaltfläche selbst ist deshalb kein Eingabegerät.
- Die Herstellerdokumentation und der aktuelle offizielle Runtimequellcode
  bestätigen für Raspberry Pi den Whisplay-Taster auf physischem Pin 11,
  entsprechend BCM17. Die Platine besitzt dort einen externen Pulldown;
  gedrückt ist HIGH und losgelassen LOW. Es wird kein interner Pullup erfunden.
- Der vorhandene Whisplay-Adapter beansprucht BCM17 als Eingang, entprellt beide
  Flanken und übergibt sie als dasselbe hardwareunabhängige PTT-Ereignis an den
  zentral serialisierten Anwendungspfad. Web, Tastatur und Hardwaretaster
  erhalten dadurch keine getrennte Navigation. Beim Schließen des Dienstes
  wird der Abfragethread vor der GPIO-Freigabe beendet.

### 2026-10-31 – BrandMeister-Play und PTT-TG-Schaltung

- Robert korrigiert die unmittelbar vorherige Klickbelegung erneut und
  abschließend: In der normalen BrandMeister-Ansicht startet der kurze rechte
  Druck die Empfangswiedergabe der bereits aktivierten Talkgroups. Er ist damit
  die ausdrückliche Play-Aktion und ersetzt bei Bedarf laufendes Radioaudio.
- Die PTT-Druckflanke aktiviert beziehungsweise deaktiviert die markierte
  Talkgroup in der persistenten Quickliste. Die Loslassflanke bleibt inert und
  es wird weiterhin keinerlei Sprache oder DMR-PTT gesendet. In geöffneten
  Menüs bleibt PTT Zurück/Abbrechen; langer rechter Druck bleibt Schnellmenü.
- Sechs bereits aktivierte Gruppen verhindern Play nicht. Das Sechserlimit gilt
  ausschließlich für den Versuch, eine siebte Gruppe zu aktivieren.
- Die Displaylautstärke stammt dienstübergreifend aus dem zentralen tatsächlichen
  Audiopegel. Eine inaktive BrandMeister-Instanz darf während sichtbarer
  DMR-Ansicht nicht ihren alten Wert – typischerweise 30 Prozent – über die
  hörbar geänderte Radio-/Playerlautstärke schreiben. Beim Start des nativen
  DMR-Empfängers wird genau dieser zentrale Pegel übernommen.

### 2026-11-01 – Ambient-Klanglagen und persistente Lieblingsmischungen

- AmbientR4D10 erhält vier weitere eigenständige, offline gecachte Grundszenen:
  dezente Vögel auf einer Streuobstwiese, entferntes Autobahnrauschen mit
  vereinzelten Vögeln, Meer von einer Klippe mit hörbar entferntem Wasser und
  entfernten Donner. Jede Szene verwendet eine vorab geprüfte, queryfreie
  Freesound-Ogg-Vorschau mit dokumentierter CC0-Quelle, festem SHA-256 und eine
  gebündelte textfreie Grafik im vorhandenen dunklen Diorama-Stil.
- Dieselben vier Aufnahmen sind zusätzlich als dezente Klanglagen verfügbar.
  Sie laufen ausschließlich zusammen mit einer aktiven Ambient-Grundszene und
  werden über getrennte lokale `mpv`-Instanzen auf dem bereits real bestätigten
  ALSA-Mischpfad ausgegeben. Ein echter Laufzeittest am Whisplay bestätigte,
  dass der ALSA-Ausgang neben dem bestehenden Hauptplayer eine zweite leise
  Instanz gleichzeitig öffnet; es wird daher kein speicherintensiver
  `aloop`-Filter und kein paralleler neuer Audio-Stack eingeführt.
- Im Ambient-Schnellmenü blättert rechts außen durch die Klanglagen. Ein kurzer
  rechter Druck schaltet die markierte Lage ein oder aus, links innen verändert
  ausschließlich deren relativen Pegel in Zehn-Prozent-Schritten und PTT geht
  zurück. Die normale linke Außenachse bleibt der Gesamtlautstärke vorbehalten.
- Aktivierung und Pegel werden in der bestehenden SQLite-Einstellungsablage
  gespeichert. Ein Lieblingsmix speichert Grundszene plus alle Klanglagen als
  neuen normalen Ambient-Kanal; er ist dadurch sortierbar, löschbar,
  updatefest und direkt über Browser oder Gerät erneut abspielbar. Das
  Schnellmenü enthält dafür einen eigenen `Mix speichern`-Eintrag; der Browser
  erlaubt zusätzlich einen frei gewählten Namen.
- Der Zero 2 W darf höchstens zwei Zusatzlagen gleichzeitig dekodieren. Ein
  dritter Aktivierungsversuch wird verständlich abgewiesen; diese feste Grenze
  schützt CPU, Akku und die bereits beobachtete Display-PWM-Stabilität.

### 2026-11-01 – DMR-Länderfilter und geführtes Ersetzen oberhalb der TG-Grenze

- Die normale DMR-Belegung bleibt: kurzer rechter Druck/Enter startet oder
  stoppt den Empfang, kurzer PTT-/Backspace-Druck schaltet die markierte TG.
  Ein mindestens zwei Sekunden gehaltener PTT-/Backspace-Druck öffnet dagegen
  eine geräteinterne Länderliste. Der zentrale Eingabepfad misst dafür die
  bereits vorhandenen aktiven HIGH/LOW-Flanken; es entsteht weder eine zweite
  GPIO-Auswertung noch eine Sendefunktion.
- Die Länderliste wird aus dem lokal gecachten offiziellen Talkgroup-Katalog
  gebildet und enthält `Alle`, alle sicher aus DMR-MCC ableitbaren Länder sowie
  `Andere` für nicht konservativ zuordenbare Gruppen. Rechts außen scrollt,
  rechter Druck übernimmt den Filter, PTT geht zurück. Ein Länderfilter ändert
  nur die Browse-Liste, niemals die sechs laufenden HoseLine-Abonnements.
- Der Länderfilter gilt ausschließlich für den inaktiven Katalog, aus dem neue
  Talkgroups hinzugefügt werden. Die bereits aktivierten Talkgroups bilden
  weiterhin den festen enabled-first-Block am Anfang der normalen DMR-Liste
  und bleiben unabhängig vom gewählten Land vollständig sichtbar und
  bedienbar. `Alle` zeigt darunter wieder den vollständigen inaktiven
  Standardkatalog; ein Land zeigt darunter nur die passenden noch inaktiven
  Kandidaten. Aktive TGs dürfen durch einen Hinzufügen-Filter niemals
  ausgeblendet werden.
- Beim Aktivieren einer siebten TG wird nicht mehr nur das Sechserlimit
  gemeldet. Stattdessen merkt der Dienst die gewünschte neue TG und öffnet
  `Welche ersetzen?` mit den sechs aktiven Gruppen. Rechts außen wählt die zu
  ersetzende TG, rechter Druck führt den Tausch aus, PTT bricht ohne Änderung
  ab. Der Browser bietet dieselbe Auswahl vor dem Aktivieren einer siebten TG.

### 2026-11-01 – Reale BCM22-PWM-Knotenbezeichnung

- Der Raspberry-Pi-Device-Tree schreibt die Unit-Adresse des BCM22-PWM-Overlays
  hexadezimal als `pwm_gpio@16`. Ein Helfer, der nur den scheinbar naheliegenden
  Dezimalnamen `pwm_gpio@22` prüft, findet das reale `/sys/class/pwm/pwmchip*`
  nicht und lässt Backlight-Initialisierung sowie Bootanimation scheitern.
- Der feste Root-Helfer akzeptiert deshalb ausschließlich `pwm_gpio@16` als
  reales Ziel und `pwm_gpio@22` als Kompatibilitätsschreibweise. Overlay und
  physischer BCM bleiben unverändert `gpio=22`; es wird kein anderer Pin
  freigegeben.
- Die native Bootanimation läuft mit `ProtectSystem=strict`, veröffentlicht
  aber nach dem ersten vollständigen Frame atomar einen Helligkeitsauftrag.
  Ihre Unit benötigt deshalb genau `ReadWritePaths=/run/openr4d10-backlight`;
  ohne diesen Pfad scheitert sie real mit `open backlight request: Read-only
  file system`. Weitere schreibbare Systempfade sind nicht zulässig.

### 2026-11-01 – Pfeiltasten im geräteinternen DMR-Menü

- Ein geöffnetes Gerätemenü besitzt im Browser die Tasten Pfeil hoch und Pfeil
  runter auch dann, wenn zuvor ein Such- oder Eingabefeld den DOM-Fokus behalten
  hat. Sonst sieht Robert zwar die DMR-Länderliste auf dem Live-Display, die
  bisherige allgemeine Eingabefeld-Sperre verschluckt aber beide Scrolltasten.
- Die Ausnahme gilt ausschließlich für diese zwei Navigationspfeile bei
  `device_ui.menu_open=true`. Backspace bleibt in editierbaren Feldern die
  Löschtaste und alle anderen Schutzregeln bleiben unverändert.

### 2026-11-01 – Zentraler Glow für jede Dienstansicht

- Der permanente weiche Display-Glow ist keine Gestaltung einzelner Dienste.
  Er wird einmal zentral vom gemeinsamen 240-x-280-Renderer nach Kopf- und
  Statusleiste und vor dem dienstspezifischen Inhalt komponiert. Recorder,
  Systemansicht und jeder zukünftig registrierte Plugin-Dienst erhalten ihn
  dadurch automatisch und dürfen ihn weder selbst nachbauen noch auslassen.
- Der frühere harte linke Akzentstreifen im gemeinsamen `SYSTEM`-/`REC`-
  Sonderzweig wird entfernt. Er war ein dienstspezifischer Rahmenrest und darf
  nicht zusätzlich über dem zentralen weichen Glow liegen.
- Nur Vollbildzustände, die ausdrücklich keine normale Dienstansicht sind,
  bleiben ohne Player-Glow: geöffnete Gerätemenüs sowie die WLAN-Hotspot-
  Einrichtung. Deren eigene klare Navigationsmarkierung bleibt unverändert.
- Ein Regressionstest prüft den Glow für sämtliche registrierten Dienste und
  insbesondere für den Recorder. Neue Renderer-Zweige dürfen nicht vor der
  zentralen Kompositionsstufe zurückkehren.

### 2026-11-01 – Sprachaufzeichnung mit PTT und Stereo-Timeline

- Der sichtbare deutsche Dienstname `RECORDER` lautet **Sprachaufzeichnung**.
  Beim Öffnen übernimmt dieser Dienst Audio exklusiv und beendet Radio-, DMR-,
  Ambient- sowie sonstige laufende Wiedergabe, damit Lautsprecher und Mikrofone
  keine Rückkopplung erzeugen.
- Ein gedrückter PTT-/Whisplay-Taster zeichnet die beiden Whisplay-
  Mikrofonkanäle auf; währenddessen wird ausschließlich der zentral komponierte
  Display-Glow rot. Beim Loslassen pausiert die Aufnahme und der Glow kehrt zur
  normalen Akzentfarbe zurück. Ein erneuter Druck setzt dieselbe laufende
  Aufnahme fort, statt ungefragt eine neue Datei zu erzeugen.
- Ein PTT-Doppelklick startet die Daueraufnahme. Solange sie läuft, beendet der
  nächste normale PTT-Klick oder ein weiterer Doppelklick die Daueraufnahme und
  finalisiert den bis dahin geschriebenen Stand. Die normale PTT-Haltefunktion
  bleibt außerhalb des Dauerbetriebs zusätzlich verfügbar. Die Erkennung
  erfolgt auf dem vorhandenen zentralen logischen PTT-Pfad und nicht durch eine
  zweite GPIO-Auswertung.
- Die Geräteansicht zeigt eine fortlaufende Stereo-Timeline: Pegelausschläge
  des rechten Mikrofons laufen oberhalb, die des linken Mikrofons unterhalb der
  Mittellinie. Bei pausierter Aufnahme steht die Timeline; beim Fortsetzen wird
  sie an derselben Aufnahme weitergeführt.
- Audiodaten werden bereits während der Aufnahme in eine absturzfeste lokale
  Arbeitsdatei geschrieben. Verlassen der Recorderansicht finalisiert die
  aktuelle Aufnahme automatisch; Ausschalten oder Dienstabsturz darf bereits
  geschriebene Sprache nicht verwerfen.
- Fertige Dateien liegen unter der Medienbibliothek im festen Bereich
  `VoiceRecorder/JJMMTT/`. Ordner heißen `JJMMTT`, Dateien verwenden den
  Startzeitpunkt und exakt das Schema
  `JJMMTT_HHMMSS_VoiceRecorder.mp3`. Die offensichtliche Tippvariante
  `VioceRecorder` wird nicht verwendet.
- Der Musikplayer zeigt diesen Bereich als eigenen Ordner `VoiceRecorder` mit
  Datumsunterordnern. Dateien aus Sprachaufzeichnung werden nicht mit
  Radio-Liedern oder deren Interpretensortierung vermischt.

### 2026-11-01 – Stream-Aufnahme bleibt im Dienst und markiert speicherwürdige Titel

- Stream-Aufzeichnung bleibt eine Funktion des jeweiligen Streamingdienstes
  und wird nicht in den separaten Mikrofon-Dienst `Sprachaufzeichnung`
  verschoben. Der Sprachrecorder nimmt ausschließlich die Whisplay-Mikrofone
  auf; der Radio-Ringspeicher bleibt Teil des Radios.
- Das Radio puffert jeden laufenden Titel nur vorläufig vollständig. Endet ein
  Titel ohne PTT-Markierung und ohne aktiven Dauerbetrieb, wird sein temporärer
  Mitschnitt sofort verworfen. Ein normaler PTT-Klick markiert exakt den
  aktuellen Titel als speicherwürdig; der Glow bleibt bis zur Titelgrenze rot.
- Ein markierter Titel wird als MP3 im Interpretenordner abgelegt. Ordnername
  ist der Interpret unter dem festen Musikbereich `Media/Music`, Dateiname
  exakt `Interpret - Lied.mp3`, zum Beispiel
  `Media/Music/Gorillaz/Gorillaz - Feel Good Inc.mp3`. Die sichtbaren Namen verwenden den
  normalen Bindestrich wie vorgegeben. Unbekannte oder widersprüchliche
  Metadaten bleiben im dokumentierten Prüfbereich und werden nicht erfunden.
- Die beiden Aufnahmearten dürfen nicht im selben Ordner landen:
  Radio-/Streamtitel liegen ausschließlich unter `Media/Music/<Interpret>/`,
  Sprachaufnahmen ausschließlich unter `Media/VoiceRecorder/JJMMTT/`.
  Eine Aktualisierung übernimmt den früheren Bereich `Media/recorded`
  verlustfrei nach `Media/Music`, ohne beliebige Benutzerordner umzudeuten.
- Ein PTT-Doppelklick startet den Radio-Dauerbetrieb „alle Titel behalten“;
  jeder folgende sauber abgegrenzte Titel wird gespeichert. Solange eine
  Daueraufnahme läuft, beendet der nächste normale PTT-Klick oder ein weiterer
  Doppelklick den Dauerbetrieb. Da im Dauerbetrieb ohnehin jeder Titel erhalten
  wird, hat der normale Klick dort keine zusätzliche Markierungsbedeutung.
- Bei einem einzelnen markierten Radiotitel leuchtet der zentral komponierte
  Glow rot. Bei Daueraufnahme pulsiert der rote Glow langsam zwischen der
  normalen Standard-Glowstärke und ungefähr der doppelten maximalen Stärke
  beziehungsweise Deckkraft. Derselbe Puls gilt für die Daueraufnahme des
  Sprachrecorders; eine normale gehaltene Sprachaufnahme zeigt konstant Rot.
- **DMR/BrandMeister ist ausdrücklich von jeder Aufnahmefunktion ausgeschlossen.**
  HoseLine bleibt ein reiner Empfangsdienst. Dort schaltet PTT ausschließlich
  Talkgroups beziehungsweise bedient Filter und Navigation wie dokumentiert;
  weder kurzer noch doppelter oder langer PTT-Druck startet eine Aufnahme,
  markiert Audio oder aktiviert einen roten Aufnahme-Glow.

### 2026-11-01 – Wiedergabefarbe und polnischer Recordername

- Der polnische Gerätename des Sprachrecorders lautet im üblichen
  Endnutzer-Sprachgebrauch **`Dyktafon`**, nicht das technische
  `Rejestrator głosu`. Laufende Aufnahme bleibt `Nagrywanie`, Daueraufnahme
  `Nagrywanie ciągłe`.
- Der zentrale Dienst-Glow zeigt einen global tatsächlich laufenden
  Audioplayer grün, auch wenn gerade eine andere visuelle Dienstansicht
  geöffnet ist. Aufnahme hat Vorrang: markierte beziehungsweise laufende
  Aufnahmen bleiben rot; ohne Wiedergabe und Aufnahme bleibt der Glow in der
  gewählten Akzentfarbe.
- Jede echte Play-Aktion wird grün dargestellt. Zeigt dieselbe Stelle dagegen
  Pause oder Stop, verwendet sie die gewählte Akzentfarbe. Das gilt für den
  physischen Play-Kreis und die tatsächlichen Play-Aktionen im Browser, nicht
  pauschal für Aktivieren-, Aktualisieren- oder Anzeigen-Schaltflächen.
- Beim Öffnen von `Dyktafon`/`Sprachaufzeichnung` endet weiterhin jede
  Audioausgabe sofort: mpv-basierte Streams, Radio-Ringspeicher,
  Ambient-Zusatzlagen und BrandMeister. Erst danach darf Mikrofonaufnahme
  beginnen.

### 2026-11-01 – Positionsbearbeitung in der Sprachaufzeichnung

- Bereits das Öffnen von `Dyktafon`/`Sprachaufzeichnung` beendet weiterhin
  synchron und vor jeder weiteren Recorderaktion sämtliche Streamingquellen:
  BrandMeister, Ambient-Grundton und -Zusatzlagen, Radio-Ringspeicher sowie den
  gemeinsamen mpv-Player. Die Recorderansicht darf niemals parallel zu einem
  fremden Stream starten.
- Eine pausierte aktuelle Sprachaufnahme besitzt einen sichtbaren Zeitcursor.
  Der rechte äußere Encoder verschiebt ihn pro Rastung um exakt eine Sekunde:
  gegen den Uhrzeigersinn zurück, im Uhrzeigersinn vor. Der linke äußere
  Encoder übernimmt im Recorder die anschließend ausdrücklich zugeordnete
  Feinjustierung um 0,1 Sekunden pro Rastung und ist dort deshalb nicht die
  Lautstärke. Der rechte innere Encoder bleibt die notwendige Dienstwahl und
  wird nicht doppelt belegt.
- Der linke innere Encoder springt im Recorder richtungsabhängig sofort an
  eine Grenze: gegen den Uhrzeigersinn zum Anfang, im Uhrzeigersinn zum Ende.
  Der rechte Druck startet die aktuelle Aufnahme ab dem Cursor beziehungsweise
  pausiert ihre Wiedergabe. Anfangswiedergabe ist dadurch nach einem Sprung auf
  null ohne Browser möglich.
- Die vertikale rechte Randbeschriftung bezeichnet ausschließlich den rechten
  Encoder-Druck und lautet im Recorder deshalb lokalisiert `PLAY`/`PAUSE`
  (`GRAJ`/`PAUZA` auf Polnisch), niemals `PTT`. PTT ist der separate reale
  Whisplay-Hardwaretaster beziehungsweise dessen Backspace-Simulation und
  bleibt allein für Aufnahmehalten/Doppelklick zuständig.
- Die Wiedergabe im Sprachrecorder verwendet immer 100 Prozent Lautstärke; der
  linke äußere Encoder bleibt dort ausschließlich die 0,1-Sekunden-
  Feinpositionierung. Beim Verlassen wird die zuvor für andere Audiodienste
  gültige Lautstärke wiederhergestellt, damit Radio oder Ambient nicht
  unbeabsichtigt mit Recorder-Maximalpegel starten.
- Beginnt PTT bei einem Cursor vor dem bisherigen Ende, überschreibt die neue
  Mikrofonaufnahme genau den zeitlich überdeckten Abschnitt. Der davor liegende
  Teil und ein durch die neue Aufnahme nicht erreichter Rest danach bleiben
  erhalten. Arbeitsdatei und Bearbeitungsmetadaten bleiben bis zum atomaren
  Abschluss im absturzsicheren Pending-Verzeichnis.
- Positionsänderungen sind während laufender Mikrofonaufnahme gesperrt. Vor
  einer neuen Aufnahme endet eine interne Recorder-Wiedergabe; fremde Streams
  werden dadurch nicht wieder gestartet.
- Der lokalisierte Aufnahmehinweis steht mindestens in der Größe der
  Statusinformationen in einem eigenen Bereich oberhalb der Timeline. Er darf
  weder als winzige Schrift noch ein zweites Mal mitten in der Audiospur
  erscheinen. Cursor, Gesamtdauer und Wiedergabestatus bleiben lesbar.

### 2026-11-01 – Recorder-App-Start ist ein exklusiver Audio-Lebenszyklus

- Roberts Formulierung „wenn die App startet“ ist wörtlich und nicht nur als
  späterer Dienstwechsel zu verstehen: Wird `Dyktafon` beziehungsweise
  `Sprachaufzeichnung` beim Prozessstart als zuletzt verwendete Geräteansicht
  wiederhergestellt, muss derselbe exklusive Entry-Lebenszyklus laufen wie bei
  einer manuellen Navigation in den Recorder.
- Der Start-Lebenszyklus wird synchron ausgeführt, bevor Webserver,
  Boot-Wartephase oder das erste Recorder-Bild fortfahren. BrandMeister,
  Ambient-Grundton und -Zusatzlagen, gemeinsamer mpv-Player und
  Radio-Ringspeicher müssen zu diesem Zeitpunkt bereits gestoppt sein.
- Eine bloße Wiederherstellung der sichtbaren `REC`-Ansicht ohne
  `voice_recorder_open` ist unzulässig. Sie führte real zu `service=REC` bei
  gleichzeitigem `active_service=brandmeister` und hörbarem DMR nach einem
  Neustart. Der einmalige Startpfad und der spätere Navigationspfad verwenden
  deshalb dieselbe vorhandene Recorder-Entry-Aktion; der Start darf sie nicht
  bei jedem Render-Refresh erneut auslösen.

### 2026-11-01 – PTT-Aufnahmeflanken sind der zeitkritische Recorderpfad

- Der reale Whisplay-Test zeigt ungefähr zwei Sekunden Verzögerung zwischen
  gedrücktem Hardware-PTT und beginnender Mikrofonaufnahme. Das ist für den
  Sprachrecorder unzulässig. Die physische BCM17-Druckflanke muss den bereits
  vorhandenen Aufnahmeprozess unmittelbar starten; Dateizusammenbau,
  Transkodierung, Indexierung und Displayarbeit dürfen diesen kritischen Pfad
  nicht verzögern.
- Die BCM17-Loslassflanke beendet beziehungsweise pausiert die laufende
  Mikrofonaufnahme ebenso unmittelbar. Erst nachdem der Capture-Prozess sicher
  kein weiteres Sample schreibt, dürfen Segmentzusammenbau und sonstige
  Nacharbeiten erfolgen. Diese Nacharbeiten dürfen weder die nächste
  Eingabeflanke noch das sichtbare Ende der Aufnahme blockieren.
- Die Doppelklick-Erkennung darf eine normale gehaltene Aufnahme nicht
  verzögern und insbesondere keine Loslassflanke unterdrücken. Ein erster
  normaler Druck startet sofort und sein Loslassen stoppt sofort; ein möglicher
  zweiter Druck kann danach den Dauerbetrieb auslösen.
- Die Recorder-Timeline besitzt immer einen sichtbaren Playhead. Er wird als
  weißer vertikaler Strich mit mindestens zwei Pixeln Breite nach allen
  Wellenformelementen gezeichnet und liegt dadurch sichtbar über der Spur.
  Nach dem Pausieren steht er an der tatsächlichen Aufnahme-/Cursorposition;
  der rechte Druck kann die Wiedergabe genau dort starten.
- Während echter Recorder-Wiedergabe ist der zentrale Glow grün und der weiße
  Playhead folgt der von mpv gemeldeten Audioposition im flüssigen Recorder-
  Takt. Pausieren hält ihn an der exakten Position; eine bloß angenommene oder
  nur optisch weiterlaufende Zeit ist unzulässig.
- Während der Recorder sichtbar ist, wird die Timeline flüssig in einem
  eigenen begrenzten Takt aktualisiert. Audioaufnahme und beide PTT-Flanken
  haben dennoch absolute Priorität vor Vollbild-SPI, Telemetrie, Netz- und
  Bildarbeit. Ein PTT-Ereignis stößt deshalb keinen synchronen vollständigen
  Displaytransfer an. Sein roter beziehungsweise wieder normaler Glow wird
  sofort über eine priorisierte kleine ST7789-Teilflächenaktualisierung
  sichtbar; die reguläre Timeline darf danach nachziehen.
- Auf dem verifizierten vierkernigen Pi Zero 2 W wird ein CPU-Kern für den
  Hardware-Eingabeworker und ein weiterer Kern für UI-Renderer, SPI und die
  Live-Wellenform reserviert. BCM17 und die später vermessenen Encoder
  verwenden den Eingabepfad; Web, Telemetrie, Audio- und Dateiarbeit verwenden
  die beiden übrigen Hintergrundkerne. Ein vom Eingabethread gestarteter
  ffmpeg-/mpv-Prozess und dessen Pegelauswertung werden ausdrücklich wieder
  auf die Hintergrundkerne gesetzt, damit sie weder Eingabe noch UI durch
  geerbte Affinität belasten.
  Auf nicht verifizierten Plattformen oder mit weniger als vier CPUs wird
  keine Affinität erzwungen.

### 2026-11-01 – Webupdate wartet auf den realen langsamen Erststart

- Beim realen Update auf 0.10.69 wurde der Release korrekt installiert. Der
  erste Dienststart traf jedoch einmalig auf eine nicht schreibbare SQLite-
  WAL-/Sidecar-Grenze und der automatische systemd-Neustart stellte den Dienst
  erst nach Ablauf des zu kurzen Installer-Healthchecks bereit. Dadurch blieb
  das Update fälschlich auf `failed`, obwohl anschließend 0.10.69 aktiv war.
- Der einzige Installer repariert vor dem Dienststart ausschließlich Besitzer
  und Modus der festen SQLite-Datei sowie ihrer beiden festen WAL-/SHM-
  Sidecars; Medien- und Benutzerverzeichnisse werden weiterhin nicht rekursiv
  verändert. Symlinks und andere Dateitypen werden nicht angefasst.
- Der lokale `/healthz`-Check erhält ein ausreichendes begrenztes
  Bereitschaftsfenster für einen einmaligen systemd-Fehlstart plus Neustart.
  Erst ein danach weiterhin nicht erreichbarer Webdienst lässt das Update
  fehlschlagen; ein erfolgreicher später Start darf nicht mehr um wenige
  Sekunden verpasst werden.

### 2026-11-01 – Getrennte Radio-Reiter und erweiterter polnischer Katalog

- Die Browser-Radioseite zeigt keine freie `Direkte Audioquelle` mehr. Die
  echten Aktionen Play/Pause, Stop, `Dieses Lied behalten` und fortlaufende
  Aufnahme bleiben unverändert sichtbar. Das argumentgeprüfte Core-Playback
  bleibt für andere interne Dienste erhalten; entfernt wird ausschließlich die
  verwirrende freie URL-Eingabe dieser Radioseite.
- Die bestehende persistente persönliche Senderliste und der kuratierte
  inaktive Katalog werden im Browser in zwei Reiter getrennt: `Aktive Sender`
  und `Sender hinzufügen`. Suchfeld, Sprachfilter, Kategoriefilter sowie die
  Maske für einen eigenen Sender stehen oberhalb der Reiter und gelten daher
  in beiden Ansichten. Es entstehen keine zweite Datenbank und keine parallele
  Radioverwaltung.
- Ein selbst angelegter Sender ist sofort aktiv, wird am Ende der persönlichen
  Reihenfolge gespeichert und öffnet den Reiter `Aktive Sender`. Wird ein
  kuratierter Katalogsender aktiviert, wird er ebenfalls updatefest ans Ende
  der persönlichen Liste kopiert und der Browser wechselt sofort zum aktiven
  Reiter. Deaktivieren verschiebt einen kuratierten Sender wieder in den
  verfügbaren Katalog; eigene Sender werden wie bisher gelöscht.
- Der zunächst inaktive polnische Katalog erhält `Radio GRA Toruń`, `Polskie
  Radio Dwójka`, `Polskie Radio Trójka`, `Radio 357` und `Radio Nowy Świat`.
  Radio Maryja und andere religiöse Sender werden ausdrücklich nicht
  aufgenommen. Die fünf Streams wurden am realen Pi mit `ffprobe` als
  dekodierbares MP3 beziehungsweise AAC geprüft; offizielle Senderseiten
  dokumentieren die verantwortlichen Player beziehungsweise Direktstreams.

### 2026-11-01 – Kollisionsfreier Recorder-Funktionskopf und grüne Release-Schranke

- Im Funktionskopf der Sprachaufzeichnung heißt die Grenzsprung-Achse nicht
  mehr das unklare `RAND`, sondern eindeutig `MIN/MAX`. Diese mathematisch
  verständliche Kurzform gilt in allen Gerätesprachen.
- Die gelben Recorderwerte `±` für die 0,1-Sekunden-Feinbewegung und `↔` für
  den Sprung zu Minimum/Maximum verwenden links eine gemeinsame feste, weiter
  rechts bei x=90 liegende Wertspalte. Sie dürfen weder `0.1` noch `MIN/MAX` berühren
  oder überlagern und müssen untereinander exakt ausgerichtet bleiben.
- Ein Pi-Update darf nicht mehr als fertig oder freigegeben gelten, solange
  der GitHub-Actions-Lauf des exakt auszuliefernden Commits rot, abgebrochen
  oder noch nicht abgeschlossen ist. Lokale Tests ergänzen diese Schranke,
  ersetzen sie aber nicht. **Ein roter Lauf ist immer Priorität 1:** Die
  arbeitende Codex-Instanz darf die Aufgabe nicht als abgeschlossen melden,
  den Fehler nicht liegen lassen und nicht auf eine spätere Sitzung
  verschieben. Sie muss sofort Logs und fehlgeschlagene Schritte untersuchen,
  die Ursache im Repository beheben, erneut pushen und diesen Zyklus so lange
  fortsetzen, bis der GitHub-Lauf des neuesten exakten Commits vollständig
  grün ist. Erst danach darf sie den Pi aktualisieren. Der Pi erhält weiterhin
  ausschließlich das feste GitHub-Archiv über `bootstrap.sh`; direkte
  Quellcodeänderungen unter `/opt/openr4d10` oder an installierten Helfern sind
  verboten.

### 2026-11-01 – Recorder-Cursor und Livebild ohne Eingabestau

- Eine Messung am realen Pi hat den Fehler eindeutig getrennt: Die eigentliche
  `voice_recorder_seek`-Operation benötigt nur etwa 65–115 ms, derselbe Schritt
  über den gemeinsamen Browser-/Encoderpfad benötigte dagegen 1,86–2,55 s pro
  Rastung. Mehrere Browserereignisse stauten sich dadurch auf ungefähr fünf
  Sekunden. Ursache war nicht die Vierkern-Affinität, sondern zwei synchrone
  Vollbildtransfers einschließlich normaler Telemetrie pro semantischem
  Recorderereignis sowie die bisherige Python-Pixel-Schleife für RGB565.
- Recorder-Positions-, Grenz- und Play/Pause-Ereignisse dürfen die bereits vom
  Dienst aufgelöste Aktion nur einmal in den nativen Zustand übernehmen und
  einmal zeichnen. Der Recorder-Schnellpfad verwendet die bereits vorhandenen
  Telemetrie-Caches; WLAN-, Batterie- und Systemabfragen gehören nicht in eine
  Cursorflanke. Ein vorläufiges `DeviceUiState.apply()` mit anschließendem
  zweiten Vollbild ist in diesem Pfad verboten.
- Die RGB565-Wandlung bleibt exakt big-endian, verwendet aber ausschließlich
  vektorisierte Pillow-Kanaloperationen statt einer Python-Schleife über 67.200
  Pixel. Auf dem realen Zero 2 W sank die isoliert gemessene Wandlung damit von
  ungefähr 299 ms auf ungefähr 11 ms pro Vollbild.
- Der 10-Hz-Recorder-Takt ist ein fester Zielzeitpunkt und keine zusätzliche
  Pause von 100 ms nach dem Zeichnen. Renderzeit wird vom nächsten Intervall
  abgezogen. Die physische Ansicht bleibt auf UI-Kern 2; die Kernzuordnung wird
  nicht aufgehoben, weil sie den gemessenen Stau nicht verursacht hat.
- Die Browser-Liveansicht darf den schweren Gesamtstatus weiterhin nur im
  normalen Takt laden, fragt im sichtbaren Recorder aber das gecachte native
  Bild begrenzt mit höchstens 10 Hz ab. Der Displayadapter hält das zuletzt tatsächlich
  gezeichnete Bild vor; `/api/device-screen.png` darf deshalb nicht für jede
  Browserabfrage nochmals die komplette Oberfläche rendern oder den SPI-Pfad
  blockieren. Gleichzeitige Bildanfragen werden im Browser nicht gestapelt.

### 2026-11-01 – Harte Echtzeitnähe für jede Benutzereingabe

- Das physische Display benötigt und erhält höchstens zehn normale Vollbilder
  pro Sekunde. Zwischen den Startzeitpunkten zweier normaler Panelbilder liegen
  mindestens 100 ms. Der Recorder nutzt für die laufende Timeline höchstens 10 Hz;
  häufiger wird nur die bereits definierte kleine priorisierte PTT-Glow-
  Teilfläche übertragen.
- Jede Encoder-, Tasten- und Browserinteraktion muss sich wie ein direktes
  Gerät anfühlen. Zielwert von Eingabe bis sichtbare Reaktion sind 100 ms;
  300 ms oder mehr gelten als Release-blockierender Performancefehler. Eine
  Funktion ist nicht releasefähig, wenn sie alte Eingaben sichtbar abarbeitet,
  das Display hängen lässt oder den aktuellen Bedienwunsch hinter einem
  Rückstau versteckt.
- Wiederholte Browser-Rotationsereignisse werden in Reihenfolge gesammelt und
  benachbarte Schritte derselben Achse bis zur API-Grenze zusammengefasst.
  Es dürfen weder parallele HTTP-Threads noch einzelne Vollbilder pro
  Betriebssystem-Keyrepeat auflaufen. Das ist Coalescing, kein Verlust des
  resultierenden Drehwegs.
- Statische Renderressourcen werden wiederverwendet: TrueType-Fonts und
  quantisierte Glow-Layer werden gecacht, das native Vorschaubild verwendet
  den letzten tatsächlich dargestellten Frame und die RGB565-Wandlung bleibt
  vektorisiert. Neue Dienste dürfen diese gemeinsamen Pfade nicht umgehen.
- Vor jedem Release sind Eingabe-, Renderer-, SPI- und Browserpfad getrennt am
  realen Pi zu messen. Wird eine vermeidbare Schwachstelle gefunden, ist sie
  vor der Freigabe zu beseitigen; zusätzliche CPU-Kerne rechtfertigen niemals
  blockierende Arbeit im Eingabepfad.
- Die Messung von 0.10.74 zeigte bei einer Folge schneller Recorder-Schritte
  zunächst 103–170 ms, durch Konkurrenz mit der periodischen 10-Hz-Timeline
  später jedoch erneut 325–465 ms. Daher haben Eingabeframes Vorrang vor
  periodischen Recorderframes: Solange Encoder, Taste oder Browserbedienung
  aktiv nachlaufen, setzt ausschließlich der entbehrliche Timeline-Refresh
  kurz aus. Nach 200 ms Eingaberuhe läuft er automatisch weiter. Die
  resultierende Position selbst und das Eingabeframe werden niemals verworfen.
- Eine weitere reale Messung zeigte für den Wechsel in `REC` ungefähr 528 ms.
  Ursache war erneut ein vermeidbares Zwischenbild: Die Dienstachse zeichnete
  zuerst den noch nicht aufgelösten UI-Zustand und nach Dienst-Eintritt oder
  -Austritt ein zweites Vollbild. Dienstwechsel ändern deshalb den geordneten
  Displayzustand unter Lock ohne SPI-Transfer, führen danach die vorhandene
  Lifecycle-Aktion aus und zeichnen genau ein endgültiges Bild mit gecachter
  Telemetrie. Eintritt und Austritt sind am Pi getrennt gegen die 300-ms-Grenze
  zu messen.
- Debouncing und Coalescing dürfen Eingabedruck begrenzen, aber niemals den
  resultierenden Drehweg, die Reihenfolge oder eine PTT-Flanke verlieren. Sie
  sind Rückstauschutz und kein Ersatz für einen schnellen aufgelösten Pfad.
- Die reale Pfadtrennung nach 0.10.76 ergab 30 vollständige lokale
  Recorderbefehle einschließlich Display mit stabilen 79–89 ms, während der
  LAN-Test einzelne höhere Werte zeigte. Der Webserver verwendete noch
  HTTP/1.0 und erzeugte damit pro Kleinstbefehl unnötig neue Verbindungen.
  Browsersteuerung nutzt deshalb persistentes HTTP/1.1, `Content-Length` und
  `TCP_NODELAY`; kalten Verbindungsaufbau und warme Bedienlatenz immer getrennt
  messen.
- Der reale 0.10.77-Abnahmelauf auf dem Pi bestand: 50 warme Recorderbefehle
  über eine einzige LAN-Verbindung benötigten 86,8–178,4 ms bei 110 ms Mittel,
  kein Wert lag bei 200 ms oder höher. Zehn vollständige Dienstwechsel lagen
  bei 101,8–232,8 ms, kein Wert erreichte die blockierende 300-ms-Grenze. Der
  lokale Pi-Pfad blieb bei 30 Wiederholungen zwischen 79 und 89 ms. Während der
  Messung meldete die Firmware `throttled=0x0`; die installierten Laufzeitdateien
  stimmten SHA-256-genau mit dem grünen GitHub-Commit überein.

### 2026-11-01 – Beide Radio-Unterreiter bleiben sichtbar

- Die beiden Browser-Unterreiter `Aktive Sender` und `Sender hinzufügen`
  bleiben unabhängig von der aktuellen Auswahl immer gleichzeitig sichtbar.
  Der aktive Reiter wird durch Akzentfarbe, Kontrast und den vorhandenen
  Auswahlzustand hervorgehoben, aber weder ausgeblendet noch so dunkel
  dargestellt, dass seine Beschriftung verschwindet. Der inaktive Reiter
  bleibt klar lesbar und direkt anklickbar.

### 2026-11-01 – Playhead folgt der Sprachwiedergabe sichtbar

- Beim Start der Wiedergabe in `Sprachaufzeichnung` muss die Arbeitsdatei
  atomar an der aktuell sichtbaren Cursorposition geladen werden. Ein
  asynchrones `loadfile` mit unmittelbar folgendem separatem `seek` ist
  verboten: mpv kann diesen Sprung vor `file-loaded` ablehnen, obwohl der Ton
  bereits beginnt; OpenR4d10 würde dann den Player fälschlich als inaktiv
  behandeln und der weiße Playhead bliebe stehen.
- Während der Wiedergabe übernimmt der bestehende 10-Hz-Recorderpfad die reale
  mpv-Position in denselben weißen, zwei Pixel breiten Playhead. Es gibt keinen
  zweiten simulierten Browser-Timer. Pause und Stopp frieren und persistieren
  die zuletzt tatsächlich gemeldete Position.
- Die laufenden 100-ms-Positionsupdates sind flüchtiger Anzeigezustand und
  dürfen nicht zehnmal pro Sekunde `edit.json` auf die SD-Karte schreiben.
  Persistiert wird an semantischen Grenzen wie Pause, Stopp oder manueller
  Positionsänderung. Tests müssen den atomaren Ladebefehl sowie mehrere
  aufeinanderfolgende, sichtbar ansteigende Wiedergabepositionen abdecken.

### 2026-11-01 – Recorder-Playhead und ALSA sind eine untrennbare Wahrheit

- Ein angenommener mpv-Steuerbefehl ist noch kein erfolgreicher Wiedergabestart.
  `PLAY`, grüner Glow, `audio_active` und ein bewegter Recorder-Playhead dürfen
  erst aktiv werden, wenn mpv die lokale Datei tatsächlich geladen und die
  Audioausgabe gestartet hat. Ein verspätetes `end-file`/`file_error` darf
  niemals als laufende Wiedergabe erscheinen.
- Der weiße Recorder-Playhead folgt ausschließlich der realen mpv-Zeitposition
  eines aktiven Audioausgangs. Gibt es keine reale Position beziehungsweise
  endet oder scheitert die Audioausgabe, bleibt der Cursor stehen, der
  Wiedergabezustand wird beendet und der Glow darf nicht grün bleiben. Eine
  simulierte Zeitachse unabhängig von ALSA ist ausdrücklich verboten.
- Der reale Gegencheck auf dem Whisplay muss vor Freigabe beide Seiten
  gleichzeitig beweisen: `/proc/asound/card0/pcm0p/sub0/status` meldet während
  der Recorderwiedergabe `RUNNING`, und der vom selben mpv-Prozess gelesene
  Playhead steigt im 10-Hz-Takt. Ein bewegter Playhead allein ist keine
  Abnahme. Radio auf demselben zentralen Player öffnet den Whisplay-ALSA-Pfad
  bereits korrekt; eine Abweichung ist deshalb im Recorder-Datei-/Ladepfad zu
  beheben und nicht mit einem zweiten Player zu umgehen.
- Die reale Abnahme von 0.10.80 zeigte zusätzlich, dass mpv globale
  Wiedergabeeigenschaften dienstübergreifend beibehält: `pause=yes` aus einer
  vorherigen Wiedergabe kann eine neu geladene Sprachaufnahme bei 0,0 Sekunden
  festhalten, und `loop-playlist=inf` aus AmbientR4D10 kann dieselbe Aufnahme
  nach dem Ende ungewollt wieder von vorn starten. Vor jedem Einzeldatei-Load
  werden daher die echten mpv-Eigenschaften `pause=no` und
  `loop-playlist=no` gesetzt. Interne Python-Flags allein reichen nicht; sie
  dürfen niemals vom tatsächlichen mpv-Zustand abweichen.
- Eine weitere reale 0.10.81-Messung trennte interne Dauer und tatsächlich
  dekodierbare Dauer: Mehrere einzeln abgeschlossene MP3-Segmente dürfen nicht
  als rohe Bytes aneinandergehängt werden. Dabei kann der Decoder bereits am
  ersten Segment Dateiende melden, obwohl der Recorder die Summe aller
  Segmentdauern anzeigt. Append und Crash-Recovery verwenden deshalb den
  vorhandenen ffmpeg-Prozessrand mit dem Concat-Demuxer und Stream-Copy; das
  Ergebnis ist eine einzige zusammenhängend dekodierbare MP3. Rohes
  Byte-Anhängen von Sprachsegmenten ist verboten.

### 2026-11-01 – Recorder-Play am Dateiende startet wieder von vorn

- Nach einer Aufnahme steht der sichtbare Recorder-Cursor absichtlich exakt am
  Ende der Arbeitsdatei. Ein rechter Kurzdruck beziehungsweise Enter darf diese
  Endposition nicht als mpv-Startzeit übernehmen, weil die Datei dann sofort
  EOF erreicht und kein Ton hörbar wird.
- Startet der Benutzer die Wiedergabe bei `position_ms >= duration_ms` und ist
  die Aufnahme nicht leer, setzt derselbe vorhandene Recorderpfad den Cursor
  zuerst persistent auf 0 und lädt anschließend dieselbe Arbeitsdatei atomar
  ab dem Anfang. An jeder echten Position vor dem Ende wird weiterhin genau ab
  dem sichtbaren Cursor abgespielt.
- Diese Rückkehr zum Anfang ist kein Loop: Nach dem nächsten natürlichen
  Dateiende bleibt die Wiedergabe wie bisher beendet. Erneutes Enter startet
  nur auf ausdrücklichen Benutzerwunsch wieder bei 0.

### 2026-11-01 – DMR-Länderauswahl öffnet bereits beim Halten

- Im normalen DMR-Bild startet die vorhandene PTT-Druckflanke genau einen
  abbrechbaren Zwei-Sekunden-Timer. Erreicht der Druck diese Schwelle, öffnet
  die vorhandene Länderauswahl sofort sichtbar, während der reale
  Whisplay-Taster beziehungsweise Backspace noch gehalten wird. Der Benutzer
  muss nicht raten, wann er loslassen darf.
- Loslassen nach der ausgelösten Schwelle wird verbraucht: Es darf weder eine
  Talkgroup umschalten noch das soeben geöffnete Menü wieder schließen. Ein
  Loslassen vor der Schwelle bricht den Timer ab und behält die bestehende
  Kurzdruckfunktion zum Umschalten der markierten Talkgroup.
- Timer, Hardwaretaste und Browser-Simulation laufen weiterhin durch denselben
  serialisierten Eingabepfad. Eine zweite GPIO-Auswertung oder ein paralleler
  DMR-Menüzustand ist verboten.

### 2026-11-01 – DMR-Menüzähler bleibt außerhalb der Zurück-Taste

- Der Positionszähler einer Menüliste, insbesondere der Ambient-,
  DMR-Länder- und TG-Ersetzungsliste, darf niemals in das rechts angedockte
  PTT-Zurück-Tastenfeld hineinragen. Der sichtbare Button enthält im
  Ruhezustand ausschließlich das gefüllte Pfeil-Icon; `1/5` oder ein anderer
  Listenzähler gehört vollständig links daneben.
- Die zentrale Innenfläche des Zurück-Tastenfelds samt Pfeil wird gegen beide
  DMR-Menütypen getestet. Eine rein textuelle Inhaltsprüfung reicht für diese
  Geometrie-Regression nicht aus.

### 2026-11-01 – DMR-Aus schickt die Markierung zur ersten aktiven TG

- Wird die im Gerätekatalog markierte aktive Talkgroup per PTT ausgeschaltet,
  darf die Markierung der nun deaktivierten Zeile nicht in den inaktiven
  Katalogblock nach unten folgen. Sie springt stattdessen auf die erste noch
  aktive Talkgroup im enabled-first-Block und die Anzeige bleibt oben.
- Diese Cursorbewegung aktiviert keine andere Talkgroup und verändert außer
  der ausdrücklich ausgeschalteten TG kein Abonnement. Bleibt keine aktive TG
  übrig, bleibt die gerade deaktivierte Zeile als deterministischer Fallback
  markiert.

### 2026-11-01 – DMR-Aktivität direkt in sechs Talkgroup-Zeilen

- Robert entfernt die redundante separate Zeile für die momentan sprechende
  Talkgroup aus der normalen BrandMeister-Geräteansicht. Die zugehörige normale
  Talkgroup-Zeile leuchtet während des real empfangenen Rufs stattdessen grün;
  Auswahlrahmen und An/Aus-Zustand bleiben davon unabhängig erkennbar.
- Der gewonnene Platz wird nicht leer gelassen: Das 240-x-280-Display zeigt in
  der normalen DMR-Ansicht sechs kompakte Katalogzeilen. Die Position im
  Gesamtkatalog steht in der markierten Zeile und benötigt keine neue Kopfzeile.
- Der native HoseLine-Empfänger, die persistente Aktivierungsgrenze, Browser-
  Anzeige und Status-API erlauben nun sechs gleichzeitig abonnierte Talkgroups.
  Erst die Aktivierung einer siebten TG öffnet die ausdrückliche Ersetzung; sie
  darf keine der sechs aktiven Gruppen stillschweigend entfernen.

### 2026-11-01 – Whisplay-Ausgang nutzt die kalibrierte Maximalverstärkung

- Die sichtbaren 0–100 Prozent waren bisher der digitale Quellpegel von mpv
  beziehungsweise dem µ-law-Decoder, während der unabhängige Whisplay-Mixer
  nach jedem Hersteller-Warmup fest auf 80 stand. `100 %` im Display war damit
  nicht die maximale physische Ausgangsverstärkung.
- Robert verlangt ausdrücklich die maximal verfügbare Lautstärke. OpenR4d10
  setzt den stabilen ALSA-Regler `speaker` deshalb nach dem Hersteller-Warmup
  auf 100. Laut der eingebundenen, messkalibrierten Herstellerkennlinie ist
  Index 100 die maximale saubere Ausgabe vor Clipping; die Anwendung erhöht
  mpv nicht über 100 Prozent und erzeugt keine zusätzliche digitale
  Übersteuerung.
- Diese Einstellung ist eine feste, versionierte Bootgrenze und kein manueller
  Einmalbefehl auf dem Pi. Ein eigener root-eigener One-Shot wartet begrenzt auf
  `whisplaysound`, setzt ausschließlich `speaker=100` und läuft vor dem
  unprivilegierten OpenR4d10-Dienst. Fehlt die Karte, darf die Hauptanwendung
  weiterhin starten und ihre vorhandene Diagnose melden.

### 2026-11-01 – DMR-Sprecheralias bleibt hinter der technischen Position

- Die technische Katalogposition einer DMR-Zeile bleibt während eines Rufs
  sichtbar und wird niemals durch Rufzeichen, Sprechername oder Talker-Alias
  ersetzt. Der tatsächlich aus HoseLine empfangene Alias steht unmittelbar
  dahinter in der konfigurierten Akzentfarbe; unbekannte Namen werden nicht
  erfunden.
- Der Statuspunkt vor einer momentan sprechenden Talkgroup pulsiert mit zwei
  vollständigen Helligkeitszyklen pro Sekunde zwischen dunklerem und hellerem
  Grün. Die aktive Zeile behält zusätzlich ihren grünen Glow.
- Damit diese Rückmeldung nicht am zweisekündigen Telemetrietakt hängt, läuft
  die sichtbare DMR-Ansicht bei vorhandener gecachter Telemetrie über denselben
  auf 100 Millisekunden begrenzten Interaktions-Zeichenpfad wie der Recorder.
  Das Display bleibt damit bei höchstens 10 FPS; eine zweite GPIO-, Eingabe-
  oder Netzwerkabfrageschleife ist verboten.

### 2026-11-01 – Whisplay-Warmup darf keinen systemd-Bootzyklus erzeugen

- Der reale Neustart nach 0.10.89 hat einen zuvor nur auf echter Hardware
  sichtbaren Ordnungszyklus nachgewiesen: Der Hersteller-Warmup war zugleich
  von `multi-user.target` gewollt und explizit danach angeordnet, während
  `openr4d10-audio-max` auf den Warmup und die Hauptanwendung wiederum auf
  `openr4d10-audio-max` wartete. systemd löschte deshalb die Startjobs für
  Maximalpegel und Hauptanwendung; das Display blieb in der Bootanimation und
  der Herstellerwert 80 aktiv.
- Der vendorte Warmup behält seinen begrenzten Karten-Wartepfad, wird aber nur
  noch nach `sound.target` und `alsa-restore.service` geordnet. Er darf nicht
  `After=multi-user.target` enthalten. Danach setzt der versionierte
  `openr4d10-audio-max` weiterhin 100 und erst danach startet OpenR4d10.
- Ein Installer-Vertragstest muss diese vollständige Kette prüfen und jede
  erneute Warmup-Abhängigkeit von `multi-user.target` ablehnen. Ein grüner CI-
  Stand ohne diese statische Zyklusprüfung reicht nicht als Freigabe.

### 2026-11-01 – ARD und ZDF werden echte öffentliche Mediathekplayer

- `KONFIGURATION NÖTIG` darf bei ARD- und ZDF-Mediathek nicht länger einen
  fehlenden externen Adapter vortäuschen. Beide Angebote sind
  zugangsdatenfreie, native Katalogdienste und werden erst dann als `BEREIT`
  gemeldet, wenn die vorhandene Implementierung Suche, Ergebniswahl und
  Wiedergabe über den einen zentralen `MpvEngine` tatsächlich bereitstellt.
- Der Browser erhält einen eigenen kompakten Reiter `Mediatheken` mit
  Anbieterauswahl, begrenzter Suche, Ergebnisliste sowie Play/Pause/Stopp. Es
  entsteht kein zweiter Medienplayer und kein Kartenraster. Die öffentliche
  Status-API enthält Titel, Sender, Thema, Dauer und Auswahlzustand, aber nie
  die internen Streamadressen.
- Die Suche verwendet die dokumentierte, schlüssellose MediathekViewWeb-
  Abfrage als Index für öffentlich zugängliche Senderinhalte. Ergebniszahl,
  Antwortgröße, Zeitlimit und erlaubte HTTPS-Ziele bleiben strikt begrenzt;
  die Wiedergabe lädt anschließend ausschließlich die vom Index gelieferte
  öffentliche Senderquelle. DRM, Altersfreigaben, Geoblocking, Anmeldung und
  sonstige Zugangssperren werden weder umgangen noch als automatisch
  bestätigt behandelt.
- ARD und ZDF bleiben getrennte Dienstmodule und besitzen jeweils Manifest,
  README und Tests, teilen sich aber genau einen Katalogadapter. Ein explizites
  Play übernimmt wie bei Podcasts den Audioausgang; bloßes Öffnen, Suchen oder
  Markieren einer Folge unterbricht einen bereits laufenden Audiodienst nicht.
- Auf dem Gerät erscheint die ausgewählte Mediathekfolge in der vorhandenen
  `PLAYER`-Ansicht. Titel, Anbieter und Wiedergabestatus stammen aus demselben
  Zustand wie im Browser; Play/Pause/Stopp bleiben die zentralen Aktionen.

### 2026-11-01 – Deutscher Mediathekenkatalog, aktuelle Themen und Browser-Video

- Der vorhandene gemeinsame Mediathekadapter wird erweitert und nicht durch
  einen parallelen Player ersetzt. Neben ARD und ZDF umfasst seine feste,
  geprüfte Senderauswahl die deutschen öffentlich-rechtlichen Informations-,
  Kultur- und Dokumentationsangebote `ZDFinfo`, `ZDFneo`, `3Sat`, `ARTE.DE`,
  `PHOENIX`, `ARD-alpha`, `tagesschau24`, `ONE` sowie BR, HR, MDR, NDR, RBB,
  SR, SWR, WDR und Deutsche Welle (`DW`). Sendernamen werden gegen die tatsächlich vom
  MediathekViewWeb-Index gelieferten Kanalwerte geprüft; eine unscharfe
  Teilzeichenfolge wie `SR`, die auch `SRF` treffen würde, genügt nicht.
- Die Browseransicht erhält eine kompakte Senderauswahl und dynamische
  Themen-Schnellwahlen. Mindestens vorhanden sind `Neu`, `Nachrichten`,
  `Tatort & Krimi`, `Dokus`, `Wissenschaft`, `Terra X`, `Harald Lesch`,
  `Geschichte` und `Natur`. Dies sind nachvollziehbare Suchprofile, keine
  redaktionell erfundenen Empfehlungen. Ergebnisse werden nach dem echten
  Veröffentlichungszeitpunkt absteigend geladen; Titel, Datum, Sender, Thema,
  Beschreibung und Dauer bleiben sichtbar.
- Eine leere Suche bedeutet beim ausgewählten Sender `Neu` und lädt dessen
  aktuelle Einträge. Die senderübergreifende Auswahl ist auf die vorgenannten
  deutschen Kanäle begrenzt. Abrufe bleiben HTTPS-only, größen-, zeit- und
  ergebnisbegrenzt, werden für kurze Zeit pro Suchprofil im Arbeitsspeicher
  wiederverwendet und umgehen weder DRM noch Anmeldung, Altersfreigabe,
  Geoblocking oder andere Zugriffsbeschränkungen.
- `Im Browser ansehen` verwendet das native HTML5-Videoelement und eine kurze
  lokale, undurchsichtige Element-ID. Der Pi leitet den Browser nur zur bereits
  geprüften öffentlichen Senderquelle weiter und proxyt keine großen
  Videodateien durch seinen Arbeitsspeicher. Rohadressen bleiben aus Status,
  SQLite und Backups ausgeschlossen. `Auf Gerät abspielen` verwendet weiterhin
  genau den zentralen `MpvEngine` und eine bandbreitenärmere verfügbare
  Senderfassung.
- Die Ergebniszeile bietet zwei gleichwertige ausdrückliche Geräteaktionen:
  `Audio auf Gerät` startet nur die Tonspur und behält die sparsame Titelansicht;
  `Video auf Gerät` startet Bild und Ton in der vorhandenen `PLAYER`-Ansicht.
  Beide wählen verbindlich zuerst `url_video_low` und nur bei deren Fehlen die
  kleinste noch verfügbare Senderfassung. Im Video-Modus stammen Bild und Ton
  aus demselben zentralen `MpvEngine`; ein zweiter Decoder, ein simulierter
  Video-Timer oder ein nur ungefähr synchron laufender Nebenprozess ist
  verboten. Während Video tatsächlich läuft, darf ausschließlich der
  240-x-175-Pixel-Videobereich mit höchstens 25 FPS als SPI-Teilfläche
  aktualisiert werden. Normale Vollbilder, Kopfzeile, Menüs, Recorder und DMR
  bleiben bei höchstens 10 FPS. Der Videotakt darf weder den vollständigen
  UI-Renderer noch die vollständige 240-x-280-RGB565-Konvertierung aufrufen;
  er skaliert, maskiert, konvertiert und überträgt ausschließlich diese
  Teilfläche. Die
  Einzelbilder werden ausschließlich flüchtig unter `/run/openr4d10` erzeugt,
  sofort in den zentralen Renderer übernommen und niemals als 10-Hz-Schreiblast
  auf der SD-Karte gespeichert. Pause, Fortsetzen, Sprung und Kanalwechsel
  verändern Bild und Ton gemeinsam und behalten den gewählten Audio-/Video-
  Modus. Browser-Video bleibt ein getrennter HTML5-Ausgabeweg.
- Die Umsetzung wird in drei ausdrücklichen Optimierungsrunden abgenommen:
  erstens Quellenabdeckung, Dubletten und aktuelle Inhalte; zweitens kompakte
  Bedienung, verständliche Namen und fünfsprachige Browsertexte; drittens
  Cache, Bandbreite, Fehlerfälle und die bestehende Eingabe-/Audioleistung.
  Freigabe und Pi-Update bleiben an den vollständig grünen GitHub-Lauf des
  exakten Commits gebunden.

### 2026-11-01 – Gerätefokus und Kanalbedienung nach Mediathek-Play

- Ein ausdrückliches `Auf Gerät abspielen` ist neben der Audioübernahme auch
  eine eindeutige Geräteaktion: Nach erfolgreichem Laden wechselt die native
  Whisplay-Ansicht sofort in die vorhandene `PLAYER`-Ansicht und zeigt Sender,
  Titel, Ergebnisposition und Wiedergabestatus. Sie darf nicht in der zuvor
  sichtbaren DMR- oder Wetteransicht verbleiben. Bloßes Suchen, Filtern,
  Markieren oder `Im Browser ansehen` verändert die Geräteansicht weiterhin
  nicht.
- Solange eine Mediathekfolge den zentralen Player besitzt und `PLAYER`
  sichtbar ist, schaltet der rechte äußere Encoder beziehungsweise Pfeil
  hoch/runter zyklisch durch genau die Ergebnisliste und Suchauswahl, aus der
  die laufende Folge gestartet wurde. Der neu gewählte Beitrag wird unmittelbar
  über denselben `MpvEngine` geladen; es entsteht kein zweiter Player und keine
  zweite Ergebnisliste.
- Ein kurzer rechter Druck beziehungsweise Enter pausiert oder setzt die reale
  Mediathek-Wiedergabe fort. Die Geräte-Kanalnummer entspricht der sichtbaren
  einsbasierten Position in der aktiven Ergebnisliste. Die Bedienung muss
  weiterhin über denselben serialisierten Eingabe- und Ein-Frame-Pfad laufen.

### 2026-11-01 – Ein alter DMR-Frame darf die Dienstwahl nicht zurücksetzen

- Die Beobachtung, dass Links/Rechts kurz einen anderen Dienst zeigt und danach
  wieder DMR erscheint, ist kein gewünschtes Folgen des aktiven Audiobesitzers.
  Sie entsteht, wenn der 10-Hz-DMR-Refresh seine Ansicht bereits vor der
  Eingabe aufgelöst hat, aber erst nach dem fertigen Eingabeframe veröffentlicht.
- Jeder periodische Frame erhält deshalb die Interaktionsgeneration, mit der er
  begonnen wurde. Beginnt oder endet während seiner Auflösung eine Geräte- oder
  Browserinteraktion, wird ausschließlich dieser alte periodische Frame
  verworfen. Das von der Eingabe angeforderte Endbild wird niemals verworfen.
- DMR oder ein anderer Audiowner darf nach dem Dienstwechsel weiter im
  Hintergrund laufen, aber weder `DeviceUiState.service` noch die sichtbare
  Ansicht zurücksetzen. Diese Sperre gilt für alle periodischen Dienstframes,
  nicht nur als DMR-Sonderfall.

### 2026-11-01 – Mediathekvideo auf dem Whisplay in Minimalauflösung

- Robert verlangt für Mediathekinhalte ausdrücklich beide Gerätewege. Jede
  Ergebniszeile bietet `Audio auf Gerät` für die sparsame Tonwiedergabe mit
  Titelansicht und `Video auf Gerät` für echtes Video plus Ton auf dem
  physischen Whisplay. Keine der beiden Möglichkeiten darf die andere ersetzen.
- `Audio auf Gerät` deaktiviert im zentralen mpv die Videospur tatsächlich mit
  `vid=no`; bloß kein Bild zu zeichnen, während mpv weiter Video dekodiert, ist
  kein Audiomodus. `Video auf Gerät` setzt für genau diesen Ladeweg `vid=auto`.
  Radio, Podcasts, Ambient und sonstige Audioquellen bleiben standardmäßig
  videodeaktiviert.
- Der bereits vorhandene Qualitätsvorrang bleibt hart: `url_video_low` wird
  immer vor `url_video` und `url_video_hd` gewählt. Ist die Low-Fassung nicht
  vorhanden, wird ausschließlich die kleinste vom Index noch angebotene
  Fassung verwendet; OpenR4d10 darf für das 240-x-280-Panel nie absichtlich HD
  bevorzugen.
- Der eine zentrale mpv-Prozess bleibt alleinige Wiedergabe- und Zeitquelle.
  Er dekodiert Video mit audio-geführter Synchronität und liefert höchstens
  zehnmal pro Sekunde einen Software-Screenshot des aktuell wirklich
  wiedergegebenen Frames. Es gibt keinen zweiten ffmpeg-/mpv-Player und keinen
  unabhängigen Bild-Playhead.
- Der Bildaustausch benutzt genau eine flüchtige, überschriebene JPEG-Datei pro
  laufendem Capture unter `/run/openr4d10`. Sie wird begrenzt gelesen und sofort
  entfernt; `/var/lib/openr4d10`, SQLite und die SD-Medienablage erhalten keine
  Videoframes. Fehlt oder verspätet sich ein Frame, bleibt das letzte gültige
  Bild stehen, ohne Ton oder Eingabe zu blockieren.
- `PLAYER` erhält bei tatsächlich laufendem Video einen eigenen 40-ms-Takt für
  ausschließlich den Medienbereich; der normale 100-ms-Vollbildpfad von
  Recorder, DMR und übriger UI bleibt unverändert. Pause behält den letzten
  Frame ohne weitere Videoneuzeichnung. Der
  gewählte Audio-/Video-Modus bleibt auch beim Kanalwechsel derselben
  Ergebnisliste erhalten. Screenshot-Anforderungen werden
  ohne Warten in die bestehende mpv-IPC gestellt, damit Play/Pause, Encoder und
  Dienstwechsel weiterhin Vorrang haben. Vor Freigabe müssen auf dem realen Pi
  A/V-Synchronität, höchstens 25 Videoteilflächen-FPS, weiterhin höchstens 10
  normale Vollbilder pro Sekunde, Eingabelatenz und fehlende dauerhafte
  Frame-Dateien geprüft werden; der exakte Commit benötigt danach vollständig
  grünes GitHub Actions.
- Die zu jeder Screenshot-Anforderung eintreffende mpv-IPC-Antwort wird
  begrenzt und nicht blockierend aus demselben privaten Socket entfernt. Sie
  darf sich bei langer Videowiedergabe niemals bis zu einem vollen Socket-
  Puffer ansammeln und dadurch spätere Nutzereingaben verzögern.
- Jede bereits im Dienstkern aufgelöste Medienaktion – insbesondere
  Play/Pause, Lautstärke und Kanalwechsel – verändert die geordnete UI zunächst
  nur zustandsseitig. Erst danach wird genau ein endgültiges Vollbild
  übertragen. Ein zusätzliches, bereits überholtes Vorab-Bild verdoppelt auf
  dem realen SPI-Panel die Eingabelatenz und ist verboten.
- Das eine endgültige Interaktionsbild verwendet die zuletzt gecachte
  Empfänger-, WLAN-, Batterie- und Systemtelemetrie. Eine Play/Pause-, Kanal-
  oder Lautstärketaste darf niemals erst synchrone `nmcli`-, I2C- oder andere
  normale Telemetrieabfragen ausführen; diese bleiben im periodischen
  Hintergrundpfad.
- Raspberry Pi OS Trixie liefert auf dem realen Zielgerät mpv 0.40. Dessen
  `--video`-Schalter akzeptiert `auto`, `no` oder eine Spur-ID, aber nicht
  `yes`. Der zentrale Player muss deshalb `--video=auto` verwenden; ein
  Vertragstest verbietet das syntaktisch naheliegende, auf dem Pi aber fatal
  ungültige `--video=yes`. Diese Zielsyntax ist vor jeder Freigabe zusätzlich
  mit dem wirklich installierten mpv zu prüfen.

### 2026-11-01 – Verspätete mpv-Endereignisse dürfen neue Medien nicht stoppen

- Beim Ersetzen einer bereits laufenden Mediathekquelle kann mpv das
  `end-file`-Ereignis der alten Playlistposition erst ausliefern, nachdem die
  neue Position schon gestartet wurde. Dieses verspätete Ereignis darf weder
  den neuen Python-Wiedergabezustand auf `stopped` setzen noch den 25-FPS-
  Videopfad abschalten, während Bild und Ton real weiterlaufen.
- Der zentrale `MpvEngine` verfolgt deshalb die von mpv gelieferten
  `playlist_entry_id`-Werte aus `start-file` und `end-file`. Nur ein
  Endereignis der aktuellsten gestarteten Playlistposition darf den sichtbaren
  Wiedergabezustand beenden; ein Endereignis einer ersetzten älteren Position
  wird als veraltet verworfen. Auf dem realen mpv 0.40 trifft die erfolgreiche
  `loadfile`-Antwort mit der neuen `playlist_entry_id` vor dem alten
  `end-file` und dem neuen `start-file` ein. Deshalb übernimmt der Player die
  neue ID bereits aus dieser Antwort; erst auf `start-file` zu warten ist zu
  spät. `start-file` stellt den Zustand zusätzlich verbindlich auf `playing`,
  falls die beiden asynchronen Ereignisse erst nach Rückkehr des Ladebefehls
  verarbeitet werden. Für ältere Testdoubles ohne ID bleibt das bisherige
  Verhalten erhalten.
- Ein Regressionstest muss die reale Reihenfolge „neuer Start, danach altes
  Ende“ abbilden und beweisen, dass der neue Stream weiter als `playing`
  gemeldet wird. Die Abnahme auf dem Pi muss anschließend Status,
  Bildbewegung und laufende ALSA-Ausgabe gemeinsam prüfen.

### 2026-11-01 – Mediathekvideo nutzt die volle untere Displayfläche

- Ausschließlich ein tatsächlich aktives Mediathekvideo ist eine bewusste
  Ausnahme von den allgemeinen Medienrändern und Medienrundungen. Unterhalb
  des Metadatenbereichs beginnt seine Teilfläche bei y=105, verwendet die
  komplette Displaybreite von 240 Pixeln und reicht ohne Seiten- oder
  Unterrand bis einschließlich zur letzten Displayzeile y=279.
- Das Video füllt diese 240-x-175-Pixel-Fläche vollständig. Dafür ist ein
  mittiger Zuschnitt zulässig und jetzt ausdrücklich gewünscht; die ältere
  Letterbox-/`contain`-Vorgabe ohne Zuschnitt ist für Mediathekvideo aufgehoben.
  Radio-Logos, Wetterbilder, Kameras, Ambientgrafiken und andere Medien behalten
  ihre bisherigen engen Ränder, Masken und Rundungen unverändert.
- Vollbildrenderer und schneller 25-FPS-Teilupdatepfad müssen exakt dieselben
  Koordinaten und dieselbe `fit`-Skalierung verwenden. Ein Regressionstest muss
  Video an x=0, x=239 und y=279 nachweisen und gleichzeitig belegen, dass der
  normale Radio-Medienrand weiterhin besteht.
