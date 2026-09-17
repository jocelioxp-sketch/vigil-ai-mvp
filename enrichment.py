"""Enriquecimento público restrito à organização, sem inferir vínculo/cargo pessoal."""
import json
import re
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from db import get_lead, save_enrichment


def fetch_company(qid):
    qid=qid.strip().upper()
    if not re.fullmatch(r'Q[1-9][0-9]{0,11}',qid):
        raise ValueError('Informe um identificador Wikidata válido, ex.: Q2283.')
    url=f'https://www.wikidata.org/wiki/Special:EntityData/{qid}.json'
    request=Request(url,headers={'User-Agent':'VigilAI-MBA/2.0 (educational company enrichment)', 'Accept':'application/json'})
    with urlopen(request,timeout=12) as response:
        # Only this public host is requested; no arbitrary URLs, credentials or private-network fetches.
        if not response.url.startswith('https://www.wikidata.org/'):
            raise ValueError('Redirecionamento de fonte não permitido.')
        raw=response.read(2_000_001)
    if len(raw)>2_000_000:
        raise ValueError('Fonte excede o limite de leitura.')
    entity=json.loads(raw)['entities'][qid]
    label=(entity.get('labels',{}).get('pt') or entity.get('labels',{}).get('en') or {}).get('value')
    if not label:
        raise ValueError('Entidade não encontrada.')
    description=(entity.get('descriptions',{}).get('pt') or entity.get('descriptions',{}).get('en') or {}).get('value','')
    websites=[]
    for claim in entity.get('claims',{}).get('P856',[]):
        if claim.get('rank')!='deprecated':
            value=claim.get('mainsnak',{}).get('datavalue',{}).get('value')
            if isinstance(value,str) and value.startswith('https://'):
                websites.append(value)
    return {'qid':qid,'company_label':label,'description':description[:600], 'official_websites':websites[:3],
            'source_url':url,'retrieved_at':datetime.now(timezone.utc).isoformat(),
            'scope':'Descrição e website da organização; não verifica emprego, cargo, porte ou interesse do lead.'}


def score_profile(lead):
    score=20
    reasons=[]
    if any(x in (lead.get('role') or '').lower() for x in ('ciso','cto','diretor','head','gerente')):
        score+=35; reasons.append('cargo declarado decisor/influenciador')
    if (lead.get('company_size') or 0)>200:
        score+=25; reasons.append('porte declarado acima de 200')
    if (lead.get('sector') or '').lower() in ('financeiro','saúde','governo','manufatura','tecnologia'):
        score+=10; reasons.append('setor declarado aderente')
    if lead.get('linkedin_url'):
        score+=5; reasons.append('link profissional declarado, não verificado')
    return score,reasons


def enrich(lead_id, qid=None, company_confirmed=False):
    lead=get_lead(lead_id)
    if lead['suppressed']:
        raise ValueError('Lead em opt-out: enriquecimento interrompido.')
    if qid:
        if not company_confirmed:
            raise ValueError('Confirme que a entidade escolhida corresponde à empresa do lead.')
        source=fetch_company(qid)
        kind='PUBLIC_COMPANY'
    elif lead['synthetic']:
        source={'mode':'SYNTHETIC','scope':'Persona fictícia; perfil declarado, sem validação externa.', 'retrieved_at':datetime.now(timezone.utc).isoformat()}
        kind='SYNTHETIC'
    else:
        raise ValueError('Selecione uma fonte pública para enriquecer um lead real.')
    score,reasons=score_profile(lead)
    summary=f"Dados declarados: {lead.get('role') or 'cargo não informado'}; {lead.get('company') or 'empresa não informada'}; setor {lead.get('sector') or 'não informado'}; interesse {lead.get('security_interest') or 'não informado'}. Score: {'; '.join(reasons)}."
    if kind=='PUBLIC_COMPANY':
        summary+=f" Fonte pública da organização: {source['company_label']} — {source['description']}. Não comprova vínculo profissional."
    else:
        summary+=' Enriquecimento sintético para demonstração.'
    save_enrichment(lead_id,summary,score,kind,source,source.get('qid'))
    return summary,score
