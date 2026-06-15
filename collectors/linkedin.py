from __future__ import annotations

import re
import time
from typing import Any, Dict, List
import urllib3
import requests
from html import unescape

def clean_html(raw_html: str) -> str:
    """Removes HTML tags and normalizes whitespace."""
    if not raw_html:
        return ""
    # Remove script and style elements
    clean = re.sub(r'<(script|style)[^>]*>([\s\S]*?)</\1>', ' ', raw_html)
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', ' ', clean)
    # Decode HTML entities
    clean = unescape(clean)
    # Normalize spaces
    clean = " ".join(clean.split())
    return clean.strip()

def extract_between(text: str, start_delim: str, end_delim: str) -> str:
    """Helper to extract substring between two delimiters."""
    try:
        start_idx = text.find(start_delim)
        if start_idx == -1:
            return ""
        start_idx += len(start_delim)
        end_idx = text.find(end_delim, start_idx)
        if end_idx == -1:
            return ""
        return text[start_idx:end_idx].strip()
    except Exception:
        return ""

def score_job(title: str, description_text: str) -> tuple[int, list[str], bool]:
    """
    Evaluates job title and description for junior compatibility and user's highlighted technologies.
    Returns: (match_score, matching_keywords, junior_friendly)
    """
    desc_lower = (title + " \n " + description_text).lower()
    
    # Junior-friendly indicators
    junior_terms = [
        "junior", "jr", "estágio", "estagio", "internship", "intern", 
        "entry level", "sem experiência", "sem experiencia", "no experience", 
        "less than a year", "sem exigir experiencia", "assistente"
    ]
    junior_friendly = any(term in desc_lower for term in junior_terms)
    
    # Technologies and terms matching
    tech_keywords = {
        "python": ["python"],
        "n8n": ["n8n"],
        "netlify": ["netlify"],
        "coolify": ["coolify"],
        "github": ["github", "git "],
        "fastapi": ["fastapi"],
        "pydantic": ["pydantic"],
        "backend": ["backend", "back-end"],
        "landing page": ["landing page", "landingpages", "landing-page"],
        "agente de atendimento": ["agente de atendimento", "agente virtual", "chatbot", "chatbots", "atendimento automatizado", "ia de atendimento", "ai agent", "ai agents"]
    }
    
    matching_keywords = []
    for display_name, patterns in tech_keywords.items():
        if any(pat in desc_lower for pat in patterns):
            matching_keywords.append(display_name)
            
    # Score calculation
    score = 40  # Base score
    
    # Add points for matching technologies
    score += len(matching_keywords) * 10
    
    if junior_friendly:
        score += 15
        
    # Cap score between 0 and 100
    score = max(0, min(100, score))
    
    return score, matching_keywords, junior_friendly

