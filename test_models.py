from models import build_webhook_payload

dummy_card = {
    "ad_library_id": "12345",
    "raw_hash": "hash123",
    "gap": "Missing CTA",
    "contact_has_form": "nao",
    "contact_has_whatsapp": "sim",
    "destination_type": "whatsapp",
    "destination_clean_url": "https://wa.me/5511999999999",
    "score": 150,
    "offer": "Bot WhatsApp",
    "niche": "veterinaria",
    "page_name": "Vet Clinic",
    "page_url": "https://facebook.com/vet",
    "search_url": "https://search.com",
    "start_date": "2023-01-01",
    "platforms": "instagram, facebook",
    "destination_url": "https://example.com/click"
}

dummy_test_results = {
    "demorou_responder": True,
    "tempo_segundos_primeira_resposta": 3600,
    "classificacao_atendimento": "demorado",
    "foi_resposta_automatica": False,
    "conteudo_resposta_automatica": None,
    "teve_qualificacao_ou_triagem": False,
    "mandou_link_agendamento": False,
    "plataforma_testada": "whatsapp"
}

payload = build_webhook_payload(dummy_card, dummy_test_results)
import json
print(json.dumps(payload, indent=2))
