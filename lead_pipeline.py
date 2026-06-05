from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from collectors.analyzers.lead_score import parse_float, parse_int, score_lead
from collectors.analyzers.pain_detector import (
    diagnose_site,
    infer_pain_and_offer,
    normalize_brazil_whatsapp_number,
    normalize_phone_digits,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "outputs" / "leads.csv"
DEFAULT_OUTPUT_DIR = ROOT / "outputs"


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def load_leads(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return [dict(row) for row in reader]


def first_name(name: str) -> str:
    value = _clean(name)
    if not value:
        return ""
    return value.split()[0]


def phone_type(phone: Any) -> str:
    digits = normalize_phone_digits(phone)
    if len(digits) == 11 and digits[2] == "9":
        return "celular"
    if len(digits) in (10, 11):
        return "fixo" if len(digits) == 10 else "celular"
    return "desconhecido"


def infer_phone_whatsapp_status(phone: Any, diagnosis=None) -> str:
    digits = normalize_phone_digits(phone)
    if not digits:
        return "desconhecido"

    if diagnosis is not None:
        hint_numbers = set(getattr(diagnosis, "whatsapp_hints", ()) or ())
        normalized = normalize_brazil_whatsapp_number(phone)
        if normalized and (normalized in hint_numbers or digits in hint_numbers):
            return "sim"

    if len(digits) == 11 and digits[2] == "9":
        return "provavel"
    if len(digits) in (10, 11):
        return "indefinido"
    return "desconhecido"


def build_message(company: str, pain: str, offer: str, price: str = "R$ 300") -> str:
    return (
        f"Oi, {company}, tudo certo? Analisei sua presença digital e percebi que {pain}. "
        f"Posso te entregar {offer} por {price}, com pagamento 100% após a entrega e prazo de 24h. "
        f"Se fizer sentido, eu te mando o resumo e já começo."
    )


def qualify_leads(leads: list[dict[str, Any]], top_n: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    enriched: list[dict[str, Any]] = []

    for row in leads:
        score = score_lead(row)
        reviews = parse_int(row.get("avaliacoes") or row.get("reviews"))
        rating = parse_float(row.get("nota") or row.get("rating"))

        enriched_row = dict(row)
        enriched_row["reviews"] = reviews
        enriched_row["rating"] = rating
        enriched_row["score"] = score.score
        enriched_row["tem_site"] = "sim" if score.tem_site else "nao"
        enriched_row["segmento_peso"] = score.segmento_peso
        enriched_row["telefone_tipo"] = phone_type(row.get("telefone"))
        enriched_row["whatsapp_telefone"] = infer_phone_whatsapp_status(row.get("telefone"))
        enriched.append(enriched_row)

    enriched.sort(
        key=lambda item: (
            int(item.get("score") or 0),
            int(item.get("reviews") or 0),
            float(item.get("rating") or 0),
            _clean(item.get("nome")).lower(),
        ),
        reverse=True,
    )

    return enriched, enriched[:top_n]


def diagnose_top_leads(top_leads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    diagnosed: list[dict[str, Any]] = []
    for row in top_leads:
        diagnosis = diagnose_site(row.get("site"))
        pain, offer, offer_type = infer_pain_and_offer(row.get("categoria"), diagnosis)
        company = _clean(row.get("nome")) or "lead"
        message = build_message(company=company, pain=pain, offer=offer)

        out = dict(row)
        out["site_valido"] = "sim" if diagnosis.site else "nao"
        out["whatsapp"] = "sim" if diagnosis.whatsapp else "nao"
        out["whatsapp_telefone"] = infer_phone_whatsapp_status(row.get("telefone"), diagnosis)
        out["agendamento"] = "sim" if diagnosis.agendamento else "nao"
        out["instagram"] = "sim" if diagnosis.instagram else "nao"
        out["formulario"] = "sim" if diagnosis.formulario else "nao"
        out["url_final"] = diagnosis.url_final
        out["erro_diagnostico"] = diagnosis.erro
        out["dor"] = pain
        out["oferta"] = offer
        out["tipo_oferta"] = offer_type
        out["mensagem"] = message
        diagnosed.append(out)

    return diagnosed


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Qualifica, rankeia e diagnostica leads automaticamente.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="CSV de entrada com leads.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Diretorio de saida.")
    parser.add_argument("--top-n", type=int, default=50, help="Quantidade de leads para diagnostico/proposta.")
    args = parser.parse_args()

    leads = load_leads(args.input)
    enriched, top_leads = qualify_leads(leads, args.top_n)
    diagnosed = diagnose_top_leads(top_leads)

    scored_path = args.output_dir / "leads_qualificados.csv"
    top_path = args.output_dir / "leads_top50.csv"
    proposals_path = args.output_dir / "propostas.csv"

    scored_fields = [
        "nome",
        "telefone",
        "site",
        "endereco",
        "reviews",
        "nota",
        "rating",
        "categoria",
        "tem_site",
        "segmento_peso",
        "telefone_tipo",
        "whatsapp_telefone",
        "score",
    ]

    top_fields = scored_fields + [
        "site_valido",
        "whatsapp",
        "whatsapp_telefone",
        "agendamento",
        "instagram",
        "formulario",
        "url_final",
        "erro_diagnostico",
        "dor",
        "oferta",
        "tipo_oferta",
        "mensagem",
    ]

    proposal_fields = [
        "nome",
        "telefone",
        "score",
        "dor",
        "oferta",
        "mensagem",
    ]

    write_csv(scored_path, enriched, scored_fields)
    write_csv(top_path, diagnosed, top_fields)
    write_csv(proposals_path, diagnosed, proposal_fields)


if __name__ == "__main__":
    main()
