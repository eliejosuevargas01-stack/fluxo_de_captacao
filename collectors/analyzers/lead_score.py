from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Any


SEGMENT_WEIGHTS: list[tuple[tuple[str, ...], int]] = [
    (("odontologia", "dentist", "dental clinic", "dental", "implantes", "ortodont"), 40),
    (("veterinaria", "veterinarian", "animal hospital", "pet", "clinic veterinaria", "clinic veterinária"), 35),
    (("imobiliaria", "real estate", "real estate agent", "commercial real estate", "construction company"), 35),
    (("estetica", "beauty", "beautician", "laser hair removal", "plastic surgery clinic", "health and beauty", "salon"), 30),
    (("barbearia", "barber"), 20),
    (("academia", "gym", "fitness", "personal trainer"), 20),
]


@dataclass(frozen=True)
class ScoreBreakdown:
    score: int
    tem_site: bool
    segmento_peso: int


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def parse_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    text = re.sub(r"[^\d\-]", "", text)
    if not text:
        return default
    try:
        return int(text)
    except ValueError:
        return default


def parse_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    text = str(value).strip().replace(",", ".")
    if not text:
        return default
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return default
    try:
        return float(match.group(0))
    except ValueError:
        return default


def segment_weight(category: Any) -> int:
    normalized = _normalize_text(category)
    if not normalized:
        return 0

    for keywords, weight in SEGMENT_WEIGHTS:
        if any(keyword in normalized for keyword in keywords):
            return weight
    return 0


def has_site(site: Any) -> bool:
    return bool(str(site or "").strip())


def score_lead(row: dict[str, Any]) -> ScoreBreakdown:
    site_present = has_site(row.get("site"))
    score = 10 if site_present else 40

    reviews = parse_int(row.get("avaliacoes") or row.get("reviews"))
    if reviews > 50:
        score += 20

    rating = parse_float(row.get("nota") or row.get("rating"))
    if rating >= 4.5:
        score += 20

    weight = segment_weight(row.get("categoria") or row.get("segmento"))
    score += weight

    return ScoreBreakdown(score=score, tem_site=site_present, segmento_peso=weight)

