from __future__ import annotations

import re
import ssl
from dataclasses import dataclass
from functools import lru_cache
from html import unescape
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import requests


SOCIAL_DOMAINS = {
    "instagram.com",
    "www.instagram.com",
    "facebook.com",
    "www.facebook.com",
    "m.facebook.com",
    "l.facebook.com",
    "wa.me",
    "api.whatsapp.com",
}


@dataclass(frozen=True)
class FunnelSignals:
    destination_type: str
    clean_url: str
    domain: str
    has_whatsapp: bool
    has_form: bool
    has_booking: bool
    has_instagram: bool
    has_phone: bool
    has_email: bool
    title: str
    error: str = ""


def normalize_url(url: Any) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.netloc.endswith("l.facebook.com"):
        params = parse_qs(parsed.query)
        if params.get("u"):
            raw = unquote(params["u"][0])
            parsed = urlparse(raw)
    if raw.startswith("//"):
        return f"https:{raw}"
    if not parsed.scheme:
        return f"https://{raw}"
    return raw


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().replace("www.", "")


def _is_social_domain(domain: str) -> bool:
    return domain in SOCIAL_DOMAINS


def _destination_type(clean_url: str) -> str:
    domain = _domain(clean_url)
    if "wa.me" in domain or "whatsapp" in domain:
        return "whatsapp"
    if "instagram.com" in domain:
        return "instagram_profile"
    if "facebook.com" in domain:
        return "facebook_page"
    if not domain:
        return "unknown"
    return "website"


def _extract_phone_digits(text: str) -> str:
    digits = re.sub(r"\D+", "", text)
    if digits.startswith("55") and len(digits) >= 12:
        return digits
    if len(digits) in (10, 11):
        return f"55{digits}"
    return ""


def _inspect_html(html: str, url: str = "") -> dict[str, bool | str]:
    blob = f"{url}\n{html}".lower()
    has_whatsapp = any(token in blob for token in ("wa.me", "api.whatsapp.com", "whatsapp://", "whatsapp"))
    has_form = any(token in blob for token in ("<form", "contact-form", "formulario", "formulário", "lead-form", "fale conosco"))
    has_booking = any(token in blob for token in ("calendly", "agendamento", "agendar", "agenda online", "booking", "book now", "schedule"))
    has_instagram = "instagram.com" in blob
    has_email = "mailto:" in blob or "@" in blob
    phone_match = re.search(r"(?:\+?55)?\s*\(?\d{2}\)?\s*\d{4,5}[-\s]?\d{4}", html)
    has_phone = bool(phone_match)
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    title = unescape(title_match.group(1)).strip() if title_match else ""
    return {
        "has_whatsapp": has_whatsapp,
        "has_form": has_form,
        "has_booking": has_booking,
        "has_instagram": has_instagram,
        "has_phone": has_phone,
        "has_email": has_email,
        "title": title,
    }


def _pick_contact_url(clean_url: str, signals: dict[str, bool | str], html: str) -> str:
    if _destination_type(clean_url) == "website":
        phone_match = re.search(r"(?:\+?55)?\s*\(?\d{2}\)?\s*\d{4,5}[-\s]?\d{4}", html)
        if phone_match:
            digits = _extract_phone_digits(phone_match.group(0))
            if digits:
                return f"https://wa.me/{digits}"
    return clean_url


