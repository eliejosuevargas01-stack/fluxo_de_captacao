from pydantic import BaseModel, Field, ConfigDict
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
    status: str = "Prospectado"
    empresa: Empresa
    reputacao_google: ReputacaoGoogle
    presenca_digital: PresencaDigital
    oportunidades_identificadas: OportunidadesIdentificadas

class WebhookPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    lead_id: str
    nome_empresa: str
    instagram: Optional[str] = None
    telefone: Optional[str] = None
    segmento: str = "geral"
    origem: str = "meta_ads_library"
    status: str = "Prospectado"
    falha_identificada: Optional[str] = None
    solucao_recomendada: Optional[str] = None
    link_whatsapp: Optional[str] = None
    facebook_page_url: Optional[str] = None
    link_destibo_botao: Optional[str] = None
    url_site: Optional[str] = None
    tem_site_proprio: bool = False
    erros_identificados_site: Optional[str] = None
    dor_identificada: Optional[str] = None
    credibilidade_da_dor_identificada: Optional[str] = None
    servico_ofertado: Optional[str] = None
    id_anuncio_meta: str
    email: Optional[str] = None
    tem_formulario: Optional[str] = Field(None, alias="tem formulario?")
    tem_cta: Optional[str] = Field(None, alias="tem cta?")
    url_abre: Optional[str] = Field(None, alias="url abre?")
    demora_pra_abrir: Optional[str] = Field(None, alias="demora pra abrir?")
    tem_formulario_de_captacao: Optional[str] = Field(None, alias="tem formulario de captação?")

from typing import Dict, Any
import datetime

def build_webhook_payload(enriched_card: Dict[str, Any], test_results: Optional[Dict[str, Any]] = None, target_platform: Optional[str] = None) -> dict:
    from collectors.analyzers.pain_detector import SiteDiagnosis, infer_pain_and_offer
    import json

    lead_id = enriched_card.get("ad_library_id") or enriched_card.get("raw_hash", "unknown")
    nome_empresa = enriched_card.get("page_name") or "Desconhecido"
    
    # Try to extract Instagram URL
    instagram = None
    dest_url = enriched_card.get("destination_url") or ""
    dest_url_lower = dest_url.lower()
    if "instagram.com" in dest_url_lower:
        instagram = dest_url
    
    telefone = enriched_card.get("contact_phone")
    segmento = enriched_card.get("niche", "geral")
    origem = "meta_ads_library"
    status = "Prospectado"

    # Analyze pain if it's website
    tem_site_proprio = (enriched_card.get("destination_type") == "website")
    
    falha_identificada = None
    dor_identificada = None
    solucao_recomendada = None
    servico_ofertado = None
    credibilidade_da_dor_identificada = None
    erros_identificados_site = None

    status_c = enriched_card.get("status_code", 0)
    load_t = enriched_card.get("load_time", 0.0)

    # Diagnostico keys
    url_abre = "não"
    demora_pra_abrir = "não"
    tem_formulario_captacao = "não"
    tem_formulario = "não"
    tem_cta = "não"

    if tem_site_proprio:
        url_abre = "sim" if status_c == 200 else "não"
        demora_pra_abrir = "sim" if load_t > 3.0 else "não"
        tem_formulario_captacao = "sim" if enriched_card.get("contact_has_form") == "sim" else "não"
        tem_formulario = "sim" if enriched_card.get("contact_has_form") == "sim" else "não"
        tem_cta = "sim" if enriched_card.get("contact_has_cta") == "sim" else "não"

        # Diagnose site using the SiteDiagnosis structure
        diag = SiteDiagnosis(
            site=True,
            whatsapp=(enriched_card.get("contact_has_whatsapp") == "sim"),
            whatsapp_hints=(),
            agendamento=(enriched_card.get("contact_has_booking") == "sim"),
            instagram=(enriched_card.get("contact_has_instagram") == "sim"),
            formulario=(enriched_card.get("contact_has_form") == "sim"),
            url_final=enriched_card.get("destination_clean_url") or "",
            erro=enriched_card.get("contact_error") or "",
            has_cta=(enriched_card.get("contact_has_cta") == "sim"),
            load_time=load_t
        )
        
        pain, solution, service = infer_pain_and_offer(segmento, diag)
        falha_identificada = json.dumps([pain])
        dor_identificada = json.dumps([pain])
        solucao_recomendada = solution
        servico_ofertado = service
        
        # Credibility score calculation
        if status_c == 200:
            credibilidade_da_dor_identificada = "100%"
        elif enriched_card.get("contact_error"):
            credibilidade_da_dor_identificada = "0%"
        else:
            credibilidade_da_dor_identificada = "50%"

        # Erros identificados list
        errors = []
        if status_c != 200:
            errors.append("fora_do_ar")
        if enriched_card.get("contact_has_form") != "sim":
            errors.append("nao_possui_formulario_captura")
        if enriched_card.get("contact_has_whatsapp") != "sim":
            errors.append("nao_possui_botao_whatsapp")
        
        erros_identificados_site = json.dumps(errors) if errors else None
    else:
        # If it's a direct WhatsApp ad
        if "whatsapp" in dest_url_lower or "wa.me" in dest_url_lower or "api.whatsapp.com" in dest_url_lower:
            tem_cta = "sim"
            tem_formulario = "não"

    # link_whatsapp: if the button link is a whatsapp link, use that. Otherwise if we found a phone, use wa.me/phone
    link_whatsapp = None
    if "wa.me" in dest_url_lower or "api.whatsapp.com" in dest_url_lower or "whatsapp.com" in dest_url_lower or "whatsapp://" in dest_url_lower:
        link_whatsapp = dest_url
    elif telefone:
        link_whatsapp = f"https://wa.me/{telefone}"

    facebook_page_url = enriched_card.get("page_url")
    link_destibo_botao = dest_url
    url_site = enriched_card.get("destination_clean_url") or dest_url if tem_site_proprio else None
    id_anuncio_meta = lead_id
    email = enriched_card.get("contact_email")

    payload = WebhookPayload(
        lead_id=f"meta_{lead_id}",
        nome_empresa=nome_empresa,
        instagram=instagram,
        telefone=telefone,
        segmento=segmento,
        origem=origem,
        status=status,
        falha_identificada=falha_identificada,
        solucao_recomendada=solucao_recomendada,
        link_whatsapp=link_whatsapp,
        facebook_page_url=facebook_page_url,
        link_destibo_botao=link_destibo_botao,
        url_site=url_site,
        tem_site_proprio=tem_site_proprio,
        erros_identificados_site=erros_identificados_site,
        dor_identificada=dor_identificada,
        credibilidade_da_dor_identificada=credibilidade_da_dor_identificada,
        servico_ofertado=servico_ofertado,
        id_anuncio_meta=id_anuncio_meta,
        email=email,
        tem_formulario=tem_formulario,
        tem_cta=tem_cta,
        url_abre=url_abre,
        demora_pra_abrir=demora_pra_abrir,
        tem_formulario_de_captacao=tem_formulario_captacao
    )

    res = payload.model_dump(by_alias=True)
    if target_platform != "site_externo":
        res.pop("url abre?", None)
        res.pop("demora pra abrir?", None)
        res.pop("tem formulario de captação?", None)

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
        status="Prospectado",
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
