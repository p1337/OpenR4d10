"""Curated, license-documented AmbientR4D10 soundscape presets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AmbientPreset:
    preset_id: str
    name: str
    description: str
    audio_url: str
    source_page: str
    credit: str
    license_name: str
    license_url: str
    sha256: str | None = None

    def public(self) -> dict[str, str]:
        value = {
            "preset_id": self.preset_id,
            "name": self.name,
            "description": self.description,
            "artwork": f"/api/ambient-art/{self.preset_id}",
            "source_page": self.source_page,
            "credit": self.credit,
            "license_name": self.license_name,
            "license_url": self.license_url,
        }
        if self.sha256 is not None:
            value["sha256"] = self.sha256
        return value


COMMONS_UPLOAD = "https://upload.wikimedia.org/wikipedia/commons/"
CC0_URL = "https://creativecommons.org/publicdomain/zero/1.0/"
PUBLIC_DOMAIN_URL = "https://creativecommons.org/publicdomain/mark/1.0/"
CC_BY_SA_3_URL = "https://creativecommons.org/licenses/by-sa/3.0/"
CC_BY_SA_4_URL = "https://creativecommons.org/licenses/by-sa/4.0/"


AMBIENT_PRESETS = (
    AmbientPreset(
        "cafe",
        "Café",
        "Quiet coffeehouse with a small group talking softly",
        "https://cdn.freesound.org/previews/46/46310_43834-lq.ogg",
        "https://freesound.org/people/moxobna/sounds/46310/",
        "moxobna",
        "CC0 1.0",
        CC0_URL,
        "86c51e4fa5001c4fbf597c8725b50e36a347c31fbc0c499cad0a1bc27e9bb072",
    ),
    AmbientPreset(
        "forest",
        "Forest",
        "Forest, wind, birds and distant insects",
        COMMONS_UPLOAD + "0/0a/20090610_0_ambience.ogg",
        "https://commons.wikimedia.org/wiki/File:20090610_0_ambience.ogg",
        "nille",
        "Public domain",
        PUBLIC_DOMAIN_URL,
        "43848c3eda5f42829f1033112c2a91ba3e5c91b79a0532fda264c9f59856d431",
    ),
    AmbientPreset(
        "beach",
        "Sea & beach",
        "Waves rolling across a pebble beach",
        COMMONS_UPLOAD + "7/73/On_a_pebble_beach.ogg",
        "https://commons.wikimedia.org/wiki/File:On_a_pebble_beach.ogg",
        "earthcalling",
        "Public domain",
        PUBLIC_DOMAIN_URL,
        "4e506141b9a285d03debdb8e0fbc9c1e30aaa29f82f8b2f368f70d5491a636b6",
    ),
    AmbientPreset(
        "brook",
        "Forest brook",
        "A small brook flowing through a forest",
        COMMONS_UPLOAD + "8/88/Brook.ogg",
        "https://commons.wikimedia.org/wiki/File:Brook.ogg",
        "Onegoodtune",
        "CC BY-SA 3.0",
        CC_BY_SA_3_URL,
        "9847be31041e84dff3a70a52cfaf9f8a1b3d12bf836033e5a157daef8b036efb",
    ),
    AmbientPreset(
        "rain",
        "Gentle rain",
        "Light rainfall without synthetic music",
        COMMONS_UPLOAD + "1/15/Sound_of_light_rainfall.ogg",
        "https://commons.wikimedia.org/wiki/File:Sound_of_light_rainfall.ogg",
        "Mijesty",
        "CC BY-SA 4.0",
        CC_BY_SA_4_URL,
        "e0233652d8173650149adcf3d6e5ddc01b73e8a93ce61b8d7809abfe582251a8",
    ),
    AmbientPreset(
        "night_crickets",
        "Night field & crickets",
        "A long field-cricket chorus at night",
        COMMONS_UPLOAD + "4/4c/Crickets_choir.ogg",
        "https://commons.wikimedia.org/wiki/File:Crickets_choir.ogg",
        "Serg Childed",
        "CC BY-SA 4.0",
        CC_BY_SA_4_URL,
        "f0d82e6b96d110d09615ccca2b2f0b8945f06b0be50c09864c66b9e440b1a7b3",
    ),
    AmbientPreset(
        "orchard_birds",
        "Orchard meadow & birds",
        "Light birdsong across a quiet orchard meadow",
        "https://cdn.freesound.org/previews/440/440807_8523759-lq.ogg",
        "https://freesound.org/people/PuzzleAudio/sounds/440807/",
        "PuzzleAudio",
        "CC0 1.0",
        CC0_URL,
        "64efe6c695a26333528592674fd23652cb712ebd359bb159e253f882099dca2f",
    ),
    AmbientPreset(
        "distant_highway",
        "Distant road & birds",
        "Distant traffic with occasional birds",
        "https://cdn.freesound.org/previews/188/188402_1451873-lq.ogg",
        "https://freesound.org/people/myrinvp/sounds/188402/",
        "myrinvp",
        "CC0 1.0",
        CC0_URL,
        "caa3be417ae45f0298c2dba9fe6eca2ec852180e3ceb5980c6bec15894030ef4",
    ),
    AmbientPreset(
        "cliff_sea",
        "Sea from a cliff",
        "Sea heard from a high cliff with the water farther away",
        "https://cdn.freesound.org/previews/525/525029_11519060-lq.ogg",
        "https://freesound.org/people/bruno.auzet/sounds/525029/",
        "bruno.auzet",
        "CC0 1.0",
        CC0_URL,
        "6f5e589d412feeee5d8c01defff9092bf169c8f9b64a01451e8d9d8636e64a58",
    ),
    AmbientPreset(
        "distant_thunder",
        "Distant thunder",
        "Low thunder rolling far beyond the listener",
        "https://cdn.freesound.org/previews/530/530133_10334845-lq.ogg",
        "https://freesound.org/people/Beetlemuse/sounds/530133/",
        "Beetlemuse",
        "CC0 1.0",
        CC0_URL,
        "97b3411cd2b2ba2036b4cb8e45ef245a7350a39cbcb47bc7463900fa1edadb6d",
    ),
)

AMBIENT_BY_ID = {item.preset_id: item for item in AMBIENT_PRESETS}
AMBIENT_LAYER_DEFAULTS = {
    "orchard_birds": 30,
    "distant_highway": 20,
    "cliff_sea": 25,
    "distant_thunder": 20,
}
AMBIENT_LAYER_IDS = tuple(AMBIENT_LAYER_DEFAULTS)
AMBIENT_ARTWORK_ROOT = Path(__file__).resolve().parents[2] / "assets" / "ambient"

AMBIENT_TRANSLATIONS = {
    "de": {
        "cafe": ("Café", "Kleines ruhiges Café mit leisen Gesprächen"),
        "forest": ("Wald", "Wald, Wind, Vögel und ferne Insekten"),
        "beach": ("Meer & Strand", "Wellen an einem Kieselstrand"),
        "brook": ("Waldbach", "Ein kleiner Bach fließt durch den Wald"),
        "rain": ("Sanfter Regen", "Leichter Regen ohne künstliche Musik"),
        "night_crickets": ("Nachtfeld & Grillen", "Langes Grillenkonzert auf einem nächtlichen Feld"),
        "orchard_birds": ("Streuobstwiese & Vögel", "Leichtes Vogelgezwitscher auf einer ruhigen Streuobstwiese"),
        "distant_highway": ("Ferne Autobahn & Vögel", "Entferntes Straßenrauschen mit vereinzelten Vögeln"),
        "cliff_sea": ("Meer von der Klippe", "Meeresrauschen von einer hohen Klippe, das Wasser weiter entfernt"),
        "distant_thunder": ("Entfernter Donner", "Leiser Donner rollt weit in der Ferne"),
    },
    "pl": {
        "cafe": ("Kawiarnia", "Mała spokojna kawiarnia z cichymi rozmowami"),
        "forest": ("Las", "Las, wiatr, ptaki i odległe owady"),
        "beach": ("Morze i plaża", "Fale na kamienistej plaży"),
        "brook": ("Leśny strumień", "Mały strumień płynący przez las"),
        "rain": ("Delikatny deszcz", "Lekki deszcz bez syntetycznej muzyki"),
        "night_crickets": ("Nocne pole i świerszcze", "Długi nocny chór świerszczy polnych"),
        "orchard_birds": ("Sad i ptaki", "Delikatny śpiew ptaków w spokojnym sadzie"),
        "distant_highway": ("Odległa droga i ptaki", "Odległy szum drogi i sporadyczne ptaki"),
        "cliff_sea": ("Morze z klifu", "Morze słyszane z wysokiego klifu"),
        "distant_thunder": ("Odległy grzmot", "Cichy grzmot daleko na horyzoncie"),
    },
    "fr": {
        "cafe": ("Café", "Petit café calme aux conversations feutrées"),
        "forest": ("Forêt", "Forêt, vent, oiseaux et insectes lointains"),
        "beach": ("Mer et plage", "Vagues sur une plage de galets"),
        "brook": ("Ruisseau forestier", "Petit ruisseau traversant une forêt"),
        "rain": ("Pluie douce", "Pluie légère sans musique synthétique"),
        "night_crickets": ("Champ nocturne et grillons", "Long chœur nocturne de grillons des champs"),
        "orchard_birds": ("Verger et oiseaux", "Chant léger d’oiseaux dans un verger calme"),
        "distant_highway": ("Route lointaine et oiseaux", "Circulation lointaine et quelques oiseaux"),
        "cliff_sea": ("Mer depuis la falaise", "Mer entendue depuis une haute falaise"),
        "distant_thunder": ("Tonnerre lointain", "Grondement discret très loin"),
    },
    "es": {
        "cafe": ("Cafetería", "Cafetería pequeña y tranquila con conversaciones suaves"),
        "forest": ("Bosque", "Bosque, viento, pájaros e insectos lejanos"),
        "beach": ("Mar y playa", "Olas sobre una playa de guijarros"),
        "brook": ("Arroyo del bosque", "Un pequeño arroyo que atraviesa el bosque"),
        "rain": ("Lluvia suave", "Lluvia ligera sin música sintética"),
        "night_crickets": ("Campo nocturno y grillos", "Largo coro nocturno de grillos de campo"),
        "orchard_birds": ("Huerto y pájaros", "Canto ligero de pájaros en un huerto tranquilo"),
        "distant_highway": ("Carretera lejana y pájaros", "Tráfico lejano con pájaros ocasionales"),
        "cliff_sea": ("Mar desde el acantilado", "Mar oído desde un acantilado alto"),
        "distant_thunder": ("Trueno lejano", "Trueno suave muy distante"),
    },
}


def ambient_text(preset_id: str, language: str) -> tuple[str, str] | None:
    """Return translated built-in scene text without changing custom names."""

    preset = AMBIENT_BY_ID.get(preset_id)
    if preset is None:
        return None
    if language == "en":
        return preset.name, preset.description
    return AMBIENT_TRANSLATIONS.get(language, {}).get(
        preset_id, (preset.name, preset.description)
    )
