from collectors.analyzers.funnel_analyzer import inspect_destination

# Test WhatsApp parsing with prefilled message
res = inspect_destination("https://wa.me/5511999999999?text=Hello%20World")
print("Destination Type:", res.destination_type)
print("Prefilled Msg:", res.prefilled_message)
