from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from collectors.analyzers.funnel_analyzer import (
    build_offer,
    build_proposal,
    infer_niche,
    inspect_destination,
)
from collectors.facebook_ads_library import MetaAdCard, scrape_query


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "inputs" / "meta_ads_queries.txt"
DEFAULT_OUTPUT_DIR = ROOT / "outputs"


def load_queries(path: Path) -> list[str]:
    queries: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#"):
            continue
        queries.append(cleaned)
    return queries


def load_cards(queries: list[str], max_results: int) -> list[MetaAdCard]:
    cards: list[MetaAdCard] = []
    for query in queries:
        actual_query = query.split(":", 1)[1].strip() if query.startswith("page:") else query
        cards.extend(scrape_query(actual_query, country="BR", max_scrolls=8, max_results=max_results))
    return cards


def flatten(text: Any) -> str:
    return " ".join(str(text or "").split())


def enrich_card(card: MetaAdCard) -> dict[str, Any]:
    signals = inspect_destination(card.destination_url or card.page_url)
    niche = infer_niche(card.query, card.page_name, card.ad_text, card.destination_url, card.cta_text)
    gap, offer, offer_type, score = build_offer(niche, signals, card.ad_status)
    proposal = build_proposal(card.page_name or "oi", gap, offer)
    contact_url = signals.clean_url if signals.clean_url else (card.destination_url or card.page_url)

    return {
        "query": card.query,
        "search_url": card.search_url,
        "ad_library_id": card.ad_library_id,
        "page_name": card.page_name,
        "page_url": card.page_url,
        "start_date": card.start_date,
        "ad_status": card.ad_status,
        "platforms": card.platforms,
        "ad_text": flatten(card.ad_text),
        "cta_text": flatten(card.cta_text),
        "destination_url": card.destination_url,
        "destination_domain": card.destination_domain,
        "destination_type": signals.destination_type,
        "destination_clean_url": signals.clean_url,
        "contact_url": contact_url,
        "contact_domain": signals.domain,
        "contact_title": signals.title,
        "contact_has_whatsapp": "sim" if signals.has_whatsapp else "nao",
        "contact_has_form": "sim" if signals.has_form else "nao",
        "contact_has_booking": "sim" if signals.has_booking else "nao",
        "contact_has_instagram": "sim" if signals.has_instagram else "nao",
        "contact_has_phone": "sim" if signals.has_phone else "nao",
        "contact_has_email": "sim" if signals.has_email else "nao",
        "contact_error": signals.error,
        "status_code": signals.status_code,
        "prefilled_message": signals.prefilled_message,
        "niche": niche,
        "gap": flatten(gap),
        "offer": flatten(offer),
        "offer_type": offer_type,
        "proposal": flatten(proposal),
        "score": score,
        "raw_hash": card.raw_hash,
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    start_time = datetime.now()
    print(f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] Iniciando scrape Meta Ads...")

    parser = argparse.ArgumentParser(description="Coleta anuncios do Meta Ads Library e aponta falhas de funil.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Arquivo com queries de busca.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Diretorio de saida.")
    parser.add_argument("--max-results", type=int, default=1000, help="Limite maximo de anuncios por query.")
    args = parser.parse_args()

    queries = load_queries(args.input)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Carregadas {len(queries)} queries")

    cards = load_cards(queries, args.max_results)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Captados {len(cards)} anúncios brutos")

    unique: dict[str, MetaAdCard] = {}
    for card in cards:
        unique[card.ad_library_id or card.raw_hash] = card

    enriched = [enrich_card(card) for card in unique.values()]
    enriched.sort(key=lambda row: (int(row.get("score") or 0), str(row.get("start_date") or ""), str(row.get("page_name") or "")), reverse=True)

    raw_fields = list(asdict(cards[0]).keys()) if cards else []
    enriched_fields = [
        "query",
        "search_url",
        "ad_library_id",
        "page_name",
        "page_url",
        "start_date",
        "ad_status",
        "platforms",
        "ad_text",
        "cta_text",
        "destination_url",
        "destination_domain",
        "destination_type",
        "destination_clean_url",
        "contact_url",
        "contact_domain",
        "contact_title",
        "contact_has_whatsapp",
        "contact_has_form",
        "contact_has_booking",
        "contact_has_instagram",
        "contact_has_phone",
        "contact_has_email",
        "contact_error",
        "niche",
        "gap",
        "offer",
        "offer_type",
        "proposal",
        "score",
    ]

    raw_rows = [asdict(card) for card in cards]
    write_csv(args.output_dir / "meta_ads_raw.csv", raw_rows, raw_fields or enriched_fields)
    write_csv(args.output_dir / "meta_ads_opportunities.csv", enriched, enriched_fields)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] Scrape Meta Ads finalizado! Total: {len(enriched)} leads. Duração: {duration:.1f}s")


if __name__ == "__main__":
    main()
