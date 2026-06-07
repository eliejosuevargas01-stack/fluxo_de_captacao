from collectors.analyzers.funnel_analyzer import inspect_destination
from models import build_webhook_payload

url = "https://wa.me/551199999?text=Quero%20agendar"
sig = inspect_destination(url)

card = {
    "destination_type": sig.destination_type,
    "contact_has_whatsapp": "sim",
    "prefilled_message": sig.prefilled_message
}
payload = build_webhook_payload(card)
print("Mensagem extraida do FunnelSignals:", sig.prefilled_message)
print("Mensagem no Payload JSON:", payload["funil_whatsapp_direct"]["mensagem_pre_preenchida"])
