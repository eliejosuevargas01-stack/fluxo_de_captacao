from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Empresa(BaseModel):
    nome: str
    telefone_contato: Optional[str] = None
    email_contato: Optional[str] = None
    instagram_url: Optional[str] = None
    facebook_page_url: Optional[str] = None
    localizacao: str = ""

class AnaliseAnuncio(BaseModel):
    id_anuncio_meta: str
    link_biblioteca_anuncios: str
    data_inicio_veiculacao: str
    plataformas_veiculadas: List[str]
    link_destino_botao: str

class ErrosIdentificadosSite(BaseModel):
    fora_do_ar: bool = False
    nao_carrega_no_mobile: bool = False
    nao_possui_formulario_captura: bool = False
    nao_possui_pixel_meta: bool = False
    nao_possui_botao_whatsapp: bool = False
    layout_antigo_quebrado: bool = False

class DiagnosticoSite(BaseModel):
    url_abre: str
    demora_pra_abrir: str
    tem_formulario_captacao: str
    tem_cta: str

class PresencaDigital(BaseModel):
    tem_site_proprio: bool
    url_site: Optional[str] = None
    status_site: Optional[int] = None
    erros_identificados_site: Optional[ErrosIdentificadosSite] = None
    diagnostico_site: Optional[DiagnosticoSite] = None

class OportunidadesIdentificadas(BaseModel):
    urgencia_de_site: bool
    urgencia_de_avaliacoes: bool
    urgencia_de_gestao_reputacao: bool
    telefone_fixo: bool

class ReputacaoGoogle(BaseModel):
    nota_media: float
    total_avaliacoes: int

class GmapsWebhookPayload(BaseModel):
    lead_id: str
    data_coleta: str
    nicho: str
    origem: str
    empresa: Empresa
    reputacao_google: ReputacaoGoogle
    presenca_digital: PresencaDigital
    oportunidades_identificadas: OportunidadesIdentificadas

class WebhookPayload(BaseModel):
    lead_id: str
    data_coleta: str
    nicho: str
    origem: Optional[str] = None
    status: Optional[str] = None
    plataforma_destino: str
    empresa: Empresa
    analise_anuncio: AnaliseAnuncio
    presenca_digital: PresencaDigital

from typing import Dict, Any
import datetime

def build_webhook_payload(enriched_card: Dict[str, Any], test_results: Optional[Dict[str, Any]] = None) -> dict:
    lead_id = enriched_card.get("ad_library_id") or enriched_card.get("raw_hash", "unknown")


    if test_results:
        demorou = test_results.get("demorou_responder", False)
        tempo_segundos = test_results.get("tempo_segundos_primeira_resposta")
        classificacao = test_results.get("classificacao_atendimento", "sem_resposta_24h")

        foi_auto = test_results.get("foi_resposta_automatica", False)
        conteudo_auto = test_results.get("conteudo_resposta_automatica")
        teve_triagem = test_results.get("teve_qualificacao_ou_triagem", False)
        mandou_link = test_results.get("mandou_link_agendamento", False)

        teste_executado = True
        plataforma_testada = test_results.get("plataforma_testada", enriched_card.get("destination_type"))

        if demorou:
            pontos_criticos.append(f"Atendimento demorou ({classificacao})")

    else:
        demorou = False
        tempo_segundos = None
        classificacao = "sem_resposta_24h"
        foi_auto = False
        conteudo_auto = None
        teve_triagem = False
        mandou_link = False
        teste_executado = False
        plataforma_testada = None

    cta_text = str(enriched_card.get("cta_text", "")).lower()
    dest_type = enriched_card.get("destination_type", "")
    dest_url = str(enriched_card.get("destination_url", "")).lower()

    if "whatsapp" in cta_text or dest_type == "whatsapp" or "wa.me" in dest_url or "api.whatsapp.com" in dest_url:
        plataforma_destino = "whatsapp"
    elif dest_type == "instagram_profile" or "instagram.com" in dest_url:
        plataforma_destino = "instagram"
    elif dest_type == "facebook_page" or "facebook.com" in dest_url:
        plataforma_destino = "facebook"
    elif dest_type == "website" or enriched_card.get("destination_url"):
        plataforma_destino = "site_externo"
    else:
        plataforma_destino = "outro"

    erros = None
    diagnostico_site = None
    if plataforma_destino == "site_externo":
        erros = ErrosIdentificadosSite(
            nao_possui_formulario_captura=not (enriched_card.get("contact_has_form") == "sim"),
            nao_possui_botao_whatsapp=not (enriched_card.get("contact_has_whatsapp") == "sim"),
        )
        status_c = enriched_card.get("status_code", 0)
        load_t = enriched_card.get("load_time", 0.0)
        diagnostico_site = DiagnosticoSite(
            url_abre="sim" if status_c == 200 else "não",
            demora_pra_abrir="sim" if load_t > 3.0 else "não",
            tem_formulario_captacao="sim" if enriched_card.get("contact_has_form") == "sim" else "não",
            tem_cta="sim" if enriched_card.get("contact_has_cta") == "sim" else "não"
        )

    presenca = PresencaDigital(
        tem_site_proprio=(enriched_card.get("destination_type") == "website" and enriched_card.get("status_code", 0) == 200),
        url_site=enriched_card.get("destination_clean_url"),
        status_site=enriched_card.get("status_code"),
        erros_identificados_site=erros,
        diagnostico_site=diagnostico_site
    )

    if "mensagem" in cta_text or "whatsapp" in cta_text or dest_type in ["whatsapp", "instagram_profile", "facebook_page"]:
        tipo_redirecionamento = "chat_direto"
    elif dest_type == "website":
        tipo_redirecionamento = "site_externo"
    else:
        tipo_redirecionamento = dest_type

    payload = WebhookPayload(
        lead_id=f"meta_{lead_id}",
        data_coleta=datetime.datetime.now().isoformat(),
        nicho=enriched_card.get("niche", "geral"),
        origem="meta_ads_library",
        status="Prospectado",
        plataforma_destino=plataforma_destino,
        empresa=Empresa(
            nome=enriched_card.get("page_name") or "Desconhecido",
            telefone_contato=enriched_card.get("contact_phone"),
            email_contato=enriched_card.get("contact_email"),
            facebook_page_url=enriched_card.get("page_url"),
            instagram_url=None,
            localizacao=""
        ),
        analise_anuncio=AnaliseAnuncio(
            id_anuncio_meta=lead_id,
            link_biblioteca_anuncios=enriched_card.get("search_url", ""),
            data_inicio_veiculacao=enriched_card.get("start_date", ""),
            plataformas_veiculadas=[p.strip() for p in str(enriched_card.get("platforms", "")).split(",") if p.strip()],
            link_destino_botao=enriched_card.get("destination_url", "")
        ),
        presenca_digital=presenca,
        funil_whatsapp_direct=funil,
        metricas_atendimento_teste=metricas
    )
    res = payload.model_dump()
    if plataforma_destino != "site_externo":
        if "presenca_digital" in res and "diagnostico_site" in res["presenca_digital"]:
            res["presenca_digital"].pop("diagnostico_site", None)
            
    return res

