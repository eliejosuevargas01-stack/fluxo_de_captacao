from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import requests
import time
from datetime import datetime

from meta_ads_pipeline import load_cards, enrich_card
from collectors.facebook_ads_library import scrape_query
from models import build_webhook_payload, build_gmaps_webhook_payload
from lead_pipeline import qualify_leads, diagnose_top_leads

app = FastAPI(title="Lead Extraction API")

from fastapi.responses import FileResponse
import os

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
    objective: Optional[str] = None
    contact_channel: Optional[str] = None

def process_meta_ads(request: ScrapeRequest):
    start_time = datetime.now()
    print(f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] Iniciando scrape Meta Ads...")
    try:
        # Define os limites globais
        max_total = request.max_results if request.max_results else 20
        min_total = request.min_results if request.min_results else 5
        target_platform = request.target_platform
        objective = request.objective
        contact_channel = request.contact_channel

        # Palavras-chave que indicam intenção comercial direta
        commercial_ctas = [
            "orçamento", "orcamento", "cotação", "cotacao", "proposta",
            "chamar", "fale", "falar", "conversar", "mensagem", "dúvidas", "duvidas",
            "agendar", "marcar", "reservar", "consulta", "avaliação", "avaliacao", "visita",
            "demonstração", "demonstracao", "análise", "analise", "diagnóstico", "diagnostico",
            "consultoria", "simulação", "simulacao", "simular", "calcular", "condições", "condicoes",
            "comprar", "assinar"
        ]
        
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

                enriched = enrich_card(card)
                
                # 1. Filtra por target_platform (para onde o anúncio redireciona)
                if target_platform == "whatsapp":
                    dest_wa = (enriched.get("destination_type") == "whatsapp" or "wa.me" in str(enriched.get("destination_url", "")).lower() or "api.whatsapp.com" in str(enriched.get("destination_url", "")).lower())
                    if not dest_wa:
                        continue
                elif target_platform == "instagram":
                    dest_type = enriched.get("destination_type", "")
                    if dest_type != "instagram_profile" and "instagram.com" not in str(enriched.get("destination_url", "")).lower():
                        continue
                elif target_platform == "facebook":
                    dest_type = enriched.get("destination_type", "")
                    if dest_type != "facebook_page" and "facebook.com" not in str(enriched.get("destination_url", "")).lower() and "m.me" not in str(enriched.get("destination_url", "")).lower():
                        continue
                elif target_platform == "site_externo":
                    dest_type = enriched.get("destination_type", "")
                    has_url = bool(enriched.get("destination_url"))
                    if not (dest_type == "website" and has_url):
                        continue

                # 2. Filtra por contact_channel (qual o meio de contato exigido para o lead)
                if contact_channel == "whatsapp":
                    has_wa = (enriched.get("contact_has_whatsapp") == "sim" or enriched.get("destination_type") == "whatsapp" or "wa.me" in str(enriched.get("destination_url", "")).lower() or "api.whatsapp.com" in str(enriched.get("destination_url", "")).lower())
                    if not has_wa:
                        continue
                elif contact_channel == "phone":
                    if not enriched.get("contact_phone"):
                        continue
                elif contact_channel == "email":
                    if not enriched.get("contact_email"):
                        continue
                elif contact_channel == "instagram":
                    dest_type = enriched.get("destination_type", "")
                    if dest_type != "instagram_profile" and "instagram.com" not in str(enriched.get("destination_url", "")).lower():
                        continue
                elif contact_channel == "facebook":
                    dest_type = enriched.get("destination_type", "")
                    if dest_type != "facebook_page" and "facebook.com" not in str(enriched.get("destination_url", "")).lower() and "m.me" not in str(enriched.get("destination_url", "")).lower():
                        continue
                elif contact_channel == "any":
                    has_phone = bool(enriched.get("contact_phone"))
                    has_email = bool(enriched.get("contact_email"))
                    has_wa = (enriched.get("contact_has_whatsapp") == "sim" or enriched.get("destination_type") == "whatsapp" or "wa.me" in str(enriched.get("destination_url", "")).lower())
                    dest_type = enriched.get("destination_type", "")
                    has_social = dest_type in ["instagram_profile", "facebook_page"] or "instagram.com" in str(enriched.get("destination_url", "")).lower() or "facebook.com" in str(enriched.get("destination_url", "")).lower()
                    if not (has_phone or has_email or has_wa or has_social):
                        continue
                else:
                    # Default: se não especificar o contact_channel, exige ao menos telefone, email ou um canal direto social/zap
                    has_phone = bool(enriched.get("contact_phone"))
                    has_email = bool(enriched.get("contact_email"))
                    has_wa = (enriched.get("contact_has_whatsapp") == "sim" or enriched.get("destination_type") == "whatsapp" or "wa.me" in str(enriched.get("destination_url", "")).lower())
                    dest_type = enriched.get("destination_type", "")
                    has_social = dest_type in ["instagram_profile", "facebook_page"] or "instagram.com" in str(enriched.get("destination_url", "")).lower() or "facebook.com" in str(enriched.get("destination_url", "")).lower()
                    if not (has_phone or has_email or has_wa or has_social):
                        continue

                # Filtra por objetivo se solicitado (ex: comercial)
                if objective == "commercial":
                    cta_text = str(enriched.get("cta_text", "")).lower()
                    has_commercial_intent = any(word in cta_text for word in commercial_ctas)
                    if not has_commercial_intent:
                        continue

                unique_leads[key] = card
                test_results = None

                payload = build_webhook_payload(enriched, test_results)
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

