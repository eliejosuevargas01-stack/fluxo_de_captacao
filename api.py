from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import requests
import time
from datetime import datetime

from meta_ads_pipeline import load_cards, enrich_card
from models import build_webhook_payload

app = FastAPI(title="Lead Extraction API")

@app.get("/")
async def root() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "Lead Extraction API",
        "message": "API is running",
    }

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
        cards = load_cards(request.queries, request.max_results)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Captados {len(cards)} anúncios brutos")

        unique_cards = {}
        for card in cards:
            key = card.ad_library_id or card.raw_hash
            unique_cards[key] = card

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {len(unique_cards)} anúncios únicos após deduplicação")
        final_report = []
        webhook_scrapper = "https://myn8n.seommerce.shop/webhook/scrapper"
        webhook_resposta = "https://myn8n.seommerce.shop/webhook/resposta-lead"

        for card in unique_cards.values():
            enriched = enrich_card(card)
            
            # Filtra por plataforma se solicitado
            if request.target_platform == "whatsapp":
                has_wa = (enriched.get("contact_has_whatsapp") == "sim" or enriched.get("destination_type") == "whatsapp")
                if not has_wa:
                    continue

            test_results = None

            # Testa velocidade de resposta apenas se há intenção de mensagem (WhatsApp, Instagram, FB detectado)
            cta_text = str(enriched.get("cta_text", "")).lower()
            dest_type = enriched.get("destination_type", "")
            intent_is_chat = "mensagem" in cta_text or "whatsapp" in cta_text or dest_type in ["whatsapp", "instagram_profile", "facebook_page"]

            if dest_type in ["whatsapp", "instagram_profile", "facebook_page"] and intent_is_chat:
                try:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Testando velocidade de resposta para: {enriched.get('contact_domain', 'unknown')}")
                    resp = requests.post(webhook_resposta, json=enriched, timeout=30)
                    if resp.status_code == 200:
                        test_results = resp.json()
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Resposta recebida de: {enriched.get('contact_domain', 'unknown')}")
                except Exception as e:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Erro ao testar resposta: {e}")
                
                # Aguarda 5 segundos entre requisições para evitar sobrecarga (502 Bad Gateway) no Evolution API do VPS
                time.sleep(5)

            payload = build_webhook_payload(enriched, test_results)
            final_report.append(payload)

        try:
            requests.post(request.webhook_url or webhook_scrapper, json={"leads": final_report}, timeout=30)
        except Exception as e:
            print(f"Error sending to webhook: {e}")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] Scrape Meta Ads finalizado! Total: {len(final_report)} leads. Duração: {duration:.1f}s")

    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Erro ao processar Meta Ads: {e}")

@app.post("/scrape/meta_ads")
async def scrape_meta_ads(request: ScrapeRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_meta_ads, request)
    return {"status": "accepted", "message": "Scraping meta ads in background"}

@app.post("/scrape/google_maps")
async def scrape_google_maps(request: ScrapeRequest):
    # Placeholder as collectors/google_maps.py is empty
    return {"status": "not_implemented", "message": "Google Maps collector is not yet implemented"}
