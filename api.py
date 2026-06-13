from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import requests
import time
from datetime import datetime
import os
import subprocess
import csv

from meta_ads_pipeline import load_cards, enrich_card
from collectors.facebook_ads_library import scrape_query
from collectors.gmaps_scraper import scrape_maps
from models import build_webhook_payload, build_gmaps_webhook_payload
from lead_pipeline import qualify_leads, diagnose_top_leads

app = FastAPI(title="Lead Extraction API")

from fastapi.responses import FileResponse

@app.get("/")
async def root():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "index.html not found"}

@app.get("/index.html")
async def index():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "index.html not found"}

@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

class ScrapeRequest(BaseModel):
    queries: List[str]
    max_results: int = 10
    webhook_url: Optional[str] = None
    target_platform: Optional[str] = None
    min_results: Optional[int] = None

def process_meta_ads(request: ScrapeRequest):
    start_time = datetime.now()
    print(f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] Iniciando scrape Meta Ads...")
    try:
        # Define os limites globais
        max_total = request.max_results if request.max_results else 20
        min_total = request.min_results if request.min_results else 5
        target_platform = request.target_platform
        
        unique_leads = {}
        final_report = []
        
        webhook_scrapper = "https://myn8n.seommerce.shop/webhook/scrapper"
        webhook_resposta = "https://myn8n.seommerce.shop/webhook/resposta-lead"

        for query in request.queries:
            # Se já atingiu o limite máximo total, interrompe as buscas
            if len(final_report) >= max_total:
                break
            
            # Limita a busca da query atual para não passar do máximo restante
            remaining_limit = max_total - len(final_report)
            actual_query = query.split(":", 1)[1].strip() if query.startswith("page:") else query
            
            try:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Buscando query: '{actual_query}' (restante necessário: {remaining_limit})...")
                cards = scrape_query(actual_query, country="BR", max_scrolls=8, max_results=remaining_limit)
            except Exception as e:
                print(f"Erro ao buscar query '{actual_query}': {e}")
                continue

            for card in cards:
                key = card.ad_library_id or card.raw_hash
                if key in unique_leads:
                    continue

                dest_url = card.destination_url or ""
                dest_url_lower = dest_url.lower()
                is_wa = "wa.me" in dest_url_lower or "api.whatsapp.com" in dest_url_lower or "whatsapp.com" in dest_url_lower or "whatsapp://" in dest_url_lower
                is_social = is_wa or "instagram.com" in dest_url_lower or "facebook.com" in dest_url_lower

                # If target_platform is whatsapp, button must direct directly to whatsapp
                if target_platform == "whatsapp" and not is_wa:
                    continue

                # If target_platform is site_externo, button must be an external site (non-social)
                if target_platform == "site_externo" and (is_social or not dest_url):
                    continue

                enriched = enrich_card(card)
                
                # Filtra apenas leads que tenham telefone ou email
                has_phone = bool(enriched.get("contact_phone"))
                has_email = bool(enriched.get("contact_email"))
                if not (has_phone or has_email):
                    continue

                unique_leads[key] = card
                test_results = None

                payload = build_webhook_payload(enriched, test_results, target_platform)
                final_report.append(payload)
                
                # Se alcançou o máximo, para de processar os cards
                if len(final_report) >= max_total:
                    break

        try:
            requests.post(request.webhook_url or webhook_scrapper, json={"leads": final_report}, timeout=30)
        except Exception as e:
            print(f"Error sending to webhook: {e}")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] Scrape Meta Ads finalizado! Total enviado: {len(final_report)} leads. Duração: {duration:.1f}s")

    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Erro ao processar Meta Ads: {e}")

@app.post("/scrape/meta_ads")
async def scrape_meta_ads(request: ScrapeRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_meta_ads, request)
    return {"status": "accepted", "message": "Scraping meta ads in background"}

def process_google_maps(request: ScrapeRequest):
    start_time = datetime.now()
    print(f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] Iniciando scrape Google Maps...")
    try:
        input_file = os.path.join("inputs", "buscas_google_maps_api.txt")
        os.makedirs(os.path.dirname(input_file), exist_ok=True)
        with open(input_file, "w", encoding="utf-8") as f:
            for q in request.queries:
                f.write(q + "\n")
        
        print(f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] Iniciando scrape Google Maps nativo...")
        
        raw_leads = []
        for query in request.queries:
            results = scrape_maps(query, request.max_results)
            raw_leads.extend(results)
            
        max_total = request.max_results if request.max_results else 20
        
        # Rodar pipelines em memória
        enriched, top_leads = qualify_leads(raw_leads, max_total)
        diagnosed = diagnose_top_leads(top_leads)

        # Montar os payloads WebhookPayload estruturados
        final_report = []
        for lead in diagnosed:
            payload = build_gmaps_webhook_payload(lead)
            final_report.append(payload)

        # Enviar para o webhook
        webhook_scrapper = "https://myn8n.seommerce.shop/webhook/scrapper"
        url = request.webhook_url or webhook_scrapper
        print(f"Enviando {len(final_report)} leads para o webhook {url}...")
        requests.post(url, json={"leads": final_report}, timeout=30)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] Scrape Google Maps finalizado! Duração: {duration:.1f}s")
        
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Erro ao processar Google Maps: {e}")

@app.post("/scrape/google_maps")
async def scrape_google_maps(request: ScrapeRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_google_maps, request)
    return {"status": "accepted", "message": "Scraping google maps in background"}