def scrape_linkedin_jobs(keywords: str, location: str = "Brasil", max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Scrapes public LinkedIn job listings (Remote only, f_WT=2) and returns details.
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    }
    
    jobs: List[Dict[str, Any]] = []
    start = 0
    
    while len(jobs) < max_results:
        # f_WT=2 forces Remote jobs
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        params = {
            "keywords": keywords,
            "location": location,
            "f_WT": "2",
            "start": start
        }
        
        try:
            res = requests.get(url, params=params, headers=headers, verify=False, timeout=15)
            if res.status_code != 200:
                print(f"Failed to fetch seeMoreJobPostings: status code {res.status_code}")
                break
                
            html = res.text
            # Find all job card links
            li_blocks = html.split("<li>")
            # If no items returned, we reached the end
            if len(li_blocks) <= 1:
                break
                
            for block in li_blocks[1:]:
                if len(jobs) >= max_results:
                    break
                    
                # Extract Job ID
                job_id_match = re.search(r'data-entity-urn="urn:li:jobPosting:(\d+)"', block)
                if not job_id_match:
                    continue
                job_id = job_id_match.group(1)
                
                # Extract Job Title
                title_match = re.search(r'<h3 class="base-search-card__title">([\s\S]*?)</h3>', block)
                job_title = title_match.group(1).strip() if title_match else "Desconhecido"
                job_title = clean_html(job_title)
                
                # Extract Job URL
                url_match = re.search(r'<a class="base-card__full-link[^"]*" href="([^"]+)"', block)
                job_url = url_match.group(1).strip() if url_match else f"https://www.linkedin.com/jobs/view/{job_id}"
                # Decode href entities
                job_url = unescape(job_url)
                
                # Extract Company Name & Company LinkedIn URL
                company_name = "Desconhecido"
                company_url = None
                
                # Try hidden link first
                company_link_match = re.search(r'<a class="hidden-nested-link"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)</a>', block)
                if company_link_match:
                    company_url = unescape(company_link_match.group(1).strip())
                    company_name = clean_html(company_link_match.group(2).strip())
                else:
                    # Try plain text subtitle
                    subtitle_match = re.search(r'<h4 class="base-search-card__subtitle">([\s\S]*?)</h4>', block)
                    if subtitle_match:
                        company_name = clean_html(subtitle_match.group(1).strip())
                        
                # Extract Location
                location_match = re.search(r'<span class="job-search-card__location">([\s\S]*?)</span>', block)
                job_location = clean_html(location_match.group(1).strip()) if location_match else ""
                
                # Extract Relative Post Date
                date_match = re.search(r'<time[^>]*datetime="([^"]+)"[^>]*>([\s\S]*?)</time>', block)
                posting_date = clean_html(date_match.group(2).strip()) if date_match else "Recente"
                
                # Fetch details for the job
                detail_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
                time.sleep(0.5)  # Throttle request to avoid blocks
                
                detail_res = requests.get(detail_url, headers=headers, verify=False, timeout=15)
                desc_html = ""
                seniority = "Não informado"
                employment_type = "Não informado"
                
                if detail_res.status_code == 200:
                    detail_html = detail_res.text
                    
                    # Extract Job Description Markup
                    desc_match = re.search(r'<div class="show-more-less-html__markup[^"]*">([\s\S]*?)</div>', detail_html)
                    if desc_match:
                        desc_html = desc_match.group(1).strip()
                    else:
                        # Fallback description search
                        desc_match_fallback = re.search(r'<section class="[^"]*description">([\s\S]*?)</section>', detail_html)
                        if desc_match_fallback:
                            desc_html = desc_match_fallback.group(1).strip()
                            
                    # Extract Seniority Level
                    # Match subheader "Seniority level" and then get the criteria text
                    seniority_block = extract_between(detail_html, "Seniority level", "</li>")
                    if seniority_block:
                        seniority = clean_html(extract_between(seniority_block, "text--criteria\">", "</span>")) or "Não informado"
                        
                    # Extract Employment Type
                    employment_block = extract_between(detail_html, "Employment type", "</li>")
                    if employment_block:
                        employment_type = clean_html(extract_between(employment_block, "text--criteria\">", "</span>")) or "Não informado"
                        
                desc_text = clean_html(desc_html)
                score, matched_requirements, jr_friendly = score_job(job_title, desc_text)
                
                jobs.append({
                    "lead_id": f"linkedin_job_{job_id}",
                    "titulo_vaga": job_title,
                    "nome_empresa": company_name,
                    "link_empresa_linkedin": company_url,
                    "link_vaga": job_url,
                    "localizacao": job_location,
                    "data_publicacao": posting_date,
                    "senioridade": seniority,
                    "tipo_contrato": employment_type,
                    "junior_friendly": jr_friendly,
                    "match_score": score,
                    "requisitos_destacados": matched_requirements,
                    "descricao_vaga": desc_text
                })
                
            start += 25  # Next page index
            
        except Exception as e:
            print(f"Error scraping LinkedIn postings: {e}")
            break
            
    return jobs
