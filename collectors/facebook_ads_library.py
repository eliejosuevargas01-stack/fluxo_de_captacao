from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


AD_LIBRARY_BASE = "https://www.facebook.com/ads/library/"


@dataclass(frozen=True)
class MetaAdCard:
    query: str
    search_url: str
    ad_library_id: str
    page_name: str
    page_url: str
    start_date: str
    ad_status: str
    platforms: str
    ad_text: str
    cta_text: str
    destination_url: str
    destination_domain: str
    raw_text: str
    raw_hash: str


def build_search_url(query: str, country: str = "BR", search_type: str = "keyword_unordered") -> str:
    params = {
        "active_status": "active",
        "ad_type": "all",
        "country": country,
        "is_targeted_country": "false",
        "media_type": "all",
        "q": query,
        "search_type": search_type,
        "sort_data[mode]": "total_impressions",
        "sort_data[direction]": "desc",
    }
    return AD_LIBRARY_BASE + "?" + "&".join(f"{quote_plus(str(k))}={quote_plus(str(v))}" for k, v in params.items())


def resolve_facebook_redirect(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.endswith("l.facebook.com"):
        params = parse_qs(parsed.query)
        if "u" in params and params["u"]:
            return unquote(params["u"][0])
    return url


def _normalize_href(href: str) -> str:
    if not href:
        return ""
    href = resolve_facebook_redirect(href)
    if href.startswith("//"):
        return f"https:{href}"
    if href.startswith("/"):
        return f"https://www.facebook.com{href}"
    return href


def _domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower().replace("www.", "")


def _extract_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()


def _find_best_external_href(card) -> tuple[str, str]:
    anchors = card.locator("a")
    candidates = []
    for idx in range(anchors.count()):
        a = anchors.nth(idx)
        href = _normalize_href(a.get_attribute("href") or "")
        if not href:
            continue
        domain = _domain(href)
        if "facebook.com" in domain and "l.facebook.com" not in href:
            continue
        if domain:
            candidates.append((href, domain))
            
    if not candidates:
        return "", ""
        
    # Priority 1: WhatsApp domains
    for href, domain in candidates:
        if "wa.me" in domain or "whatsapp.com" in domain:
            return href, domain
            
    # Priority 2: General websites (non-social, non-facebook, non-instagram)
    social_keywords = ["instagram.com", "facebook.com", "youtube.com", "twitter.com", "linkedin.com", "tiktok.com", "pinterest.com"]
    for href, domain in candidates:
        if not any(kw in domain for kw in social_keywords):
            return href, domain
            
    # Priority 3: Instagram/social profiles
    for href, domain in candidates:
        if "instagram.com" in domain:
            return href, domain
            
    # Fallback to the first available candidate
    return candidates[0]


def _find_page_href(card) -> str:
    anchors = card.locator("a")
    for idx in range(anchors.count()):
        a = anchors.nth(idx)
        href = _normalize_href(a.get_attribute("href") or "")
        if not href:
            continue
        domain = _domain(href)
        if "facebook.com" in domain and "ads/library" not in href and "l.facebook.com" not in href:
            return href
    return ""


def _best_cta_text(card) -> str:
    ignore = {
        "Abrir menu suspenso",
        "Ver detalhes do anúncio",
        "Reproduzir o vídeo",
        "Reproduzir",
        "Configurações",
        "Entrar no modo de tela cheia",
        "Reativar",
    }
    priority = (
        "Enviar mensagem pelo WhatsApp",
        "Acessar o perfil do Instagram",
        "Saiba mais",
        "Enviar mensagem",
        "Ligar agora",
        "Abrir link",
        "Ver mais",
    )
    buttons = card.get_by_role("button")
    cleaned: list[str] = []
    for idx in range(buttons.count()):
        text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", buttons.nth(idx).inner_text())
        text = " ".join(text.split())
        if not text or text in ignore:
            continue
        cleaned.append(text)
    for preferred in priority:
        for text in cleaned:
            if preferred.lower() in text.lower():
                return text
    if cleaned:
        return cleaned[0]
    return ""


def _split_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and line.strip() != "\u200b"]


def _extract_page_name(lines: list[str]) -> str:
    try:
        idx = lines.index("Patrocinado")
        if idx > 0:
            return lines[idx - 1]
    except ValueError:
        pass
    try:
        idx = lines.index("Ver detalhes do anúncio")
        if idx + 1 < len(lines):
            return lines[idx + 1]
    except ValueError:
        pass
    return ""


