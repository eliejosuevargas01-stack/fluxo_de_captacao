from collectors.analyzers.funnel_analyzer import build_offer, FunnelSignals

signals = FunnelSignals(
    destination_type="whatsapp",
    clean_url="https://wa.me/5511999999999",
    domain="wa.me",
    has_whatsapp=True,
    has_form=False,
    has_booking=False,
    has_instagram=False,
    has_phone=False,
    has_email=False,
    title="",
    error=""
)

gap, offer, kind, score = build_offer("veterinaria", signals, "active")
print("=== Dummy Lead 1: WhatsApp without form (Veterinaria) ===")
print("Gap:", gap)
print("Offer:", offer)
print("Score:", score)
print()

signals2 = FunnelSignals(
    destination_type="instagram_profile",
    clean_url="https://instagram.com/clinicaxyz",
    domain="instagram.com",
    has_whatsapp=False,
    has_form=False,
    has_booking=False,
    has_instagram=True,
    has_phone=False,
    has_email=False,
    title="",
    error=""
)

gap2, offer2, kind2, score2 = build_offer("odontologia", signals2, "active")
print("=== Dummy Lead 2: Instagram profile (Odontologia) ===")
print("Gap:", gap2)
print("Offer:", offer2)
print("Score:", score2)
print()

signals3 = FunnelSignals(
    destination_type="website",
    clean_url="https://imobiliaria-ruim.com",
    domain="imobiliaria-ruim.com",
    has_whatsapp=False,
    has_form=False,
    has_booking=False,
    has_instagram=False,
    has_phone=False,
    has_email=False,
    title="",
    error=""
)

gap3, offer3, kind3, score3 = build_offer("imobiliaria", signals3, "active")
print("=== Dummy Lead 3: Website without form (Imobiliaria) ===")
print("Gap:", gap3)
print("Offer:", offer3)
print("Score:", score3)
