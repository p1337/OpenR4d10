# Deutsche öffentliche Mediatheken

Dieses Modul erweitert den gemeinsamen, begrenzten MediathekViewWeb-Katalog um
deutsche Informations-, Kultur-, Dokumentations- und Regionalangebote. Es
umfasst ZDFinfo, ZDFneo, 3sat, ARTE, phoenix, ARD alpha, tagesschau24, ONE sowie
BR, HR, MDR, NDR, rbb, SR, SWR, WDR und Deutsche Welle. ARD und ZDF behalten ihre eigenen
Module; Suche und Wiedergabe verwenden trotzdem denselben Adapter und Player.

Die Browseransicht kann eine geprüfte öffentliche Videoquelle über eine
prozesslokale, undurchsichtige Element-ID direkt öffnen. Der Raspberry Pi
proxyt die große Videodatei nicht. Auf dem Gerät stehen getrennt Audio und
Video bereit. Beide verwenden die kleinste Senderfassung und den zentralen
`MpvEngine`; im Video-Modus stammt das Whisplaybild synchron aus genau diesem
Prozess. Nur sein Medienbereich darf als Teilflächenupdate bis 25 FPS laufen;
normale Vollbilder bleiben auf 10 FPS begrenzt. Zugangsdaten, Stream-URLs und Website-
URLs werden weder in SQLite noch im öffentlichen Status oder in Backups
gespeichert. DRM, Anmeldung, Altersfreigabe und Geoblocking werden nicht
umgangen.

Diagnose: Dienstbereitschaft erfordert das vorhandene `mpv`; Katalogfehler
erscheinen als begrenzte Suchfehlermeldung. Die Quelle, Senderwerte, Limits und
Browser-/Gerätegrenze sind in `docs/MEDIATHEK.md` dokumentiert.

Der zentrale Geräteplayer unterstützt einen entprellten Suchlauf ausschließlich
über den unteren linken Encoder, echten mpv-Pufferfortschritt sowie den
gemeinsamen persistenten Verlauf und Favoritenstellen aller Mediatheken.
## Device groups

Hold the physical Whisplay PTT button for two seconds in PLAYER to open the
localized Favorites/search-group picker. Selection is non-blocking and starts
a random low-resolution video through the central player when ready.