def build_gmaps_webhook_payload(lead: Dict[str, Any]) -> dict:
    lead_id = lead.get("nome") or lead.get("telefone") or "unknown"
    import re
    safe_id = re.sub(r'[^a-zA-Z0-9]', '_', lead_id).lower()
    
    has_site = (lead.get("site_valido") == "sim" or lead.get("tem_site") == "sim")
    
    # 1. Reputacao Google
    try:
        nota = float(lead.get("nota") or 0)
    except ValueError:
        nota = 0.0
        
    try:
        avaliacoes = int(float(lead.get("avaliacoes") or 0))
    except ValueError:
        avaliacoes = 0
        
    reputacao = ReputacaoGoogle(
        nota_media=nota,
        total_avaliacoes=avaliacoes
    )
    
    # 2. Oportunidades Identificadas
    tipo_telefone = str(lead.get("telefone_tipo") or "").lower()
    telefone_fixo = (tipo_telefone == "fixo")
    
    oportunidades = OportunidadesIdentificadas(
        urgencia_de_site=not has_site,
        urgencia_de_avaliacoes=(avaliacoes < 50),
        urgencia_de_gestao_reputacao=(nota < 4.0 and avaliacoes > 0),
        telefone_fixo=telefone_fixo
    )
    
    # 3. Presenca Digital e Diagnostico
    diagnostico_site_obj = None
    if has_site:
        url_abre = "nao" if lead.get("erro_diagnostico") else "sim"
        load_time_str = str(lead.get("load_time", ""))
        try:
            load_time_val = float(load_time_str)
        except ValueError:
            load_time_val = 0.0
        demora_pra_abrir = "sim" if load_time_val > 3.0 else "nao"
        
        diagnostico_site_obj = DiagnosticoSite(
            url_abre=url_abre,
            demora_pra_abrir=demora_pra_abrir,
            tem_formulario_captacao=lead.get("formulario") or "nao",
            tem_cta=lead.get("has_cta") or "nao"
        )
        
    presenca = PresencaDigital(
        tem_site_proprio=has_site,
        url_site=lead.get("site"),
        status_site=None,
        erros_identificados_site=None,
        diagnostico_site=diagnostico_site_obj
    )
    
    payload = GmapsWebhookPayload(
        lead_id=f"gmaps_{safe_id}",
        data_coleta=datetime.datetime.now().isoformat(),
        nicho=lead.get("categoria") or "geral",
        origem="google_maps",
        empresa=Empresa(
            nome=lead.get("nome") or "Desconhecido",
            telefone_contato=lead.get("telefone"),
            email_contato=None,
            facebook_page_url=None,
            localizacao=lead.get("endereco") or "",
        ),
        reputacao_google=reputacao,
        presenca_digital=presenca,
        oportunidades_identificadas=oportunidades
    )
    
    res = payload.model_dump()
    if not has_site:
        if "presenca_digital" in res and "diagnostico_site" in res["presenca_digital"]:
            res["presenca_digital"].pop("diagnostico_site", None)
            
    return res
