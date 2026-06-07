from collectors.analyzers.funnel_analyzer import inspect_destination

# Example of a redirect link that goes to whatsapp
# Bitly, linktr.ee, or generic shorteners might need real endpoints to test fully
# To simulate, we'll hit an endpoint that we know redirects to a domain that includes whatsapp or wa.me
# For the sake of this unit test logic, let's just make sure the attribute isn't throwing errors
# by testing the same dummy URL structure.

res = inspect_destination("https://wa.me/5519844915407")
print("Destination Type:", res.destination_type)
print("Is Web?", "website" == res.destination_type)
