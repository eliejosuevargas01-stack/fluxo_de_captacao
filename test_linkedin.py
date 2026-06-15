import json
from collectors.linkedin import scrape_linkedin_jobs
from models import build_linkedin_webhook_payload

def main():
    print("Iniciando teste de busca de vagas no LinkedIn para 'Python'...")
    jobs = scrape_linkedin_jobs("Python", location="Brasil", max_results=2)
    print(f"Total de vagas retornadas: {len(jobs)}")
    
    for idx, job in enumerate(jobs):
        print(f"\n=== VAGA {idx + 1} ===")
        print(f"Título: {job['titulo_vaga']}")
        print(f"Empresa: {job['nome_empresa']}")
        print(f"Local: {job['localizacao']}")
        print(f"Postagem: {job['data_publicacao']}")
        print(f"Contrato: {job['tipo_contrato']}")
        print(f"Senioridade: {job['senioridade']}")
        print(f"Junior Friendly: {job['junior_friendly']}")
        print(f"Match Score: {job['match_score']}")
        print(f"Requisitos Destaque: {job['requisitos_destacados']}")
        print(f"URL: {job['link_vaga']}")
        
        # Test models payload mapping
        payload = build_linkedin_webhook_payload(job)
        print("Webhook Payload JSON:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
