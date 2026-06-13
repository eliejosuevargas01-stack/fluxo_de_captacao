from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime

class Empresa(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    nome: str = Field(..., alias="nome_empresa")
    telefone_contato: Optional[str] = Field(None, alias="telefone")
    email_contato: Optional[str] = Field(None, alias="email")
    instagram_url: Optional[str] = Field(None, alias="instagram")
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
    model_config = ConfigDict(populate_by_name=True)

    url_abre: str = Field(..., alias="url abre?")
    demora_pra_abrir: str = Field(..., alias="demora pra abrir?")
    tem_formulario_captacao: str = Field(..., alias="tem formulario de captação?")
    tem_cta: str = Field(..., alias="tem cta?")

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
    model_config = ConfigDict(populate_by_name=True)

    lead_id: str
    data_coleta: str
    nicho: str
    segmento: str = "geral"
    origem: str
    status: str = "Prospectado"
    nome_empresa: str
    telefone: Optional[str] = None
    email: Optional[str] = None
    instagram: Optional[str] = None
    facebook_page_url: Optional[str] = None
    link_whatsapp: Optional[str] = None
    link_destibo_botao: Optional[str] = None
    url_site: Optional[str] = None
    tem_site_proprio: bool = False
    erros_identificados_site: Optional[str] = None
    falha_identificada: Optional[str] = None
    dor_identificada: Optional[str] = None
    solucao_recomendada: Optional[str] = None
    servico_ofertado: Optional[str] = None
    credibilidade_da_dor_identificada: Optional[str] = None
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
    nicho: str = "geral"
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
    dest_url = enriched_card.get("destination_url") or ""
    dest_url_lower = dest_url.lower()
    is_wa_dest = "wa.me" in dest_url_lower or "api.whatsapp.com" in dest_url_lower or "whatsapp.com" in dest_url_lower or "whatsapp://" in dest_url_lower

    tem_site_proprio = (enriched_card.get("destination_type") == "website" and not is_wa_dest)
    
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
    from collectors.analyzers.pain_detector import SiteDiagnosis, infer_pain_and_offer
    import json
    import re

    lead_id = lead.get("nome") or lead.get("telefone") or "unknown"
    safe_id = re.sub(r'[^a-zA-Z0-9]', '_', lead_id).lower()
    
    url_site = lead.get("site")
    is_wa_site = False
    if url_site:
        u_lower = url_site.lower()
        if "wa.me" in u_lower or "api.whatsapp.com" in u_lower or "whatsapp.com" in u_lower or "whatsapp://" in u_lower:
            is_wa_site = True

    has_site = (lead.get("site_valido") == "sim" or lead.get("tem_site") == "sim") and not is_wa_site
    
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
    
    # Flat field initialization
    url_abre = "não"
    demora_pra_abrir = "não"
    tem_formulario_captacao = "não"
    tem_formulario = "não"
    tem_cta = "não"
    
    falha_identificada = None
    dor_identificada = None
    solucao_recomendada = None
    servico_ofertado = None
    credibilidade_da_dor_identificada = None
    erros_identificados_site = None
    
    nicho = lead.get("categoria") or "geral"
    segmento = nicho
    nome_empresa = lead.get("nome") or "Desconhecido"
    telefone = lead.get("telefone")
    email = None
    instagram = None
    facebook_page_url = None
    
    url_site = None if is_wa_site else lead.get("site")
    link_destibo_botao = lead.get("site")
    
    if has_site:
        url_abre = "não" if lead.get("erro_diagnostico") else "sim"
        load_time_str = str(lead.get("load_time", ""))
        try:
            load_time_val = float(load_time_str)
        except ValueError:
            load_time_val = 0.0
        demora_pra_abrir = "sim" if load_time_val > 3.0 else "não"
        tem_formulario_captacao = "sim" if lead.get("formulario") == "sim" else "não"
        tem_formulario = "sim" if lead.get("formulario") == "sim" else "não"
        tem_cta = "sim" if lead.get("has_cta") == "sim" else "não"
        
        diagnostico_site_obj = DiagnosticoSite(
            url_abre=url_abre,
            demora_pra_abrir=demora_pra_abrir,
            tem_formulario_captacao=tem_formulario_captacao,
            tem_cta=tem_cta
        )
        

        
    presenca = PresencaDigital(
        tem_site_proprio=has_site,
        url_site=url_site,
        status_site=None,
        erros_identificados_site=None,
        diagnostico_site=diagnostico_site_obj
    )
    
    link_whatsapp = None
    if telefone:
        link_whatsapp = f"https://wa.me/{telefone}"
        
    payload = GmapsWebhookPayload(
        lead_id=f"gmaps_{safe_id}",
        data_coleta=datetime.datetime.now().isoformat(),
        nicho=nicho,
        segmento=segmento,
        origem="google_maps",
        status="Prospectado",
        nome_empresa=nome_empresa,
        telefone=telefone,
        email=email,
        instagram=instagram,
        facebook_page_url=facebook_page_url,
        link_whatsapp=link_whatsapp,
        link_destibo_botao=link_destibo_botao,
        url_site=url_site,
        tem_site_proprio=has_site,
        erros_identificados_site=erros_identificados_site,
        falha_identificada=falha_identificada,
        dor_identificada=dor_identificada,
        solucao_recomendada=solucao_recomendada,
        servico_ofertado=servico_ofertado,
        credibilidade_da_dor_identificada=credibilidade_da_dor_identificada,
        empresa=Empresa(
            nome=nome_empresa,
            telefone_contato=telefone,
            email_contato=email,
            instagram_url=instagram,
            facebook_page_url=facebook_page_url,
            localizacao=lead.get("endereco") or "",
        ),
        reputacao_google=reputacao,
        presenca_digital=presenca,
        oportunidades_identificadas=oportunidades
    )
    
    res = payload.model_dump(by_alias=True)
    if not has_site:
        if "presenca_digital" in res and "diagnostico_site" in res["presenca_digital"]:
            res["presenca_digital"].pop("diagnostico_site", None)
            
    return res
