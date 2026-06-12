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


@dataclass
class OfferProposal:
    gap: str
    offer: str
    kind: str
    score: int
    confidence: int
    evidence: list[str]


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
    email: str | None = None
    phone: str | None = None


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


def _extract_phone_from_whatsapp_url(url: str) -> str | None:
    parsed = urlparse(url)
    if "wa.me" in parsed.netloc:
        digits = re.sub(r"\D+", "", parsed.path)
        if digits:
            return digits
    elif "whatsapp.com" in parsed.netloc:
        params = parse_qs(parsed.query)
        if "phone" in params and params["phone"]:
            return re.sub(r"\D+", "", params["phone"][0])
    return None


def extract_emails_from_text(text: str) -> list[str]:
    if not text:
        return []
    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    return list(dict.fromkeys(emails))


def extract_phones_from_text(text: str) -> list[str]:
    if not text:
        return []
    found_phones = []
    
    # 1. WhatsApp link pattern
    wa_pattern = r"(?:wa\.me/|api\.whatsapp\.com/send\?(?:[^&]*&)*phone=|whatsapp\.com/send\?(?:[^&]*&)*phone=|whatsapp://send\?(?:[^&]*&)*phone=)(\+?\d+)"
    for match in re.finditer(wa_pattern, text, re.IGNORECASE):
        digits = _extract_phone_digits(match.group(1))
        if digits and digits not in found_phones:
            found_phones.append(digits)
            
    # 2. Plain phone pattern (Brazilian format)
    # Check mobile numbers first (starts with 9)
    mobile_pattern = r"(?:\+?55)?\s*\(?([1-9][1-9])\)?\s*(9\s?\d{4}[-\s]?\d{4})"
    for match in re.finditer(mobile_pattern, text):
        digits = _extract_phone_digits(match.group(0))
        if digits and digits not in found_phones:
            found_phones.append(digits)
            
    # Check landline/general numbers as fallback
    landline_pattern = r"(?:\+?55)?\s*\(?([1-9][1-9])\)?\s*([2-5]\d{3}[-\s]?\d{4})"
    for match in re.finditer(landline_pattern, text):
        digits = _extract_phone_digits(match.group(0))
        if digits and digits not in found_phones:
            found_phones.append(digits)
            
    return found_phones


def _inspect_html(html: str, url: str = "") -> dict[str, Any]:
    blob = f"{url}\n{html}".lower()
    has_whatsapp = any(token in blob for token in ("wa.me", "api.whatsapp.com", "whatsapp://", "whatsapp"))
    has_form = any(token in blob for token in ("<form", "contact-form", "formulario", "formulário", "lead-form", "fale conosco"))
    has_booking = any(token in blob for token in ("calendly", "agendamento", "agendar", "agenda online", "booking", "book now", "schedule"))
    has_instagram = "instagram.com" in blob
    
    # Extrai o email real usando a nova função
    emails = extract_emails_from_text(html)
    email = emails[0] if emails else None
    has_email = bool(email)
    
    # Extrai o telefone real usando a nova função
    phones = extract_phones_from_text(blob)
    phone = phones[0] if phones else None
    has_phone = bool(phone)
    
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    title = unescape(title_match.group(1)).strip() if title_match else ""
    return {
        "has_whatsapp": has_whatsapp,
        "has_form": has_form,
        "has_booking": has_booking,
        "has_instagram": has_instagram,
        "has_phone": has_phone,
        "has_email": has_email,
        "email": email,
        "phone": phone,
        "title": title,
    }


