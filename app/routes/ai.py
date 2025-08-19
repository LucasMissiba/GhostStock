from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
import os
import re
from ..ai_intents import get_intent_response

from ..models import Item
from .. import db

ai_bp = Blueprint("ai", __name__, url_prefix="/ai")


@dataclass
class Suggestion:
    title: str
    details: str

    def to_text(self) -> str:
        return f"{self.title}\n{self.details}"


@ai_bp.route("/solve", methods=["GET", "POST"])
def solve():
    """Endpoint simples de sugestões baseadas nos dados (heurísticas).
    Entrada: { q: string }
    Saída: { text: string }
    """
    if request.method == "GET":
        q = (request.args.get("q") or "").strip()
    else:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            data = {}
        q: str = (data.get("q") or "").strip()
    if not q:
        return jsonify({"text": "Olá! Faça sua pergunta. Ex.: 'Quantos disponíveis?'"})

    q_lower = q.lower()

                                                            
    try:
        static_root = current_app.static_folder or "app/static"
    except Exception:
        static_root = "app/static"
    intent_text = get_intent_response(q_lower, static_root)
    if intent_text:
        return jsonify({"text": intent_text})

                                           
    if any(k in q_lower for k in ["dispon", "estoque", "resumo", "quantos"]):
        total = db.session.query(Item).count()
        disponiveis = db.session.query(Item).filter(Item.status == "disponivel").count()
        em_uso = db.session.query(Item).filter(Item.status.in_(["locado", "em_uso", "em uso"])) .count()
                                                                                          
        cutoff_due = datetime.utcnow() - timedelta(days=60)
        em_manutencao = db.session.query(Item).filter(Item.status == "em_manutencao").count()
        aguardando = (
            db.session.query(Item)
            .filter(
                Item.last_maintenance_date.isnot(None),
                Item.last_maintenance_date > (datetime.utcnow() - timedelta(days=60)),
                Item.last_maintenance_date <= (datetime.utcnow() - timedelta(days=45)),
            )
            .count()
        )
        pct_disp = (disponiveis / total) * 100 if total else 0
        if pct_disp < 10:
            sug = Suggestion(
                title="Alerta: Disponibilidade baixa",
                details=(
                    f"Total: {total} • Disponíveis: {disponiveis} ({pct_disp:.1f}%) • Em uso: {em_uso}\n"
                    f"Recomendação: Transferir itens de estoques com maior folga ou abrir ordem de compra para +{max(1, int(total*0.05))} unidades."
                ),
            )
        else:
            sug = Suggestion(
                title="Resumo do estoque",
                details=(
                    f"Total: {total}\nDisponíveis: {disponiveis}\nEm uso: {em_uso}\n"
                    f"Em manutenção: {em_manutencao}\nAguardando manutenção: {aguardando}"
                ),
            )
        return jsonify({"text": sug.to_text()})

                            
    m = re.search(r"\b([a-z]{2,6}\d{3,})\b", q, re.I)
    if m:
        code = m.group(1).upper()
        item = db.session.query(Item).filter((Item.code == code) | (Item.name == code)).first()
        if not item:
            return jsonify({"text": f"Não encontrei o item {code}."})
        rec_parts = [
            f"Status: {item.status}",
            f"Tipo: {item.item_type or '-'}",
            f"Local: {item.location or '-'}",
        ]
                    
        if item.last_maintenance_date:
            days = (datetime.utcnow() - item.last_maintenance_date).days
            if days >= 60:
                rec_parts.append("Recomendação: abrir ordem de manutenção (vencida).")
            elif days >= 45:
                rec_parts.append("Recomendação: planejar manutenção (em breve).")
        text = f"Item {code}\n" + "\n".join(rec_parts)
        return jsonify({"text": text})

                                 
    if any(k in q_lower for k in ["manuten", "aguard", "vencid"]):
        due = (
            db.session.query(Item)
            .filter(Item.last_maintenance_date.isnot(None))
            .filter(Item.last_maintenance_date <= (datetime.utcnow() - timedelta(days=60)))
            .count()
        )
        soon = (
            db.session.query(Item)
            .filter(Item.last_maintenance_date.isnot(None))
            .filter(
                Item.last_maintenance_date > (datetime.utcnow() - timedelta(days=60)),
                Item.last_maintenance_date <= (datetime.utcnow() - timedelta(days=45)),
            )
            .count()
        )
        return jsonify({
            "text": (
                "Manutenção — visão geral\n"
                f"Vencidas: {due}\nAguardando (em breve): {soon}\n"
                "Ação sugerida: priorizar vencidas, depois programar as em breve por rota/estoque."
            )
        })

                                                         
    out_topics = [
        "clima", "tempo", "chuva", "calor", "futebol", "jogo", "partida", "gol",
        "política", "elei", "celebridade", "filme", "série", "música", "piada", "receita",
    ]
    if any(t in q_lower for t in out_topics):
        return jsonify({
            "text": "Isso foge do meu segmento. Posso ajudar com estoque, manutenção, relatórios, mapa e rastreabilidade."
        })

                                           
    return jsonify({
        "text": (
            "Não tenho essa resposta pronta. Posso ajudar com: resumo do estoque, manutenção (vencida/aguardando), localização de item por código e relatórios. Ex.: 'Resumo do estoque', 'Manutenção', 'Status CAM00123'."
        )
    })


@ai_bp.route("/chat", methods=["GET", "POST"])
def chat():
    """Endpoint de IA real com fallback.
    Usa OpenAI se OPENAI_API_KEY estiver configurada; caso contrário, delega ao solver.
    """
    if request.method == "GET":
        q = (request.args.get("q") or "").strip()
    else:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
                                                                         
            data = {}
        q: str = (data.get("q") or "").strip()
    if not q:
        return jsonify({"text": "Olá! Faça sua pergunta. Ex.: 'Quantos disponíveis?'"})

    api_key = current_app.config.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    try:
        from openai import OpenAI
        sys_prompt = (
            "Você é a GhostIA, assistente para gestão de estoque hospitalar. "
            "Responda em português do Brasil, de forma objetiva."
        )
        msg = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": q},
        ]

        if api_key:
                            
            client = OpenAI(api_key=api_key)
            model = current_app.config.get("OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
            resp = client.chat.completions.create(model=model, messages=msg, temperature=0.2)
            text = resp.choices[0].message.content.strip()
            return jsonify({"text": text})

                                                            
        base_url = current_app.config.get("OLLAMA_BASE_URL") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        model = current_app.config.get("OLLAMA_MODEL") or os.getenv("OLLAMA_MODEL", "llama3.1")
        client = OpenAI(base_url=base_url, api_key="ollama")
        resp = client.chat.completions.create(model=model, messages=msg, temperature=0.2)
        text = resp.choices[0].message.content.strip()
        return jsonify({"text": text})
    except Exception:
                             
        return solve()


