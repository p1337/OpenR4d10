# ARD Mediathek

Dieses Modul durchsucht öffentlich zugängliche ARD-Inhalte über den begrenzten
MediathekViewWeb-Index und übergibt die gewählte Senderquelle an den zentralen
OpenR4d10-Player. Es benötigt weder Konto noch Zugangsdaten.

Die Ergebnisliste enthält keine Streamadressen. Suche und Antwortgröße sind
begrenzt; DRM, Geoblocking und Altersfreigaben werden nicht umgangen.

Im Browser kann ein gewählter Beitrag über eine undurchsichtige lokale ID im
HTML5-Videoplayer angesehen werden; der Pi leitet nur zur geprüften öffentlichen
Quelle weiter. `Audio auf Gerät` und `Video auf Gerät` verwenden beide die
kleinste verfügbare Senderfassung und denselben zentralen mpv-Prozess wie Radio
und Podcasts. Nur der Video-Modus übergibt dessen synchrones aktuelles Bild mit
höchstens 25 FPS als begrenztes Teilflächenupdate an das Whisplay; normale
Vollbilder bleiben bei 10 FPS. Der vollständige Senderkatalog und seine
Grenzen stehen in `docs/MEDIATHEK.md`.

Der zentrale Geräteplayer unterstützt einen entprellten Suchlauf ausschließlich
über den unteren linken Encoder, echten mpv-Pufferfortschritt sowie den
gemeinsamen persistenten Verlauf und Favoritenstellen aller Mediatheken.
## Gerätegruppen

Im noch inaktiven `PLAYER` ist die lokalisierte Favoriten-/Suchgruppenauswahl
sofort sichtbar und mit rechtem Encoder plus Druck bedienbar. PTT-lang öffnet
dieselbe Auswahl nur zusätzlich als Schnellzugriff. Die nicht blockierende
Auswahl startet anschließend ein zufälliges Video niedriger Auflösung über den
zentralen Player.

PTT-lang pausiert eine laufende Wiedergabe vor dem Öffnen der Liste. Derselbe
noch gehaltene Tastendruck wird bis zum Loslassen verbraucht und kann die Liste
nicht als Zurück-Eingabe wieder schließen.
