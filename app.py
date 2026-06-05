from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
DEFAULT_FILES = {
    "Leads base": ROOT / "outputs" / "leads.csv",
    "Leads qualificados": ROOT / "outputs" / "leads_qualificados.csv",
    "Top 50": ROOT / "outputs" / "leads_top50.csv",
    "Propostas": ROOT / "outputs" / "propostas.csv",
}


st.set_page_config(
    page_title="Painel de Leads",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #0c111b;
            --panel: rgba(16, 23, 38, 0.86);
            --panel-border: rgba(255, 255, 255, 0.08);
            --text: #e8edf7;
            --muted: #9aa7bd;
            --accent: #78dcca;
            --accent-2: #f5b942;
            --danger: #ff6f61;
        }

        html, body, [class*="css"]  {
            font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(120, 220, 202, 0.15), transparent 35%),
                radial-gradient(circle at top right, rgba(245, 185, 66, 0.12), transparent 30%),
                linear-gradient(180deg, #09111e 0%, #0c111b 38%, #0b1320 100%);
            color: var(--text);
        }

        .hero {
            padding: 1.25rem 1.4rem;
            border: 1px solid var(--panel-border);
            border-radius: 22px;
            background: linear-gradient(135deg, rgba(18, 28, 48, 0.94), rgba(9, 17, 28, 0.88));
            box-shadow: 0 24px 60px rgba(0, 0, 0, 0.25);
            margin-bottom: 1rem;
        }

        .hero h1 {
            margin: 0;
            font-size: 2.15rem;
            letter-spacing: -0.03em;
            color: white;
        }

        .hero p {
            margin: 0.35rem 0 0 0;
            color: var(--muted);
            max-width: 70ch;
            line-height: 1.5;
        }

        .metric-card {
            border: 1px solid var(--panel-border);
            border-radius: 18px;
            background: var(--panel);
            padding: 1rem 1rem 0.85rem 1rem;
            min-height: 110px;
            box-shadow: 0 14px 35px rgba(0,0,0,0.18);
        }

        .metric-label {
            color: var(--muted);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            margin-bottom: 0.35rem;
        }

        .metric-value {
            font-size: 1.9rem;
            line-height: 1;
            font-weight: 700;
            color: white;
        }

        .metric-sub {
            color: var(--muted);
            font-size: 0.88rem;
            margin-top: 0.4rem;
        }

        .section-title {
            margin: 1rem 0 0.5rem 0;
            font-size: 1.05rem;
            color: white;
        }

        .small-pill {
            display: inline-block;
            padding: 0.35rem 0.6rem;
            border-radius: 999px;
            background: rgba(120, 220, 202, 0.12);
            border: 1px solid rgba(120, 220, 202, 0.25);
            color: var(--accent);
            font-size: 0.78rem;
            margin-right: 0.35rem;
            margin-bottom: 0.35rem;
        }

        .lead-panel {
            border: 1px solid var(--panel-border);
            border-radius: 20px;
            background: var(--panel);
            padding: 1rem 1rem 0.9rem 1rem;
            box-shadow: 0 18px 40px rgba(0,0,0,0.18);
        }

        .lead-name {
            font-size: 1.5rem;
            font-weight: 700;
            color: white;
            margin-bottom: 0.3rem;
        }

        .lead-meta {
            color: var(--muted);
            font-size: 0.92rem;
            margin-bottom: 0.8rem;
        }

        .insight {
            border-left: 3px solid var(--accent);
            padding: 0.6rem 0.8rem;
            background: rgba(120, 220, 202, 0.07);
            border-radius: 10px;
            margin-bottom: 0.65rem;
        }

        .insight strong {
            color: white;
        }

        .stDataFrame, .stTable {
            border-radius: 16px;
            overflow: hidden;
        }

        .stSidebar {
            background: rgba(8, 13, 22, 0.95);
            border-right: 1px solid rgba(255,255,255,0.06);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def read_csvs() -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for label, path in DEFAULT_FILES.items():
        if path.exists() and path.stat().st_size > 0:
            df = pd.read_csv(path)
        else:
            df = pd.DataFrame()
        frames[label] = df
    return frames


def first_existing(df: pd.DataFrame, columns: list[str], default: Any = "") -> Any:
    for col in columns:
        if col in df.columns:
            return df.iloc[0][col]
    return default


def to_bool_text(value: Any) -> str:
    if pd.isna(value):
        return "Nao"
    text = str(value).strip().lower()
    if text in {"sim", "yes", "true", "1"}:
        return "Sim"
    if text in {"nao", "não", "no", "false", "0"}:
        return "Nao"
    return str(value)


def fmt_currency(value: Any) -> str:
    try:
        num = float(value)
    except Exception:
        return str(value)
    return f"R$ {num:,.0f}".replace(",", ".")


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except Exception:
        return default


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()
    rename_map = {
        "avaliacoes": "reviews",
        "nota": "rating",
    }
    for old, new in rename_map.items():
        if old in out.columns and new not in out.columns:
            out = out.rename(columns={old: new})

    numeric_columns = ["score", "reviews", "rating", "segmento_peso"]
    for col in numeric_columns:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    return out


def apply_sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    st.sidebar.header("Filtros")
    query = st.sidebar.text_input("Buscar por nome ou categoria", value="")

    categories = sorted([str(x) for x in df.get("categoria", pd.Series(dtype=str)).dropna().unique().tolist()])
    selected_categories = st.sidebar.multiselect(
        "Categorias",
        options=categories,
        default=categories[:],
    )

    min_score = safe_int(df["score"].min()) if "score" in df.columns and not df["score"].dropna().empty else 0
    max_score = safe_int(df["score"].max()) if "score" in df.columns and not df["score"].dropna().empty else 0
    score_range = st.sidebar.slider("Score", min_value=min_score, max_value=max_score, value=(min_score, max_score))

    site_filter = st.sidebar.selectbox("Site", options=["Todos", "Com site", "Sem site"])
    whatsapp_filter = st.sidebar.selectbox("WhatsApp", options=["Todos", "Sim", "Nao"])
    agendamento_filter = st.sidebar.selectbox("Agendamento", options=["Todos", "Sim", "Nao"])

    filtered = df.copy()

    if query.strip():
        q = query.strip().lower()
        mask = (
            filtered.get("nome", pd.Series(index=filtered.index, dtype=str)).astype(str).str.lower().str.contains(q, na=False)
            | filtered.get("categoria", pd.Series(index=filtered.index, dtype=str)).astype(str).str.lower().str.contains(q, na=False)
        )
        filtered = filtered.loc[mask]

    if selected_categories:
        filtered = filtered[filtered.get("categoria", pd.Series(index=filtered.index, dtype=str)).isin(selected_categories)]

    if "score" in filtered.columns:
        filtered = filtered[filtered["score"].fillna(0).between(score_range[0], score_range[1])]

    if site_filter != "Todos" and "tem_site" in filtered.columns:
        want = "sim" if site_filter == "Com site" else "nao"
        filtered = filtered[filtered["tem_site"].astype(str).str.lower() == want]

    if whatsapp_filter != "Todos" and "whatsapp" in filtered.columns:
        filtered = filtered[filtered["whatsapp"].astype(str).str.lower() == whatsapp_filter.lower()]

    if agendamento_filter != "Todos" and "agendamento" in filtered.columns:
        filtered = filtered[filtered["agendamento"].astype(str).str.lower() == agendamento_filter.lower()]

    return filtered


def metric_card(label: str, value: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero">
            <h1>Painel de Leads</h1>
            <p>Veja o pipeline completo: qualificação, ranking, diagnóstico, dor, proposta e mensagem pronta para envio. A tela foi pensada para decidir rápido quais leads valem contato e o que oferecer para cada um.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metrics(df: pd.DataFrame, top_df: pd.DataFrame) -> None:
    total = len(df)
    top = len(top_df)
    avg_score = f"{df['score'].mean():.0f}" if "score" in df.columns and total else "0"
    avg_rating = f"{df['rating'].mean():.1f}" if "rating" in df.columns and total else "0.0"
    sem_site = int((df["tem_site"].astype(str).str.lower() == "nao").sum()) if "tem_site" in df.columns and total else 0
    com_whatsapp = int((top_df.get("whatsapp", pd.Series(dtype=str)).astype(str).str.lower() == "sim").sum()) if top else 0

    cols = st.columns(5)
    with cols[0]:
        metric_card("Leads totais", str(total), "Base carregada de leads.csv")
    with cols[1]:
        metric_card("Top 50", str(top), "Leads priorizados para contato")
    with cols[2]:
        metric_card("Media score", avg_score, "Pontuacao media da base")
    with cols[3]:
        metric_card("Media nota", avg_rating, "Classificacao media do Google Maps")
    with cols[4]:
        metric_card("Sem site", str(sem_site), f"{com_whatsapp} com WhatsApp detectado no Top 50")


def render_segment_summary(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Distribuicao por segmento</div>', unsafe_allow_html=True)
    if df.empty or "categoria" not in df.columns:
        st.info("Nao ha dados para mostrar a distribuicao.")
        return
    dist = (
        df["categoria"]
        .fillna("Sem categoria")
        .astype(str)
        .value_counts()
        .reset_index()
        .rename(columns={"index": "categoria", "categoria": "quantidade"})
    )
    st.dataframe(dist, use_container_width=True, hide_index=True)


def render_score_chart(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Score por lead</div>', unsafe_allow_html=True)
    if df.empty or "score" not in df.columns:
        st.info("Sem score para plotar.")
        return
    chart_df = df[["nome", "score"]].dropna().head(20).set_index("nome")
    st.bar_chart(chart_df)


def lead_detail_panel(row: pd.Series) -> None:
    name = str(row.get("nome", "Lead"))
    category = str(row.get("categoria", ""))
    score = row.get("score", "")
    rating = row.get("rating", row.get("nota", ""))
    reviews = row.get("reviews", row.get("avaliacoes", ""))

    st.markdown(
        f"""
        <div class="lead-panel">
            <div class="lead-name">{name}</div>
            <div class="lead-meta">{category} | Score {score} | Nota {rating} | {reviews} avaliacoes</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f"""
            <div class="lead-panel">
                <div class="section-title" style="margin-top:0">Situação digital</div>
                <div class="small-pill">Site: {to_bool_text(row.get("site_valido", row.get("tem_site", "")))}</div>
                <div class="small-pill">WhatsApp: {to_bool_text(row.get("whatsapp", ""))}</div>
                <div class="small-pill">Agendamento: {to_bool_text(row.get("agendamento", ""))}</div>
                <div class="small-pill">Instagram: {to_bool_text(row.get("instagram", ""))}</div>
                <div class="small-pill">Formulario: {to_bool_text(row.get("formulario", ""))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="lead-panel">
                <div class="section-title" style="margin-top:0">Dor detectada</div>
                <div class="insight">{row.get("dor", "Sem dor detectada.")}</div>
                <div class="section-title">Oferta sugerida</div>
                <div class="insight">{row.get("oferta", "Sem oferta.")}</div>
                <div class="section-title">Tipo</div>
                <div class="small-pill">{row.get("tipo_oferta", "N/A")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="lead-panel">
                <div class="section-title" style="margin-top:0">Mensagem pronta</div>
                <div class="insight">{row.get("mensagem", "Sem mensagem gerada.")}</div>
                <div class="section-title">Contato</div>
                <div class="small-pill">{row.get("telefone", "Sem telefone")}</div>
                <div class="small-pill">{row.get("site", "Sem site") or "Sem site"}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("Ver todos os campos do lead"):
        st.json(row.to_dict())


def proposal_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("Sem propostas para mostrar.")
        return
    cols = [
        col
        for col in [
            "nome",
            "telefone",
            "score",
            "dor",
            "oferta",
            "mensagem",
        ]
        if col in df.columns
    ]
    st.dataframe(df[cols], use_container_width=True, hide_index=True)


def main() -> None:
    inject_css()
    frames = {name: normalize_df(df) for name, df in read_csvs().items()}
    base_df = frames["Leads qualificados"] if not frames["Leads qualificados"].empty else frames["Leads base"]
    top_df = frames["Top 50"]
    proposals_df = frames["Propostas"]

    if base_df.empty:
        st.error("Nao encontrei leads para exibir. Gere os CSVs antes de abrir este dashboard.")
        st.stop()

    render_hero()
    render_metrics(base_df, top_df if not top_df.empty else base_df.head(0))

    st.sidebar.markdown("## Navegacao")
    mode = st.sidebar.radio("Modo", ["Visao geral", "Lead detalhado", "Propostas"], index=0)

    filtered = apply_sidebar_filters(base_df)

    tabs = st.tabs(["Ranking", "Insights", "Dados brutos"])

    with tabs[0]:
        left, right = st.columns([1.25, 0.75], gap="large")
        with left:
            st.markdown('<div class="section-title">Ranking filtrado</div>', unsafe_allow_html=True)
            ranking_cols = [col for col in ["nome", "categoria", "score", "reviews", "rating", "tem_site", "site", "telefone"] if col in filtered.columns]
            display_df = filtered.sort_values(by=[c for c in ["score", "reviews", "rating"] if c in filtered.columns], ascending=False)
            st.dataframe(display_df[ranking_cols].head(50), use_container_width=True, hide_index=True)
        with right:
            st.markdown('<div class="section-title">Resumo rapido</div>', unsafe_allow_html=True)
            render_segment_summary(filtered)
            render_score_chart(filtered)

    with tabs[1]:
        if mode == "Visao geral":
            if top_df.empty:
                st.warning("O arquivo de Top 50 nao foi encontrado. Rode o pipeline antes.")
            else:
                st.markdown('<div class="section-title">Top 50 priorizados</div>', unsafe_allow_html=True)
                proposal_view = top_df.sort_values(by=[c for c in ["score", "reviews", "rating"] if c in top_df.columns], ascending=False)
                cols = [col for col in ["nome", "categoria", "score", "reviews", "rating", "dor", "oferta"] if col in proposal_view.columns]
                st.dataframe(proposal_view[cols], use_container_width=True, hide_index=True)
        elif mode == "Lead detalhado":
            source_df = top_df if not top_df.empty else filtered
            if source_df.empty:
                st.warning("Nenhum lead disponivel para detalhamento.")
            else:
                options = source_df["nome"].fillna("Lead").astype(str).tolist()
                selected_name = st.selectbox("Escolha o lead", options=options)
                row = source_df[source_df["nome"].astype(str) == selected_name].iloc[0]
                lead_detail_panel(row)
        else:
            proposal_table(proposals_df if not proposals_df.empty else top_df)

    with tabs[2]:
        st.markdown('<div class="section-title">Dados completos filtrados</div>', unsafe_allow_html=True)
        st.dataframe(filtered, use_container_width=True, hide_index=True)

        csv = filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Baixar leads filtrados",
            data=csv,
            file_name="leads_filtrados.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
