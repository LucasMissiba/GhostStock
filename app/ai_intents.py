from __future__ import annotations

import json
import os
import re
from typing import Optional, List, Tuple


_CACHE: dict = {
    "compiled": [],                                  
    "mtime": None,
}


def _default_intents() -> List[Tuple[str, str]]:
    """Returns a list of (regex_pattern, response) pairs.
    Designed to be easily extensible up to ~1000 entries via JSON file.
    """
                                                
    pairs: List[Tuple[str, str]] = [
        (r"\b(oi|olá|ola|eai|opa|bom dia|boa tarde|boa noite)\b", "Olá! Posso ajudar com estoque, manutenção, relatórios, mapa e busca de itens."),
        (r"\b(ajuda|como usar|o que você faz|para que serve|tutorial|manual)\b", "Sou a GhostIA: respondo perguntas sobre estoque, manutenção, relatórios e rastreabilidade."),
        (r"\b(quem é você|quem é a ghostia|sobre a ghostia)\b", "Sou a GhostIA, assistente de gestão de estoque hospitalar integrada ao GhostStock."),
        (r"\b(obrigado|valeu|obg)\b", "De nada! Se precisar, pergunte sobre estoque ou manutenção."),
        (r"\b(tchau|até mais|falou|até logo)\b", "Até mais! Quando voltar, posso atualizar números ou localizar itens."),
        (r"\b(suporte|contato|email|telefone)\b", "Suporte: suporte@ghoststock.local"),
        (r"\b(relat[óo]rio[s]?|pdf|excel|planilha|exportar)\b", "Relatórios: use a aba 'Relatórios' para gerar PDF/Excel com filtros."),
        (r"\b(indicadores|gr[áa]fico[s]?|kpi|dashboard)\b", "Indicadores: abra a aba 'Indicadores' para ver KPIs e gráficos."),
        (r"\b(manueten[cç][aã]o|manuten[cç][aã]o|ordem|calend[áa]rio|agenda)\b", "Manutenção: use 'Manutenção' para abrir ordens ou ver o calendário."),
        (r"\b(map[ae]|localiza[cç][aã]o geral|cluster|mapa geral)\b", "Mapa: a aba 'Mapa' mostra visão geral com clusters e ícones por tipo."),
        (r"\b(cadastrar|novo item|adicionar item|incluir item)\b", "Cadastro: 'Itens' > 'Novo item'. Código é sequencial e status começa 'disponível'."),
        (r"\b(login|acesso|senha|entrar)\b", "Para acesso/recuperação de senha, contate o administrador do sistema."),
        (r"\b(tema|modo escuro|modo claro|dark mode)\b", "Tema: ajuste em 'Configurações' (ícone de engrenagem)."),
        (r"\b(buscar item|procurar item|localizar item)\b", "Você pode buscar por nome/código em 'Itens' ou perguntar 'Status CAM00123'."),
        (r"\b(qr|qrcode|c[óo]digo qr)\b", "QR: gere em 'Itens' > 'QR PNG' ou 'QR PDF'."),
        (r"\b(estoque baixo|alerta|falta|reposição)\b", "Alertas: quando disponibilidade cair, sugerimos transferir ou comprar."),
        (r"\b(pdf|imprimir|baixar relat[óo]rio)\b", "Use 'Relatórios' para gerar PDF filtrado e fazer download."),
        (r"\b(colch[aã]o pneum[aá]tico|cpneu)\b", "CPNEU incluído em filtros e gráficos. Consulte 'Indicadores' para distribuição por tipo."),
        (r"\b(em manuten[cç][aã]o|aguardando manuten[cç][aã]o)\b", "Em 'Manutenção' você vê ordens em aberto e próximas. No 'Indicadores' há os totais."),
        (r"\b(endere[cç]o|coordenada|latitude|longitude|rastreamento|rastreabilidade)\b", "Rastreabilidade: em 'Itens' > 'Ver', há link para abrir localização no Google Maps (se disponível)."),
    ]
    return pairs


def _load_from_json(static_root: str) -> Optional[List[Tuple[str, str]]]:
    path = os.path.join(static_root, "ai", "intents.json")
    if not os.path.exists(path):
        return None
    try:
        mtime = os.path.getmtime(path)
        if _CACHE.get("mtime") == mtime and _CACHE.get("compiled"):
                              
            return [(p.pattern, r) for p, r in _CACHE["compiled"]]
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        pairs: List[Tuple[str, str]] = []
        for entry in data:
                                                                     
            patterns = entry.get("patterns") or []
            resp = entry.get("response") or ""
            for pat in patterns:
                pairs.append((pat, resp))
                           
        compiled = [(re.compile(pat, re.I), resp) for pat, resp in pairs]
        _CACHE["compiled"] = compiled
        _CACHE["mtime"] = mtime
        return pairs
    except Exception:
        return None


def get_intent_response(text: str, static_root: str) -> Optional[str]:
    """Returns a response if any intent pattern matches the text.
    Loads from static intents.json when available; otherwise uses defaults.
    Supports large sets (hundreds to ~1000 entries).
    """
    if not text:
        return None
                                         
    pairs = _load_from_json(static_root)
    if pairs is None:
                                                   
        if not _CACHE.get("compiled"):
            default = _default_intents()
            _CACHE["compiled"] = [(re.compile(pat, re.I), resp) for pat, resp in default]
        compiled = _CACHE["compiled"]
    else:
        compiled = _CACHE["compiled"]

    for pattern, response in compiled:
        if pattern.search(text):
            return response
    return None


