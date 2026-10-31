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
)

AMBIENT_BY_ID = {item.preset_id: item for item in AMBIENT_PRESETS}
AMBIENT_ARTWORK_ROOT = Path(__file__).resolve().parents[2] / "assets" / "ambient"

AMBIENT_TRANSLATIONS = {
    "de": {
        "cafe": ("Café", "Kleines ruhiges Café mit leisen Gesprächen"),
        "forest": ("Wald", "Wald, Wind, Vögel und ferne Insekten"),
        "beach": ("Meer & Strand", "Wellen an einem Kieselstrand"),
        "brook": ("Waldbach", "Ein kleiner Bach fließt durch den Wald"),
        "rain": ("Sanfter Regen", "Leichter Regen ohne künstliche Musik"),
        "night_crickets": ("Nachtfeld & Grillen", "Langes Grillenkonzert auf einem nächtlichen Feld"),
    },
    "pl": {
        "cafe": ("Kawiarnia", "Mała spokojna kawiarnia z cichymi rozmowami"),
        "forest": ("Las", "Las, wiatr, ptaki i odległe owady"),
        "beach": ("Morze i plaża", "Fale na kamienistej plaży"),
        "brook": ("Leśny strumień", "Mały strumień płynący przez las"),
        "rain": ("Delikatny deszcz", "Lekki deszcz bez syntetycznej muzyki"),
        "night_crickets": ("Nocne pole i świerszcze", "Długi nocny chór świerszczy polnych"),
    },
    "fr": {
        "cafe": ("Café", "Petit café calme aux conversations feutrées"),
        "forest": ("Forêt", "Forêt, vent, oiseaux et insectes lointains"),
        "beach": ("Mer et plage", "Vagues sur une plage de galets"),
        "brook": ("Ruisseau forestier", "Petit ruisseau traversant une forêt"),
        "rain": ("Pluie douce", "Pluie légère sans musique synthétique"),
        "night_crickets": ("Champ nocturne et grillons", "Long chœur nocturne de grillons des champs"),
    },
    "es": {
        "cafe": ("Cafetería", "Cafetería pequeña y tranquila con conversaciones suaves"),
        "forest": ("Bosque", "Bosque, viento, pájaros e insectos lejanos"),
        "beach": ("Mar y playa", "Olas sobre una playa de guijarros"),
        "brook": ("Arroyo del bosque", "Un pequeño arroyo que atraviesa el bosque"),
        "rain": ("Lluvia suave", "Lluvia ligera sin música sintética"),
        "night_crickets": ("Campo nocturno y grillos", "Largo coro nocturno de grillos de campo"),
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
