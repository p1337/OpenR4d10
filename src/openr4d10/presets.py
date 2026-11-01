"""Curated, reviewable radio and feed presets with no credentials."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class RadioPreset:
    preset_id: str
    name: str
    country: str
    genre: str
    stream_url: str
    homepage: str
    artwork_url: str
    source_url: str
    language: str = "de"
    categories: tuple[str, ...] = ("music",)
    description: str = ""
    default_enabled: bool = True

    def public(self) -> dict[str, object]:
        value = asdict(self)
        value.pop("stream_url")
        value.pop("artwork_url")
        value.pop("default_enabled")
        value["artwork"] = f"/api/radio-art/{self.preset_id}"
        return value


@dataclass(frozen=True, slots=True)
class FeedPreset:
    preset_id: str
    name: str
    language: str
    feed_url: str
    homepage: str
    credit: str

    def public(self) -> dict[str, str]:
        value = asdict(self)
        value.pop("feed_url")
        return value


RADIO_PRESETS = (
    RadioPreset(
        "swr3", "SWR3", "Deutschland", "Pop & Nachrichten",
        "https://dispatcher.rndfnk.com/swr/swr3/live/mp3/128/stream.mp3",
        "https://www.swr3.de/",
        "https://www.swr3.de/assets/swr3/icons/logo.jpg",
        "https://www.swr3.de/musik/webradio/swr3-ueber-das-internet-empfangen-100.html",
        categories=("music", "pop", "news"),
        description="Pop, entertainment and current news",
    ),
    RadioPreset(
        "sunshine_live", "sunshine live", "Deutschland", "Electronic Music",
        "https://stream.sunshine-live.de/live/mp3-128/stream.sunshine-live.de/",
        "https://www.sunshine-live.de/",
        "https://upload.sunshine-live.de/production/static/1792483605187/icons/icon_512.fmRwc30M41g.png",
        "https://stream.sunshine-live.de/live",
        categories=("music", "electronic", "dance"),
        description="Electronic music and dance",
    ),
    RadioPreset(
        "deutschlandfunk", "Deutschlandfunk", "Deutschland", "Nachrichten & Kultur",
        "https://st01.sslstream.dlf.de/dlf/01/128/mp3/stream.mp3",
        "https://www.deutschlandfunk.de/",
        "https://www.deutschlandfunk.de/static/img/deutschlandfunk/icons/apple-touch-icon-180x180.png",
        "https://www.deutschlandradio.de/streamingdienste-100.html",
        categories=("news", "culture", "science", "technology"),
        description="News, analysis, culture, science and technology",
    ),
    RadioPreset(
        "rmf_fm", "RMF FM", "Polska", "Muzyka & wiadomości",
        "https://rs9-krk2.rmfstream.pl/rmf_fm",
        "https://www.rmf.fm/",
        "https://www.rmfon.pl/assets/images/favicon/android-chrome-192x192.png",
        "https://www.rmf.fm/radio/",
        language="pl", categories=("music", "pop", "news"),
        description="Muzyka, rozrywka i wiadomości",
    ),
    RadioPreset(
        "radio_zet", "Radio ZET", "Polska", "Muzyka & wiadomości",
        "https://zt01.cdn.eurozet.pl/zet-old.mp3",
        "https://player.radiozet.pl/",
        "https://gfx-player.radiozet.pl/design/player_radiozet/images/logo_share.jpg",
        "https://player.radiozet.pl/",
        language="pl", categories=("music", "pop", "news"),
        description="Muzyka i wiadomości",
    ),
    RadioPreset(
        "bbc_world", "BBC World Service", "United Kingdom", "World News",
        "https://stream.live.vc.bbcmedia.co.uk/bbc_world_service",
        "https://www.bbc.co.uk/sounds/play/live:bbc_world_service",
        "https://static.files.bbci.co.uk/bbcdotcom/web/20261027-121803-88dfe2b2c8-web-3.26.0-4/apple-touch-icon.png",
        "https://www.bbc.co.uk/sounds/play/live:bbc_world_service",
        language="en", categories=("news", "world", "science", "culture"),
        description="International news, documentaries and analysis",
    ),
    RadioPreset(
        "die_neue_1077", "DIE NEUE 107.7", "Deutschland", "Rock & Pop",
        "https://addrad.io/4454xcp",
        "https://dieneue1077.de/radio/bester-rock-und-pop",
        "https://images.dieneue1077.de/files/2025-01/stream_icons_radio_dn1077.png?width=360&height=360",
        "https://dieneue1077.de/radio/bester-rock-und-pop",
        categories=("music", "rock", "pop"),
        description="Rock and pop from Stuttgart",
    ),
    RadioPreset(
        "afn_eagle", "AFN The Eagle", "Deutschland / US Forces", "Music & News",
        "https://playerservices.streamtheworld.com/api/livestream-redirect/AFNE_KTN.mp3",
        "https://afngo.net/afneurope/Kaiserslautern/radio/Kaiserslautern",
        "https://www.afngo.net/favicon.ico",
        "https://afngo.net/afneurope/Kaiserslautern/radio/Kaiserslautern",
        language="en", categories=("music", "news", "talk"),
        description="English-language music and news for the US Forces community",
    ),
    RadioPreset(
        "rock_antenne", "ROCK ANTENNE", "Deutschland", "Rock",
        "https://stream.rockantenne.de/rockantenne/stream/mp3",
        "https://www.rockantenne.de/",
        "https://www.rockantenne.de/media/cache/3/version/14/ra-v1.jpg/3928d70d548bddf5.jpg",
        "https://www.rockantenne.de/rockhoeren/empfang/streamlinks",
        categories=("music", "rock"),
        description="Rock music",
    ),
    RadioPreset(
        "rock_fm", "ROCK FM", "Deutschland", "Rock",
        "https://stream.regenbogen2.de/dab/mp3-128/private",
        "https://www.rockfm.de/",
        "https://image.atsw.de/atsw/production/2025-08/rockfm_cover_livestream.jpg?width=360&height=360",
        "https://www.rockfm.de/service/empfang",
        categories=("music", "rock"),
        description="Rock music from Baden-Württemberg",
    ),
    # English
    RadioPreset(
        "bbc_radio_2", "BBC Radio 2", "United Kingdom", "Pop & Entertainment",
        "https://as-hls-ww-live.akamaized.net/pool_74208725/live/ww/bbc_radio_two/bbc_radio_two.isml/bbc_radio_two-audio%3d128000.norewind.m3u8",
        "https://www.bbc.co.uk/sounds/play/live:bbc_radio_two",
        "https://cdn-radiotime-logos.tunein.com/s24940q.png",
        "https://www.bbc.co.uk/sounds/play/live:bbc_radio_two",
        language="en", categories=("music", "pop", "entertainment"),
        description="Popular music, live sessions and entertainment", default_enabled=False,
    ),
    RadioPreset(
        "bbc_radio_3", "BBC Radio 3", "United Kingdom", "Classical & Culture",
        "https://as-hls-ww-live.akamaized.net/pool_23461179/live/ww/bbc_radio_three/bbc_radio_three.isml/bbc_radio_three-audio%3d128000.norewind.m3u8",
        "https://www.bbc.co.uk/sounds/play/live:bbc_radio_three",
        "https://cdn-radiotime-logos.tunein.com/s24941q.png",
        "https://www.bbc.co.uk/sounds/play/live:bbc_radio_three",
        language="en", categories=("music", "classical", "culture"),
        description="Classical music, arts and cultural programmes", default_enabled=False,
    ),
    RadioPreset(
        "bbc_radio_4", "BBC Radio 4", "United Kingdom", "News & Speech",
        "https://as-hls-ww-live.akamaized.net/pool_55057080/live/ww/bbc_radio_fourfm/bbc_radio_fourfm.isml/bbc_radio_fourfm-audio%3d128000.norewind.m3u8",
        "https://www.bbc.co.uk/sounds/play/live:bbc_radio_fourfm",
        "https://cdn-radiotime-logos.tunein.com/s25419q.png",
        "https://www.bbc.co.uk/sounds/play/live:bbc_radio_fourfm",
        language="en", categories=("news", "talk", "science", "culture", "drama"),
        description="News, current affairs, science, drama and comedy", default_enabled=False,
    ),
    # Polish
    RadioPreset(
        "polskie_radio_1", "Polskie Radio Jedynka", "Polska", "Wiadomości & Muzyka",
        "http://mp3.polskieradio.pl:8900/;.mp3", "https://jedynka.polskieradio.pl/",
        "https://www.polskieradio.pl/favicon.ico", "https://player.polskieradio.pl/",
        language="pl", categories=("news", "talk", "music", "culture"),
        description="Informacja, publicystyka, kultura i muzyka", default_enabled=False,
    ),
    RadioPreset(
        "polskie_radio_4", "Polskie Radio Czwórka", "Polska", "Muzyka & Kultura",
        "https://stream14.polskieradio.pl/pr4/pr4.sdp/playlist.m3u8", "https://www.polskieradio.pl/10,Czworka",
        "https://upload.wikimedia.org/wikipedia/commons/7/79/Czw%C3%B3rka_Polskie_Radio.jpg",
        "https://player.polskieradio.pl/", language="pl",
        categories=("music", "culture", "technology"),
        description="Nowa muzyka, kultura i nowe technologie", default_enabled=False,
    ),
    RadioPreset(
        "polskie_radio_24", "Polskie Radio 24", "Polska", "Informacja",
        "http://stream3.polskieradio.pl:8080/;.mp3", "https://polskieradio24.pl/",
        "https://www.polskieradio.pl/favicon.ico", "https://player.polskieradio.pl/",
        language="pl", categories=("news", "talk", "politics"),
        description="Całodobowe wiadomości i publicystyka", default_enabled=False,
    ),
    RadioPreset(
        "radio_gra_torun", "Radio GRA Toruń", "Polska", "Muzyka & lokalne informacje",
        "https://rs103-krk.rmfstream.pl/radio_gra", "https://gra.fm/",
        "https://gra.fm/pliki/2025/05/RADIO-GRA-04-podstawowe-Torun.png",
        "https://gra.fm/", language="pl",
        categories=("music", "pop", "local", "news"),
        description="Muzyka, rozrywka i lokalne informacje z Torunia", default_enabled=False,
    ),
    RadioPreset(
        "polskie_radio_2", "Polskie Radio Dwójka", "Polska", "Kultura & muzyka klasyczna",
        "https://stream12.polskieradio.pl/pr2/pr2.sdp/playlist.m3u8",
        "https://www.polskieradio.pl/8,Dwojka",
        "https://upload.wikimedia.org/wikipedia/commons/9/97/Polskie_Radio_Dw%C3%B3jka.png",
        "https://player.polskieradio.pl/", language="pl",
        categories=("culture", "classical", "documentary", "talk", "music"),
        description="Kultura, reportaże, dokumenty i muzyka klasyczna", default_enabled=False,
    ),
    RadioPreset(
        "polskie_radio_3", "Polskie Radio Trójka", "Polska", "Kultura & publicystyka",
        "https://stream13.polskieradio.pl/pr3/pr3.sdp/playlist.m3u8",
        "https://trojka.polskieradio.pl/", "https://www.polskieradio.pl/favicon.ico",
        "https://player.polskieradio.pl/", language="pl",
        categories=("culture", "news", "talk", "documentary", "music"),
        description="Publicystyka, reportaże, kultura i autorska muzyka", default_enabled=False,
    ),
    RadioPreset(
        "radio_357", "Radio 357", "Polska", "Muzyka & rozmowy",
        "https://stream.radio357.pl", "https://radio357.pl/",
        "https://media.radio357.pl/2025/01/radio357_ogimage.png?auto=format%2Ccompress",
        "https://radio357.pl/faq/ogolne/jak-sluchac-radia-357/", language="pl",
        categories=("music", "talk", "culture", "news", "documentary"),
        description="Autorskie audycje, rozmowy, kultura i różnorodna muzyka", default_enabled=False,
    ),
    RadioPreset(
        "radio_nowy_swiat", "Radio Nowy Świat", "Polska", "Kultura & rozmowy",
        "https://stream.nowyswiat.online/mp3", "https://nowyswiat.online/",
        "https://nowyswiat.online/userfiles/radio_nowy_swiat_logo.jpg",
        "https://nowyswiat.online/jak-nas-sluchac", language="pl",
        categories=("music", "talk", "culture", "news", "documentary"),
        description="Rozmowy, reportaże, kultura i starannie wybrana muzyka", default_enabled=False,
    ),
    # French
    RadioPreset(
        "france_inter", "France Inter", "France", "Généraliste",
        "https://icecast.radiofrance.fr/franceinter-midfi.mp3", "https://www.radiofrance.fr/franceinter",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a0/France_Inter_logo_2021.svg/960px-France_Inter_logo_2021.svg.png",
        "https://www.radiofrance.fr/franceinter", language="fr",
        categories=("news", "talk", "culture", "science"),
        description="Information, culture, société et sciences", default_enabled=False,
    ),
    RadioPreset(
        "france_info", "franceinfo", "France", "Information",
        "https://icecast.radiofrance.fr/franceinfo-midfi.mp3", "https://www.francetvinfo.fr/en-direct/radio.html",
        "https://www.francetvinfo.fr/assets/common/images/pwa/ios/120-5487caf3.png",
        "https://www.francetvinfo.fr/en-direct/radio.html", language="fr",
        categories=("news", "talk"), description="Information en continu", default_enabled=False,
    ),
    RadioPreset(
        "france_culture", "France Culture", "France", "Culture & Savoirs",
        "https://icecast.radiofrance.fr/franceculture-midfi.mp3", "https://www.radiofrance.fr/franceculture",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d6/France_Culture_logo_2021.svg/960px-France_Culture_logo_2021.svg.png",
        "https://www.radiofrance.fr/franceculture", language="fr",
        categories=("culture", "science", "technology", "history", "talk"),
        description="Culture, histoire, sciences et idées", default_enabled=False,
    ),
    RadioPreset(
        "fip", "FIP", "France", "Musique éclectique",
        "https://icecast.radiofrance.fr/fip-midfi.mp3", "https://www.radiofrance.fr/fip",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/1/16/FIP_logo_2021.svg/960px-FIP_logo_2021.svg.png",
        "https://www.radiofrance.fr/fip", language="fr",
        categories=("music", "jazz", "world", "electronic"),
        description="Sélection musicale éclectique sans interruption", default_enabled=False,
    ),
    RadioPreset(
        "france_musique", "France Musique", "France", "Classique & Jazz",
        "https://icecast.radiofrance.fr/francemusique-midfi.mp3", "https://www.radiofrance.fr/francemusique",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/France_Musique_logo_2021.svg/960px-France_Musique_logo_2021.svg.png",
        "https://www.radiofrance.fr/francemusique", language="fr",
        categories=("music", "classical", "jazz", "culture"),
        description="Musique classique, jazz et création", default_enabled=False,
    ),
    # Spanish
    RadioPreset(
        "rne_radio_nacional", "RNE Radio Nacional", "España", "Generalista",
        "https://rtvelivestream.rtve.es/rtvesec/rne/rne_r1_main.m3u8", "https://www.rtve.es/play/radio/radio-nacional/",
        "https://www.rtve.es/favicon.ico", "https://www.rtve.es/play/videos/directo/radio-en-directo/",
        language="es", categories=("news", "talk", "culture", "music"),
        description="Información, actualidad, cultura y entretenimiento", default_enabled=False,
    ),
    RadioPreset(
        "rne_clasica", "RNE Radio Clásica", "España", "Música clásica",
        "https://rtvelivestream.rtve.es/rtvesec/rne/rne_r2_main.m3u8", "https://www.rtve.es/play/radio/radio-clasica/",
        "https://www.rtve.es/favicon.ico", "https://www.rtve.es/play/videos/directo/radio-en-directo/",
        language="es", categories=("music", "classical", "culture"),
        description="Música clásica, jazz y creación contemporánea", default_enabled=False,
    ),
    RadioPreset(
        "rne_radio_3", "RNE Radio 3", "España", "Música & Cultura",
        "https://rtvelivestream.rtve.es/rtvesec/rne/rne_r3_main.m3u8", "https://www.rtve.es/play/radio/radio-3/",
        "https://www.rtve.es/favicon.ico", "https://www.rtve.es/play/videos/directo/radio-en-directo/",
        language="es", categories=("music", "alternative", "culture", "technology"),
        description="Música alternativa, cultura, sociedad y tecnología", default_enabled=False,
    ),
    RadioPreset(
        "rne_radio_5", "RNE Radio 5", "España", "Noticias",
        "https://rtvelivestream.rtve.es/rtvesec/rne/rne_r5_madrid_main.m3u8", "https://www.rtve.es/play/radio/radio-5/",
        "https://www.rtve.es/favicon.ico", "https://www.rtve.es/play/videos/directo/radio-en-directo/",
        language="es", categories=("news", "talk"),
        description="Información continua y servicio público", default_enabled=False,
    ),
    RadioPreset(
        "rne_radio_exterior", "RNE Radio Exterior", "España", "Internacional",
        "https://rtvelivestream.rtve.es/rtvesec/rne/rne_re_main.m3u8", "https://www.rtve.es/play/radio/radio-exterior/",
        "https://www.rtve.es/favicon.ico", "https://www.rtve.es/play/videos/directo/radio-en-directo/",
        language="es", categories=("news", "world", "culture", "science"),
        description="Actualidad española e internacional", default_enabled=False,
    ),
    # Italian
    RadioPreset(
        "rai_radio_1", "Rai Radio 1", "Italia", "Notizie & Sport",
        "https://icestreaming.rai.it/1.mp3", "https://www.raiplaysound.it/radio1",
        "https://www.rai.it/favicon.ico", "https://www.radiocorrieretv.rai.it/radio-rai/",
        language="it", categories=("news", "talk", "sport"),
        description="Notizie, attualità, sport e intrattenimento", default_enabled=False,
    ),
    RadioPreset(
        "rai_radio_2", "Rai Radio 2", "Italia", "Musica & Intrattenimento",
        "https://icestreaming.rai.it/2.mp3", "https://www.raiplaysound.it/radio2",
        "https://www.rai.it/favicon.ico", "https://www.radiocorrieretv.rai.it/radio-rai/",
        language="it", categories=("music", "pop", "entertainment"),
        description="Musica, comicità e intrattenimento", default_enabled=False,
    ),
    RadioPreset(
        "rai_radio_3", "Rai Radio 3", "Italia", "Cultura & Musica",
        "https://icestreaming.rai.it/3.mp3", "https://www.raiplaysound.it/radio3",
        "https://www.rai.it/favicon.ico", "https://www.radiocorrieretv.rai.it/radio-rai/",
        language="it", categories=("culture", "science", "music", "classical"),
        description="Cultura, scienza, idee e musica di qualità", default_enabled=False,
    ),
    RadioPreset(
        "rai_isoradio", "Rai Isoradio", "Italia", "Mobilità & Informazione",
        "https://icestreaming.rai.it/6.mp3", "https://www.raiplaysound.it/isoradio",
        "https://www.rai.it/favicon.ico", "https://www.radiocorrieretv.rai.it/radio-rai/",
        language="it", categories=("news", "traffic", "talk", "music"),
        description="Infomobilità, viabilità e musica", default_enabled=False,
    ),
    RadioPreset(
        "radio_24_italia", "Radio 24", "Italia", "News & Talk",
        "http://shoutcast2.radio24.it:8000/;", "https://www.radio24.ilsole24ore.com/",
        "https://www.radio24.ilsole24ore.com/whitelabel/group-2420101401040528/img/apple-touch-icon.png",
        "https://www.radio24.ilsole24ore.com/", language="it",
        categories=("news", "talk", "economy", "science", "technology"),
        description="Notizie, economia, scienza e tecnologia", default_enabled=False,
    ),
    # Dutch
    RadioPreset(
        "npo_radio_1", "NPO Radio 1", "Nederland", "Nieuws & Sport",
        "https://icecast.omroep.nl/radio1-bb-mp3", "https://www.nporadio1.nl/",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/d/da/NPO_Radio_1_logo_2014.svg/960px-NPO_Radio_1_logo_2014.svg.png",
        "https://npo.nl/service/npo-luister-en-radio", language="nl",
        categories=("news", "talk", "sport"), description="Nieuws, debat en sport", default_enabled=False,
    ),
    RadioPreset(
        "npo_radio_2", "NPO Radio 2", "Nederland", "Pop & Actualiteit",
        "https://icecast.omroep.nl/radio2-bb-mp3", "https://www.nporadio2.nl/",
        "https://www.nporadio2.nl/apple-touch-icon.png",
        "https://npo.nl/service/npo-luister-en-radio", language="nl",
        categories=("music", "pop", "talk"), description="Popmuziek en actualiteit", default_enabled=False,
    ),
    RadioPreset(
        "npo_3fm", "NPO 3FM", "Nederland", "Nieuwe Muziek",
        "https://icecast.omroep.nl/3fm-bb-mp3", "https://www.npo3fm.nl/",
        "https://www.3fm.nl/apple-touch-icon.png", "https://npo.nl/service/npo-luister-en-radio",
        language="nl", categories=("music", "pop", "alternative"),
        description="Nieuwe muziek en jong talent", default_enabled=False,
    ),
    RadioPreset(
        "npo_klassiek", "NPO Klassiek", "Nederland", "Klassiek",
        "https://icecast.omroep.nl/radio4-bb-mp3", "https://www.npoklassiek.nl/",
        "https://upload.wikimedia.org/wikipedia/commons/0/01/NPO_Klassiek_Logo.png",
        "https://npo.nl/service/npo-luister-en-radio", language="nl",
        categories=("music", "classical", "culture"), description="Klassieke muziek en concerten", default_enabled=False,
    ),
    RadioPreset(
        "npo_radio_5", "NPO Radio 5", "Nederland", "Evergreens",
        "https://icecast.omroep.nl/radio5-bb-mp3", "https://www.nporadio5.nl/",
        "https://www.nporadio5.nl/apple-touch-icon.png", "https://npo.nl/service/npo-luister-en-radio",
        language="nl", categories=("music", "oldies", "talk"),
        description="Muziek uit de jaren zestig, zeventig en tachtig", default_enabled=False,
    ),
    # Portuguese
    RadioPreset(
        "rtp_antena_1", "RTP Antena 1", "Portugal", "Informação & Música",
        "https://radiocast.rtp.pt/antena180a.mp3", "https://www.rtp.pt/play/direto/antena1",
        "https://www.rtp.pt/favicon.ico", "https://www.rtp.pt/play/direto/antena1",
        language="pt", categories=("news", "talk", "music", "sport"),
        description="Informação, desporto e música portuguesa", default_enabled=False,
    ),
    RadioPreset(
        "rtp_antena_2", "RTP Antena 2", "Portugal", "Clássica & Cultura",
        "https://radiocast.rtp.pt/antena280a.mp3", "https://www.rtp.pt/play/direto/antena2",
        "https://www.rtp.pt/favicon.ico", "https://www.rtp.pt/",
        language="pt", categories=("music", "classical", "culture"),
        description="Música clássica, artes e cultura", default_enabled=False,
    ),
    RadioPreset(
        "rtp_antena_3", "RTP Antena 3", "Portugal", "Nova Música",
        "https://radiocast.rtp.pt/antena380a.mp3", "https://www.rtp.pt/play/direto/antena3",
        "https://www.rtp.pt/favicon.ico", "https://www.rtp.pt/play/direto/antena3",
        language="pt", categories=("music", "alternative", "pop"),
        description="Nova música portuguesa e internacional", default_enabled=False,
    ),
    RadioPreset(
        "tsf", "TSF Rádio Notícias", "Portugal", "Notícias",
        "https://directo.tsf.pt/tsfdirecto.mp3", "https://www.tsf.pt/",
        "https://www.celsoazevedo.com/files/2024/tsf.png", "https://www.tsf.pt/",
        language="pt", categories=("news", "talk", "sport"),
        description="Notícias, atualidade e desporto", default_enabled=False,
    ),
    RadioPreset(
        "radio_observador", "Rádio Observador", "Portugal", "Informação & Ideias",
        "https://playerservices.streamtheworld.com/api/livestream-redirect/OBSERVADOR.mp3",
        "https://observador.pt/radio/", "https://observador.pt/wp-content/themes/observador-child/assets/build/img/favicon.ico",
        "https://observador.pt/perfil/radioobservador/", language="pt",
        categories=("news", "talk", "science", "technology", "culture"),
        description="Notícias, ciência, tecnologia, cultura e debate", default_enabled=False,
    ),
)

FEED_PRESETS = (
    FeedPreset(
        "tagesschau", "tagesschau – alle Meldungen", "de",
        "https://www.tagesschau.de/infoservices/alle-meldungen-100~rss2.xml",
        "https://www.tagesschau.de/", "Quelle: tagesschau.de",
    ),
    FeedPreset(
        "dlf_nachrichten", "Deutschlandfunk Nachrichten", "de",
        "https://www.deutschlandfunk.de/nachrichten-100.rss",
        "https://www.deutschlandfunk.de/", "Quelle: Deutschlandfunk",
    ),
    FeedPreset(
        "rmf24", "RMF24 – najważniejsze informacje", "pl",
        "https://www.rmf24.pl/feed",
        "https://www.rmf24.pl/", "Źródło: RMF24.pl",
    ),
    FeedPreset(
        "bbc_world", "BBC News – World", "en",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.bbc.com/news/world", "Source: BBC News",
    ),
)

RADIO_BY_ID = {item.preset_id: item for item in RADIO_PRESETS}
FEED_BY_ID = {item.preset_id: item for item in FEED_PRESETS}