def _pick_contact_url(clean_url: str, signals: dict[str, Any], html: str) -> str:
    if _destination_type(clean_url) == "website":
        if signals.get("phone"):
            return f"https://wa.me/{signals['phone']}"
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
            email=None,
            phone=None,
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
        phone = _extract_phone_from_whatsapp_url(clean_url) if destination_type == "whatsapp" else None
        return FunnelSignals(
            destination_type=destination_type,
            clean_url=clean_url,
            domain=domain,
            has_whatsapp=("whatsapp" in clean_url or "wa.me" in clean_url or destination_type == "whatsapp"),
            has_form=False,
            has_booking=False,
            has_instagram="instagram.com" in domain,
            has_phone=bool(phone),
            has_email=False,
            title="",
            error="social_only",
            status_code=200,
            prefilled_message=prefilled_message,
            email=None,
            phone=phone,
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
    
    # Se for link de whatsapp de redirecionamento, tenta ler o número
    phone = signals.get("phone")
    if not phone:
        if destination_type == "whatsapp":
            phone = _extract_phone_from_whatsapp_url(clean_url)
        if not phone:
            extra_phones = extract_phones_from_text(html)
            if extra_phones:
                phone = extra_phones[0]

    return FunnelSignals(
        destination_type=destination_type,
        clean_url=_pick_contact_url(clean_url, signals, html) if destination_type == "website" else clean_url,
        domain=domain,
        has_whatsapp=bool(signals["has_whatsapp"]),
        has_form=bool(signals["has_form"]),
        has_booking=bool(signals["has_booking"]),
        has_instagram=bool(signals["has_instagram"]),
        has_phone=bool(signals["has_phone"]) or bool(phone),
        has_email=bool(signals["has_email"]),
        title=str(signals["title"]),
        error=error,
        status_code=status_code,
        prefilled_message=prefilled_message,
        email=signals.get("email"),
        phone=phone,
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


def build_offer(niche: str, signals: FunnelSignals, ad_status: str = "unknown") -> OfferProposal:
    dest = signals.destination_type
    score = 0
    confidence = 0
    evidence = []

    if ad_status == "active":
        score += 50
        evidence.append("ad_status=active")

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
        confidence = 80
        evidence.append(f"niche={niche}")
    elif dest == "whatsapp":
        gap = "enviando os leads direto para o WhatsApp sem um fluxo automatico de qualificacao"
        offer = "Bot WhatsApp"
        kind = "automacao"
        confidence = 90
        evidence.append("destination=whatsapp")
    elif dest in {"instagram_profile", "facebook_page"}:
        gap = "nao tem landing page"
        offer = "Landing Page"
        kind = "landing_page"
        confidence = 90
        evidence.append(f"destination={dest}")
    elif dest == "website":
        evidence.append("website_detected")
        if not signals.has_form:
            gap = "site recebe trafego mas nao possui uma captacao clara"
            offer = "Captacao de leads"
            kind = "captacao"
            confidence = 95
            evidence.append("has_form=false")
        elif signals.has_form:
            gap = "possivel falta de qualificacao dos leads"
            offer = "Automacao de Qualificacao"
            kind = "captacao"
            confidence = 40
            evidence.append("has_form=true")
        else:
            gap = "processo de captacao nao identificado"
            offer = "Captacao de leads"
            kind = "captacao"
            confidence = 20
            evidence.append("unknown_form_state")
    else:
        gap = "funil desestruturado"
        offer = "Landing Page e Automacao"
        kind = "landing_page"
        confidence = 20
        evidence.append("unknown_destination")

    return OfferProposal(
        gap=gap,
        offer=offer,
        kind=kind,
        score=score,
        confidence=confidence,
        evidence=evidence
    )


def build_proposal(page_name: str, proposal: OfferProposal, price: str = "R$ 300") -> str:
    if proposal.confidence >= 80:
        intro = f"Notei que {proposal.gap}."
    elif proposal.confidence >= 50:
        intro = f"Me chamou atenção um possível gargalo: {proposal.gap}."
    else:
        intro = f"Posso estar vendo errado, mas fiquei com uma dúvida sobre a forma como os contatos que chegam dos anúncios são tratados hoje ({proposal.gap})."

    return (
        f"Oi, {page_name}. Analisei os seus anuncios e vi isso. {intro} "
        f"Posso te entregar {proposal.offer} por {price}, com pagamento 100% apos a entrega e prazo de 24h. "
        f"Se fizer sentido, eu te mostro o plano e ja começo."
    )
