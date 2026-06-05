from __future__ import annotations

import csv
import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INPUT_FILE = ROOT / "inputs" / "buscas_google_maps.txt"
OUTPUT_DIR = ROOT / "outputs"
RAW_OUTPUT = OUTPUT_DIR / "leads_raw.csv"
FINAL_OUTPUT = OUTPUT_DIR / "leads.csv"


def ensure_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INPUT_FILE.parent.mkdir(parents=True, exist_ok=True)


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def pull_image() -> None:
    run(["docker", "--context", "default", "pull", "gosom/google-maps-scraper"])


def scrape() -> None:
    run(
        [
            "docker",
            "--context",
            "default",
            "run",
            "--rm",
            "-v",
            "gmaps-playwright-cache:/opt",
            "-v",
            f"{INPUT_FILE}:/queries.txt:ro",
            "-v",
            f"{OUTPUT_DIR}:/out",
            "gosom/google-maps-scraper",
            "-input",
            "/queries.txt",
            "-results",
            "/out/leads_raw.csv",
            "-depth",
            "1",
            "-exit-on-inactivity",
            "3m",
        ]
    )


def normalize_csv() -> None:
    if not RAW_OUTPUT.exists():
        raise FileNotFoundError(f"Arquivo bruto nao encontrado: {RAW_OUTPUT}")

    field_aliases = {
        "nome": ["title", "name"],
        "telefone": ["phone"],
        "site": ["website", "site"],
        "endereco": ["address", "complete_address"],
        "avaliacoes": ["review_count", "reviews", "reviewcount"],
        "nota": ["review_rating", "rating"],
        "categoria": ["category"],
    }

    with RAW_OUTPUT.open("r", encoding="utf-8", newline="") as src, FINAL_OUTPUT.open(
        "w", encoding="utf-8", newline=""
    ) as dst:
        reader = csv.DictReader(src)
        writer = csv.DictWriter(
            dst,
            fieldnames=["nome", "telefone", "site", "endereco", "avaliacoes", "nota", "categoria"],
        )
        writer.writeheader()

        for row in reader:
            normalized = {}
            for target, aliases in field_aliases.items():
                value = ""
                for alias in aliases:
                    if alias in row and row[alias]:
                        value = row[alias]
                        break
                normalized[target] = value
            writer.writerow(normalized)


def main(run_scrape: bool = True) -> None:
    ensure_dirs()
    if run_scrape:
        pull_image()
        scrape()
    normalize_csv()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--normalize-only",
        action="store_true",
        help="Gera o CSV final a partir do leads_raw.csv existente sem rodar o scraper.",
    )
    args = parser.parse_args()
    main(run_scrape=not args.normalize_only)
