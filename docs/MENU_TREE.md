# Interne Menübaum- und Navigationsübersicht

Diese Datei ist ausschließlich eine Debug-/Entwicklerübersicht für Robert und
die Implementierung. Sie ist weder Produktseite noch sichtbarer Menüpunkt.

```text
Normalansicht
├─ RADIO
│  ├─ Senderliste (CH / äußerer rechter Encoder)
│  ├─ Play/Pause (rechter Klick / Enter)
│  └─ aktuelles Lied behalten (PTT / Browser: Backspace)
├─ WEATHER
│  ├─ Regenradar Deutschland
│  ├─ Satellit Deutschland
│  └─ Europa
├─ PLAYER
│  ├─ Aufnahmen
│  ├─ Favoriten
│  ├─ Mein Soundmix (Favoriten, Shuffle, Endlosschleife)
│  └─ alle Aufnahmen (Shuffle)
├─ DMR
├─ REC
└─ SYSTEM (reine Statusansicht; keine Mediengrafik, kein Play)

Hauptmenü (linker Klick / Leertaste)
├─ Anzeige
├─ Akzentfarbe
├─ WLAN
├─ Dienstmodule
├─ Dienst-Store
├─ Bluetooth
├─ Eingabe & Sprache
├─ Sprache
├─ System
└─ Informationen & Support

Navigation
├─ rechter äußerer Encoder / Pfeil hoch-runter: Eintrag oder Kanal
├─ rechter Klick / Enter: auswählen
├─ PTT / Backspace: eine Ebene zurück
├─ linker äußerer Encoder / W-S: Lautstärke in 10-%-Schritten
├─ linker innerer Encoder / A-D: Squelch
└─ rechter innerer Encoder / Pfeil links-rechts: Dienst wechseln
```

Audio läuft bei einem Wechsel zu einer visuellen Ansicht weiter. Erst `Play`
auf einer anderen Audioquelle ersetzt die aktuelle Quelle. Die zuletzt
verwendete sinnvolle Dienstansicht wird gespeichert; `SYSTEM` wird nicht als
künstliche Medienansicht verwendet.
