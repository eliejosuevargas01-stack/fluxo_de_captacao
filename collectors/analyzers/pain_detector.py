from __future__ import annotations

from dataclasses import dataclass
import re
import ssl
from functools import lru_cache
from html import unescape
from typing import Any
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from collectors.analyzers.lead_score import _normalize_text


MAX_HTML_BYTES = 512_000
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class SiteDiagnosis:
    site: bool
    whatsapp: bool
    whatsapp_hints: tuple[str, ...]
    agendamento: bool
    instagram: bool
    formulario: bool
    url_final: str
    erro: str = ""


def normalize_url(url: Any) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    if raw.startswith("//"):
        return f"https:{raw}"
    parsed = urlparse(raw)
    if parsed.scheme:
        return raw
    return f"https://{raw}"


def normalize_phone_digits(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def normalize_brazil_whatsapp_number(value: Any) -> str:
    digits = normalize_phone_digits(value)
    if not digits:
        return ""
    if digits.startswith("55") and len(digits) >= 12:
        return digits
    if len(digits) in (10, 11):
        return f"55{digits}"
    return digits


def extract_whatsapp_hints(url: str, html: str) -> tuple[str, ...]:
    sources = f"{url}\n{html}"
    patterns = (
        r"wa\.me/(\d{10,15})",
        r"api\.whatsapp\.com/send/\?phone=(\d{10,15})",
        r"whatsapp://send\?phone=(\d{10,15})",
    )
    found: set[str] = set()
    for pattern in patterns:
        for match in re.findall(pattern, sources, flags=re.IGNORECASE):
            found.add(normalize_brazil_whatsapp_number(match))
    return tuple(sorted(x for x in found if x))


def _looks_like_instagram(url: str, html: str) -> bool:
    url = url.lower()
    html = html.lower()
    return "instagram.com" in url or "instagram.com" in html


def _looks_like_whatsapp(url: str, html: str) -> bool:
    url = url.lower()
    html = html.lower()
    patterns = ("wa.me", "api.whatsapp.com", "whatsapp", "chat.whatsapp")
    return any(pattern in url or pattern in html for pattern in patterns)


def _looks_like_agendamento(url: str, html: str) -> bool:
    hay = _normalize_text(f"{url} {html}")
    patterns = (
        "agendamento",
        "agendar",
        "agenda online",
        "marcar consulta",
        "marque seu horario",
        "marque seu horário",
        "booking",
        "book now",
        "schedule",
        "calendly",
        "reserve",
        "reserva",
    )
    return any(pattern in hay for pattern in patterns)


def _looks_like_form(html: str) -> bool:
    hay = html.lower()
    patterns = (
        "<form",
        "contact-form",
        "formulario",
        "formulário",
        "fale conosco",
        "contato",
        "lead-form",
        'type="email"',
        "name=\"email\"",
        "name='email'",
        'name="phone"',
        "name='phone'",
    )
    return any(pattern in hay for pattern in patterns)


@lru_cache(maxsize=256)
def diagnose_site(url: Any) -> SiteDiagnosis:
    normalized_url = normalize_url(url)
    if not normalized_url:
        return SiteDiagnosis(
            site=False,
            whatsapp=False,
            whatsapp_hints=(),
            agendamento=False,
            instagram=False,
            formulario=False,
            url_final="",
            erro="sem_site",
        )

    html = ""
    final_url = normalized_url
    error = ""

    try:
        request = Request(
            normalized_url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
                "Accept-Encoding": "identity",
            },
            method="GET",
        )
        context = ssl.create_default_context()
        with urlopen(request, timeout=12, context=context) as response:
            final_url = response.geturl()
            raw = response.read(MAX_HTML_BYTES)
            html = raw.decode("utf-8", errors="ignore")
            html = unescape(html)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        error = exc.__class__.__name__
    except Exception as exc:  # pragma: no cover - defensive fallback
        error = exc.__class__.__name__

    return SiteDiagnosis(
        site=True,
        whatsapp=_looks_like_whatsapp(final_url, html),
        whatsapp_hints=extract_whatsapp_hints(final_url, html),
        agendamento=_looks_like_agendamento(final_url, html),
        instagram=_looks_like_instagram(final_url, html),
        formulario=_looks_like_form(html),
        url_final=final_url,
        erro=error,
    )


