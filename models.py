from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Empresa(BaseModel):
    nome: str
    telefone_contato: Optional[str] = None
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

class PresencaDigital(BaseModel):
    tem_site_proprio: bool
    url_site: Optional[str] = None
    status_site: Optional[int] = None
    erros_identificados_site: ErrosIdentificadosSite

class FunilWhatsappDirect(BaseModel):
    tipo_redirecionamento_anuncio: str
    tem_link_whatsapp: bool
    numero_whatsapp_detectado: Optional[str] = None
    mensagem_pre_preenchida: Optional[str] = None

class TempoResposta(BaseModel):
    demorou_responder: bool = False
    tempo_segundos_primeira_resposta: Optional[int] = None
    classificacao_atendimento: str = "sem_resposta_24h"

class QualidadeAtendimentoInicial(BaseModel):
    foi_resposta_automatica: bool = False
    conteudo_resposta_automatica: Optional[str] = None
    teve_qualificacao_ou_triagem: bool = False
    mandou_link_agendamento: bool = False

class MetricasAtendimentoTeste(BaseModel):
    teste_executado: bool = False
    plataforma_testada: Optional[str] = None
    horario_envio_teste: str
    tempo_resposta: TempoResposta
    qualidade_atendimento_inicial: QualidadeAtendimentoInicial

class DiagnosticoPainDetector(BaseModel):
    pontos_criticos: List[str]
    perda_financeira_estimada: str
    solucao_ideal_recomendada: str

class WebhookPayload(BaseModel):
    lead_id: str
    data_coleta: str
    nicho: str
    empresa: Empresa
    analise_anuncio: AnaliseAnuncio
    presenca_digital: PresencaDigital
    funil_whatsapp_direct: FunilWhatsappDirect
    metricas_atendimento_teste: MetricasAtendimentoTeste
    diagnostico_do_pain_detector: DiagnosticoPainDetector

from typing import Dict, Any
import datetime

def build_webhook_payload(enriched_card: Dict[str, Any], test_results: Optional[Dict[str, Any]] = None) -> dict:
    lead_id = enriched_card.get("ad_library_id") or enriched_card.get("raw_hash", "unknown")

    pontos_criticos = []
    if enriched_card.get("gap"):
        pontos_criticos.append(enriched_card["gap"])

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

    erros = ErrosIdentificadosSite(
        nao_possui_formulario_captura=not (enriched_card.get("contact_has_form") == "sim"),
        nao_possui_botao_whatsapp=not (enriched_card.get("contact_has_whatsapp") == "sim"),
    )

    presenca = PresencaDigital(
        tem_site_proprio=(enriched_card.get("destination_type") == "website"),
        url_site=enriched_card.get("destination_clean_url"),
        status_site=None,
        erros_identificados_site=erros
    )

    funil = FunilWhatsappDirect(
        tipo_redirecionamento_anuncio=enriched_card.get("destination_type", "site_externo"),
        tem_link_whatsapp=(enriched_card.get("contact_has_whatsapp") == "sim"),
        numero_whatsapp_detectado=None,
        mensagem_pre_preenchida=None
    )

    metricas = MetricasAtendimentoTeste(
        teste_executado=teste_executado,
        plataforma_testada=plataforma_testada,
        horario_envio_teste=datetime.datetime.now().isoformat(),
        tempo_resposta=TempoResposta(
            demorou_responder=demorou,
            tempo_segundos_primeira_resposta=tempo_segundos,
            classificacao_atendimento=classificacao
        ),
        qualidade_atendimento_inicial=QualidadeAtendimentoInicial(
            foi_resposta_automatica=foi_auto,
            conteudo_resposta_automatica=conteudo_auto,
            teve_qualificacao_ou_triagem=teve_triagem,
            mandou_link_agendamento=mandou_link
        )
    )

    diagnostico = DiagnosticoPainDetector(
        pontos_criticos=pontos_criticos,
        perda_financeira_estimada="Alta" if enriched_card.get("score", 0) > 100 else "Media",
        solucao_ideal_recomendada=enriched_card.get("offer", "")
    )

    payload = WebhookPayload(
        lead_id=f"meta_{lead_id}",
        data_coleta=datetime.datetime.now().isoformat(),
        nicho=enriched_card.get("niche", "geral"),
        empresa=Empresa(
            nome=enriched_card.get("page_name") or "Desconhecido",
            facebook_page_url=enriched_card.get("page_url"),
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
        metricas_atendimento_teste=metricas,
        diagnostico_do_pain_detector=diagnostico
    )
    return payload.model_dump()