import subprocess
import csv

def process_google_maps(request: ScrapeRequest):
    start_time = datetime.now()
    print(f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] Iniciando scrape Google Maps...")
    try:
        # 1. Escrever queries no arquivo de entrada
        input_file = os.path.join("inputs", "buscas_google_maps_api.txt")
        os.makedirs(os.path.dirname(input_file), exist_ok=True)
        with open(input_file, "w", encoding="utf-8") as f:
            for q in request.queries:
                f.write(q + "\n")
        
        # 2. Definir caminhos de saída
        output_dir = os.path.abspath("outputs")
        os.makedirs(output_dir, exist_ok=True)
        raw_output = os.path.join(output_dir, "leads_raw.csv")
        
        # Remover arquivo antigo se existir para evitar falsos positivos
        if os.path.exists(raw_output):
            try:
                os.remove(raw_output)
            except Exception:
                pass

        # 3. Rodar Docker do scraper
        print(f"Rodando docker gosom/google-maps-scraper para as queries...")
        cmd = [
            "docker", "--context", "default", "run", "--rm",
            "-v", "gmaps-playwright-cache:/opt",
            "-v", f"{os.path.abspath(input_file)}:/queries.txt:ro",
            "-v", f"{output_dir}:/out",
            "gosom/google-maps-scraper",
            "-input", "/queries.txt",
            "-results", "/out/leads_raw.csv",
            "-depth", "1",
            "-exit-on-inactivity", "3m"
        ]
        subprocess.run(cmd, check=True)
        
        # 4. Normalizar, qualificar e gerar payloads em memória
        if not os.path.exists(raw_output):
            raise FileNotFoundError("Scraper executado mas leads_raw.csv nao foi gerado.")

        print("Processando leads em memória (sem gravar CSV)...")
        field_aliases = {
            "nome": ["title", "name"],
            "telefone": ["phone"],
            "site": ["website", "site"],
            "endereco": ["address", "complete_address"],
            "avaliacoes": ["review_count", "reviews", "reviewcount"],
            "nota": ["review_rating", "rating"],
            "categoria": ["category"],
        }
        
        raw_leads = []
        with open(raw_output, "r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                normalized = {}
                for target, aliases in field_aliases.items():
                    value = ""
                    for alias in aliases:
                        if alias in row and row[alias]:
                            value = row[alias]
                            break
                    normalized[target] = value
                raw_leads.append(normalized)

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