def infer_pain_and_offer(category: Any, diagnosis: SiteDiagnosis) -> tuple[str, str, str]:
    normalized = _normalize_text(category)
    has_site = diagnosis.site
    has_whatsapp = diagnosis.whatsapp
    has_schedule = diagnosis.agendamento
    has_form = diagnosis.formulario
    has_instagram = diagnosis.instagram

    if any(token in normalized for token in ("odont", "dental", "implantes", "ortodont")):
        if not has_schedule:
            return (
                "nao tem agendamento online e pode estar perdendo consultas para concorrentes com agenda digital",
                "sistema de agendamento online + landing page simples",
                "automacao",
            )
        if not has_whatsapp:
            return (
                "o atendimento inicial pode estar lento e depender de contato manual",
                "bot de WhatsApp com respostas automáticas",
                "automacao",
            )
        if not has_form:
            return (
                "o site nao captura leads de forma clara",
                "landing page de conversao com captura de contatos",
                "landing_page",
            )
        return (
            "a presença digital existe, mas ainda da para aumentar conversao e previsibilidade",
            "landing page de conversao + automacao basica",
            "landing_page",
        )

    if any(token in normalized for token in ("veter", "animal hospital", "pet")):
        if not has_schedule:
            return (
                "nao existe agenda online para consultas e retornos",
                "sistema de agendamento online + lembretes",
                "automacao",
            )
        if not has_whatsapp:
            return (
                "o primeiro contato pode estar sendo perdido no atendimento manual",
                "bot de WhatsApp para triagem e atendimento",
                "automacao",
            )
        return (
            "ha oportunidade de melhorar a captura de consultas e organizacao do atendimento",
            "landing page simples + automacao de captacao",
            "landing_page",
        )

    if any(token in normalized for token in ("imobili", "real estate", "property")):
        if not has_form:
            return (
                "o site nao parece capturar leads de forma estruturada",
                "landing page com formulario + integracao com CRM",
                "landing_page",
            )
        if not has_whatsapp:
            return (
                "a velocidade de resposta pode estar abaixo do ideal para leads quentes",
                "bot de WhatsApp para resposta imediata",
                "automacao",
            )
        return (
            "existe potencial para aumentar conversao com funil mais direto",
            "landing page + automacao de captura de leads",
            "landing_page",
        )

    if any(token in normalized for token in ("barbear", "barber")):
        if not has_whatsapp:
            return (
                "o canal principal de atendimento pode estar ausente ou pouco evidente",
                "bot de WhatsApp para agendamento e atendimento",
                "automacao",
            )
        if not has_schedule:
            return (
                "o fluxo de agendamento pode estar manual demais",
                "sistema simples de agendamento",
                "automacao",
            )
        return (
            "ha oportunidade de vender mais com pagina simples e melhor captura de clientes",
            "landing page com chamada para agendamento",
            "landing_page",
        )

    if any(token in normalized for token in ("academia", "gym", "fitness", "personal trainer")):
        if not has_form:
            return (
                "o site nao parece transformar visitas em leads ou aulas experimentais",
                "landing page com captura de interessados",
                "landing_page",
            )
        if not has_schedule:
            return (
                "a jornada de conversao pode estar sem agendamento ou teste gratuito claro",
                "pagina de oferta com agendamento rapido",
                "landing_page",
            )
        return (
            "existe oportunidade para ampliar conversao de visitantes em matrículas",
            "landing page de conversao + automacao simples",
            "landing_page",
        )

    if has_site and not has_form:
        return (
            "o site existe, mas a captacao de lead parece fraca",
            "landing page simples com formulario e WhatsApp",
            "landing_page",
        )

    if has_site and not has_whatsapp:
        return (
            "o contato rapido pode estar pouco visivel",
            "bot de WhatsApp e respostas automaticas",
            "automacao",
        )

    if has_site and not has_instagram:
        return (
            "a presenca social pode estar subutilizada",
            "estrutura simples de links e captacao",
            "landing_page",
        )

    return (
        "nao foi possivel detectar sinais fortes de automacao no canal principal",
        "landing page simples com WhatsApp e formulario",
        "landing_page",
    )