@lru_cache(maxsize=512)
def inspect_destination(url: Any) -> FunnelSignals:
    clean_url = normalize_url(url)
    if not clean_url:
        return FunnelSignals(
            destination_type="none",
            clean_url="",
            domain="",
            has_whatsapp=False,
            has_form=False,
            has_booking=False,
            has_instagram=False,
            has_phone=False,
            has_email=False,
            title="",
            error="sem_url",
        )

    domain = _domain(clean_url)
    destination_type = _destination_type(clean_url)

    if _is_social_domain(domain):
        return FunnelSignals(
            destination_type=destination_type,
            clean_url=clean_url,
            domain=domain,
            has_whatsapp="whatsapp" in clean_url,
            has_form=False,
            has_booking=False,
            has_instagram="instagram.com" in domain,
            has_phone=False,
            has_email=False,
            title="",
            error="social_only",
        )

    html = ""
    error = ""
    try:
        response = requests.get(
            clean_url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            },
            allow_redirects=True,
        )
        html = response.text
        clean_url = response.url
        domain = _domain(clean_url)
    except Exception as exc:  # pragma: no cover - network dependent
        error = exc.__class__.__name__

    signals = _inspect_html(html, clean_url)
    return FunnelSignals(
        destination_type=destination_type,
        clean_url=_pick_contact_url(clean_url, signals, html) if destination_type == "website" else clean_url,
        domain=domain,
        has_whatsapp=bool(signals["has_whatsapp"]),
        has_form=bool(signals["has_form"]),
        has_booking=bool(signals["has_booking"]),
        has_instagram=bool(signals["has_instagram"]),
        has_phone=bool(signals["has_phone"]),
        has_email=bool(signals["has_email"]),
        title=str(signals["title"]),
        error=error,
    )


def infer_niche(*texts: Any) -> str:
    blob = " ".join(str(t or "") for t in texts).lower()
    rules = [
        ("odontologia", ("odont", "dentist", "dental", "implantes", "ortodont")),
        ("veterinaria", ("veter", "animal hospital", "pet")),
        ("imobiliaria", ("imobili", "real estate", "property", "corretor")),
        ("estetica", ("estet", "beauty", "beautician", "laser", "harmoniz")),
        ("barbearia", ("barber", "barbear", "barbershop")),
        ("academia", ("academia", "gym", "fitness", "personal trainer", "treinamento funcional")),
    ]
    for label, keys in rules:
        if any(key in blob for key in keys):
            return label
    return "geral"


def build_offer(niche: str, signals: FunnelSignals) -> tuple[str, str, str, int]:
    dest = signals.destination_type
    score = 0

    if dest in {"instagram_profile", "facebook_page"}:
        score += 40
        if niche in {"barbearia", "estetica", "academia", "odontologia", "veterinaria", "imobiliaria"}:
            gap = "o trafego esta indo para um perfil social, sem uma pagina de conversao clara"
        else:
            gap = "o trafego esta indo para um perfil social e pode estar perdendo conversao"
        offer = "landing page simples com WhatsApp e captura de leads"
        kind = "landing_page"
    elif dest == "whatsapp":
        score += 30
        gap = "a conversao depende de WhatsApp direto, mas ainda falta estrutura para qualificar o lead"
        offer = "landing page simples com formulario e automacao de WhatsApp"
        kind = "automacao"
    elif dest == "website":
        weak = not signals.has_form or not signals.has_whatsapp or not signals.has_booking
        if weak:
            score += 25
            missing = []
            if not signals.has_form:
                missing.append("formulario")
            if not signals.has_whatsapp:
                missing.append("WhatsApp")
            if not signals.has_booking:
                missing.append("agendamento")
            gap = f"o site nao esta capturando bem o lead: falta {', '.join(missing)}"
            if niche in {"odontologia", "veterinaria", "imobiliaria"}:
                offer = "landing page de conversao + automacao de atendimento"
            else:
                offer = "landing page simples + automacao de captura"
            kind = "landing_page"
        else:
            score += 10
            gap = "o site existe, mas ainda ha espaco para aumentar a taxa de conversao"
            offer = "otimizacao da landing page e automacao leve"
            kind = "otimizacao"
    else:
        score += 20
        gap = "o destino nao ficou claro e o funil parece pouco estruturado"
        offer = "landing page simples com WhatsApp e formulario"
        kind = "landing_page"

    if signals.has_phone:
        score += 5
    if signals.has_email:
        score += 2

    return gap, offer, kind, score


def build_proposal(page_name: str, gap: str, offer: str, price: str = "R$ 300") -> str:
    return (
        f"Oi, {page_name}. Analisei os seus anuncios e vi que {gap}. "
        f"Posso te entregar {offer} por {price}, com pagamento 100% apos a entrega e prazo de 24h. "
        f"Se fizer sentido, eu te mostro o plano e ja começo."
    )
