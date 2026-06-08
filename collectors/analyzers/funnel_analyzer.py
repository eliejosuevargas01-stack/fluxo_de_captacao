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
    status_code: int = 0
    prefilled_message: str = ""
    extracted_email: str = ""
    extracted_phone: str = ""


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
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", html)
    extracted_email = email_match.group(0) if email_match else ""
    has_email = bool(extracted_email) or ("mailto:" in blob)

    phone_match = re.search(r"(?:\+?55)?\s*\(?\d{2}\)?\s*\d{4,5}[-\s]?\d{4}", html)
    extracted_phone = phone_match.group(0).strip() if phone_match else ""
    has_phone = bool(extracted_phone)

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
        "extracted_email": extracted_email,
        "extracted_phone": extracted_phone,
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
            status_code=0,
            prefilled_message="",
            extracted_email="",
            extracted_phone="",
        )

    domain = _domain(clean_url)
    destination_type = _destination_type(clean_url)

    prefilled_message = ""
    if "wa.me" in clean_url or "api.whatsapp.com" in clean_url:
        parsed = urlparse(clean_url)
        params = parse_qs(parsed.query)
        if "text" in params and params["text"]:
            prefilled_message = params["text"][0]

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
            status_code=200,
            prefilled_message=prefilled_message,
            extracted_email="",
            extracted_phone="",
        )

    html = ""
    error = ""
    status_code = 0
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
        destination_type = _destination_type(clean_url)
        status_code = response.status_code
    except Exception as exc:  # pragma: no cover - network dependent
        error = exc.__class__.__name__

    prefilled_message = ""
    if "wa.me" in clean_url or "api.whatsapp.com" in clean_url:
        parsed = urlparse(clean_url)
        params = parse_qs(parsed.query)
        if "text" in params and params["text"]:
            prefilled_message = params["text"][0]

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
        status_code=status_code,
        prefilled_message=prefilled_message,
        extracted_email=str(signals["extracted_email"]),
        extracted_phone=str(signals["extracted_phone"]),
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


def build_offer(niche: str, signals: FunnelSignals, ad_status: str = "unknown") -> tuple[str, str, str, int]:
    dest = signals.destination_type
    score = 0

    if ad_status == "active":
        score += 50
    if dest != "website":
        score += 50
    if dest == "whatsapp":
        score += 10
    if niche in ["odontologia", "veterinaria"]:
        score += 30

    if niche == "imobiliaria":
        gap = "anuncia imoveis mas sem CRM e sem automacao"
        offer = "Pipeline de leads"
        kind = "pipeline"
    elif dest == "whatsapp":
        gap = "enviando os leads direto para o WhatsApp sem um fluxo automatico de qualificacao"
        offer = "Bot WhatsApp"
        kind = "automacao"
    elif dest in {"instagram_profile", "facebook_page"}:
        gap = "nao tem landing page"
        offer = "Landing Page"
        kind = "landing_page"
    elif dest == "website":
        gap = "formulario horrivel"
        offer = "Captacao de leads"
        kind = "captacao"
    else:
        gap = "funil desestruturado"
        offer = "Landing Page e Automacao"
        kind = "landing_page"

    return gap, offer, kind, score


def build_proposal(page_name: str, gap: str, offer: str, price: str = "R$ 300") -> str:
    return (
        f"Oi, {page_name}. Analisei os seus anuncios e vi que {gap}. "
        f"Posso te entregar {offer} por {price}, com pagamento 100% apos a entrega e prazo de 24h. "
        f"Se fizer sentido, eu te mostro o plano e ja começo."
    )