def _extract_start_date(text: str) -> str:
    match = re.search(r"Veiculação iniciada em\s+([^\n]+)", text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _extract_library_id(text: str) -> str:
    match = re.search(r"Identificação da biblioteca:\s*(\d+)", text, flags=re.IGNORECASE)
    return match.group(1) if match else ""


def _extract_status(text: str) -> str:
    if "Ativo" in text:
        return "active"
    if "Inativo" in text:
        return "inactive"
    return "unknown"


def _extract_platforms(lines: list[str]) -> str:
    # The UI is noisy; keep the first obvious platform tokens we can find.
    candidates = []
    for line in lines:
        upper = line.upper()
        if upper in {"FACEBOOK.COM", "INSTAGRAM.COM", "WHATSAPP.COM", "MESSENGER.COM"}:
            candidates.append(line.lower().replace(".com", ""))
    return ", ".join(dict.fromkeys(candidates))


def _extract_ad_text(lines: list[str]) -> str:
    if "Patrocinado" not in lines:
        return ""
    start = lines.index("Patrocinado") + 1
    stop_tokens = {
        "INSTAGRAM.COM",
        "FACEBOOK.COM",
        "WHATSAPP.COM",
        "MESSENGER.COM",
        "Acessar o perfil do Instagram",
        "Enviar mensagem pelo WhatsApp",
        "Saiba mais",
        "Abrir link",
        "Ver mais",
    }
    collected: list[str] = []
    for line in lines[start:]:
        if line in stop_tokens:
            break
        if line.upper() in stop_tokens:
            break
        if line.startswith("0:") and "/" in line:
            break
        collected.append(line)
    return "\n".join(collected).strip()


def parse_ad_card(card, query: str, search_url: str) -> MetaAdCard:
    raw_text = card.inner_text()
    lines = _split_lines(raw_text)
    page_name = _extract_page_name(lines)
    library_id = _extract_library_id(raw_text)
    start_date = _extract_start_date(raw_text)
    ad_status = _extract_status(raw_text)
    platforms = _extract_platforms(lines)
    ad_text = _extract_ad_text(lines)
    cta_text = _best_cta_text(card)
    page_url = _find_page_href(card)
    destination_url, destination_domain = _find_best_external_href(card)
    return MetaAdCard(
        query=query,
        search_url=search_url,
        ad_library_id=library_id,
        page_name=page_name,
        page_url=page_url,
        start_date=start_date,
        ad_status=ad_status,
        platforms=platforms,
        ad_text=ad_text,
        cta_text=cta_text,
        destination_url=destination_url,
        destination_domain=destination_domain,
        raw_text=raw_text,
        raw_hash=_extract_hash(raw_text),
    )


def scrape_query(
    query: str,
    country: str = "BR",
    max_scrolls: int = 8,
    max_results: int = 200,
) -> list[MetaAdCard]:
    search_url = build_search_url(query, country=country)
    collected: list[MetaAdCard] = []
    seen_ids: set[str] = set()
    seen_hashes: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1600})
        page.goto(search_url, wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(5000)

        stale_rounds = 0
        previous_total = 0
        for _ in range(max_scrolls):
            try:
                cards = page.get_by_text("Ver detalhes do anúncio")
                total = cards.count()
                for idx in range(total):
                    card = cards.nth(idx).locator("xpath=ancestor::*[6]")
                    if card.count() == 0:
                        continue
                    ad = parse_ad_card(card, query=query, search_url=search_url)
                    key = ad.ad_library_id or ad.raw_hash
                    if key in seen_ids or ad.raw_hash in seen_hashes:
                        continue
                    if not ad.page_name and not ad.ad_text:
                        continue
                    seen_ids.add(key)
                    seen_hashes.add(ad.raw_hash)
                    collected.append(ad)
                    if len(collected) >= max_results:
                        browser.close()
                        return collected

                if len(collected) == previous_total:
                    stale_rounds += 1
                else:
                    stale_rounds = 0
                previous_total = len(collected)

                if stale_rounds >= 2:
                    break

                page.mouse.wheel(0, 2800)
                page.wait_for_timeout(1600)
            except PlaywrightTimeoutError:
                break
        browser.close()

    return collected
