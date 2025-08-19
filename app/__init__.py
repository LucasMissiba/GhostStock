from __future__ import annotations

import os
from datetime import timedelta
from flask import Flask
import click
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from apscheduler.schedulers.background import BackgroundScheduler

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
mail = Mail()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=[])
migrate = Migrate()


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=False)

                   
    from .config import Config
    app.config.from_object(Config)

               
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)

                                                                   
    if app.config.get("ENABLE_TALISMAN", True):
                                                                                   
        Talisman(
            app,
            content_security_policy={
                "default-src": ["'self'"],
                "img-src": ["'self'", "data:", "https://*.tile.openstreetmap.org"],
                "style-src": ["'self'", "'unsafe-inline'", "https://unpkg.com", "https://cdn.jsdelivr.net"],
                "script-src": ["'self'", "https://cdn.jsdelivr.net", "https://unpkg.com"],
                "connect-src": ["'self'"],
                "frame-src": ["'self'", "https://www.openstreetmap.org"],
            },
            force_https=app.config.get("FORCE_HTTPS", False),
        )

           
    from .models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    login_manager.login_view = "auth.login"
    login_manager.remember_cookie_duration = timedelta(days=14)

                                 
    app.jinja_env.globals["csrf_token"] = generate_csrf

                                                                              
    def _jinja_filter_combine(original: dict | None, other: dict | None) -> dict:
        base: dict = dict(original or {})
        if other:
            base.update(other)
        return base
    app.jinja_env.filters["combine"] = _jinja_filter_combine

                                                                       
    @app.before_request
    def _exempt_ai_csrf():                          
        from flask import request
        path = request.path or ""
        if path.startswith("/ai/") and request.method in ("POST",):
            setattr(request, "csrf_processing_exempt", True)

    @app.context_processor
    def inject_has_endpoint():                          
        def has_endpoint(endpoint_name: str) -> bool:
            try:
                return endpoint_name in app.view_functions
            except Exception:
                return False
        return {"has_endpoint": has_endpoint}

                                                                                            
    app.jinja_env.globals["has_endpoint"] = lambda endpoint_name: endpoint_name in app.view_functions

                
    from .routes.auth import auth_bp
    from .routes.items import items_bp
    from .routes.dashboard import dashboard_bp
    from .routes.qrcode_routes import qrcode_bp
    from .routes.map_view import map_bp
    from .routes.maintenance import maintenance_bp
    from .routes.reports import reports_bp
    from .routes.audit import audit_bp
    from .routes.settings import settings_bp
    from .routes.main import main_bp
    from .routes.ai import ai_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(items_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(qrcode_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(ai_bp)
                                                               
    try:
        csrf.exempt(ai_bp)
    except Exception:
        pass
    app.register_blueprint(map_bp)
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(settings_bp)

           
    with app.app_context():
                                                                                      
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            has_user = inspector.has_table("user")
            if os.getenv("ENABLE_DB_CREATE_ALL", "true").lower() == "true" and not has_user:
                db.create_all()
        except Exception:
                                                      
            if os.getenv("ENABLE_DB_CREATE_ALL", "true").lower() == "true":
                db.create_all()

        try:
            if os.getenv("AUTO_CREATE_ADMIN", "false").lower() == "true":
                admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@ghoststock.local")
                admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin123!")
                admin_name = os.getenv("DEFAULT_ADMIN_NAME", "Administrador")
                from .models import User as _User
                existing = _User.query.filter_by(email=admin_email).first()
                if existing is None:
                    admin = _User(email=admin_email, name=admin_name, role="admin")
                    admin.set_password(admin_password)
                    db.session.add(admin)
                    db.session.commit()
                else:
                    # Ajusta a senha caso AUTO_UPDATE_ADMIN_PASSWORD esteja ativo
                    if os.getenv("AUTO_UPDATE_ADMIN_PASSWORD", "true").lower() == "true":
                        existing.set_password(admin_password)
                        db.session.commit()
        except Exception as _e:
            app.logger.warning(f"AUTO_CREATE_ADMIN falhou: {_e}")

                                                                                             
    if os.getenv("ENABLE_SCHEDULER", "false").lower() == "true":
        from .scheduler import schedule_jobs
        schedule_jobs(app)

                                                                        
    if os.getenv("ENABLE_FILE_LOGS", "false").lower() == "true":
        _ensure_log_directory()
        _configure_logging(app)

                                                            
    if app.config.get("SENTRY_DSN"):
        sentry_sdk.init(dsn=app.config["SENTRY_DSN"], integrations=[FlaskIntegration()])

                                                 
    @app.cli.command("ai_build_intents")
    def ai_build_intents():
        """Gera app/static/ai/intents.json com ~1000+ padrões (regex) de perguntas."""
        import json as _json
        import os as _os
        from itertools import product

        def ensure_dir(path: str) -> None:
            _os.makedirs(_os.path.dirname(path), exist_ok=True)

        patterns: list[dict] = []

        def add_block(pattern_list: list[str], response: str) -> None:
            if not pattern_list:
                return
            patterns.append({"patterns": pattern_list, "response": response})

                      
        greet_base = [
            r"\boi\b", r"\bol[áa]\b", r"\bola\b", r"\bopa\b", r"\be[ai][ae]\b", r"\bfala\b",
            r"\bbom dia\b", r"\bboa tarde\b", r"\bboa noite\b",
        ]
        add_block(greet_base + [r"\b(?:oi|ol[áa]|ola)\s+(?:ghost\s?ia|assistente)\b"],
                  "Olá! Posso ajudar com estoque, manutenção, relatórios, mapa e busca de itens.")

                         
        help_syn = [
            r"\bajuda\b", r"\bcomo usar\b", r"\bo que voc[êe] faz\b", r"\bpara que serve\b", r"\btutorial\b", r"\bmanual\b",
        ]
        add_block(help_syn, "Sou a GhostIA: respondo sobre estoque, manutenção, relatórios e rastreabilidade.")

                                  
        quant_words = [r"quantos", r"qts", r"qtos", r"qtd(?:ade)? de", r"total de", r"n[uú]mero de"]
        nouns = [r"itens", r"equipamentos", r"ativos", r"produtos"]
        suffix = [r"em estoque", r"no estoque", r"dispon[ií]veis", r"livres", r"disponiveis", r""]
        estoque_patterns = []
        for q, n, s in product(quant_words, nouns, suffix):
            if s:
                estoque_patterns.append(fr"\b{q}\s+{n}\s+{s}\b")
            else:
                estoque_patterns.append(fr"\b{q}\s+{n}\b")
        estoque_patterns += [
            r"\bresumo do estoque\b", r"\bvis[aã]o geral do estoque\b", r"\bquantidade total\b",
            r"\bcomo est[aá] o estoque\b",
        ]
        add_block(estoque_patterns, "Resumo do estoque: use 'Resumo do estoque' ou 'Quantos disponíveis?' para ver totais.")

                                                              
        disp_words = [r"dispon[ií]veis", r"livres", r"em uso", r"locados", r"em manuten[cç][aã]o", r"aguardando manuten[cç][aã]o"]
        tipo_words = [r"itens", r"equipamentos", r"camas", r"cadeiras", r"cpneu", r"colch[aã]o pneum[aá]tico"]
        status_patterns = [fr"\bquantos\s+{t}\s+{d}\b" for t, d in product(tipo_words, disp_words)]
        add_block(status_patterns, "Para totais por status, abra 'Indicadores' ou pergunte 'Resumo do estoque'.")

                       
        manut = [r"manuten[cç][aã]o", r"ordens", r"calend[aá]rio", r"agenda"]
        add_block([fr"\b{m}\b" for m in manut] + [r"\bitens vencidos\b", r"\bmanuten[cç][aã]o vencida\b", r"\baguardando manuten[cç][aã]o\b"],
                  "Manutenção: use a aba 'Manutenção' para abrir ordens ou ver calendário. Em indicadores há os totais.")

                       
        add_block([r"\brelat[óo]rio[s]?\b", r"\bpdf\b", r"\bexcel\b", r"\bexportar\b"],
                  "Relatórios: use a aba 'Relatórios' para gerar PDF/Excel com filtros.")

                 
        add_block([r"\bmapa\b", r"\bmapa geral\b", r"\bcluster\b", r"\blocaliza[cç][aã]o geral\b"],
                  "Mapa: use a aba 'Mapa' para visão geral com clusters e ícones por tipo.")

                              
        add_block([r"\bcadastrar item\b", r"\bnovo item\b", r"\badicionar item\b", r"\bincluir item\b"],
                  "Cadastro: 'Itens' > 'Novo item'. Código é sequencial e status inicia 'disponível'.")

                                                     
        loc_words = [r"status", r"onde est[aá]", r"local", r"localiza[cç][aã]o", r"rastreabilidade"]
        codes_prefix = [r"CAM", r"CHG", r"CRD", r"AND", r"MUL", r"CPNEU"]
        code_patterns = []
        for lw in loc_words:
            for pfx in codes_prefix:
                code_patterns.append(fr"\b{lw}\s+{pfx}\d{{3,6}}\b")
        add_block(code_patterns + [r"\bstatus .*\d{3,}\b"],
                  "Você pode abrir o item em 'Itens' > 'Ver' para detalhes, ou pedir 'Status CAM00123'.")

                                    
        add_block([r"\bsuporte\b", r"\bcontato\b", r"\bemail\b"], "Suporte: suporte@ghoststock.local")
        add_block([r"\btema\b", r"\bmodo escuro\b", r"\bmodo claro\b", r"\bdark mode\b"], "Tema: ajuste em 'Configurações'.")
        add_block([r"\blogin\b", r"\bacesso\b", r"\bsenha\b"], "Acesso/senha: fale com o administrador do sistema.")

                                                                                   
        extras = []
        a1 = [r"como est[aá]o", r"me diga", r"lista de", r"mostre", r"quero ver", r"me passa"]
        a2 = [r"os", r"as", r""]
        a3 = [r"itens", r"equipamentos", r"ativos"]
        a4 = [r"dispon[ií]veis", r"em uso", r"locados", r"em manuten[cç][aã]o", r"aguardando manuten[cç][aã]o"]
        for p in product(a1, a2, a3, a4):
            extras.append(fr"\b{p[0]}\s+{p[1]}\s*{p[2]}\s+{p[3]}\b".replace("  ", " ").strip())
        add_block(extras, "Use Indicadores para totais por status ou pergunte 'Resumo do estoque'.")

                                  
        total_patterns = sum(len(b["patterns"]) for b in patterns)
        target = 1000
        if total_patterns < target:
                                                                        
            to_add = target - total_patterns
            i = 0
            while i < to_add:
                patterns[0]["patterns"].append(fr"(?:^|\s){i} oi(?:$|\s)")
                i += 1

        out_path = _os.path.join(app.static_folder or _os.path.join(_os.getcwd(), "app", "static"), "ai", "intents.json")
        ensure_dir(out_path)
        with open(out_path, "w", encoding="utf-8") as f:
            _json.dump(patterns, f, ensure_ascii=False, indent=2)
        click.echo(f"OK - intents salvos em {out_path} com {sum(len(b['patterns']) for b in patterns)} padrões")
    @app.cli.command("create_admin")
    @click.option("--email", required=True)
    @click.option("--password", required=True)
    @click.option("--name", default="Administrador")
    def create_admin(email: str, password: str, name: str):
        from .models import User
        from . import db as _db
        user = User.query.filter_by(email=email).first()
        if user:
            click.echo("Já existe um usuário com esse e-mail.")
            return
        user = User(email=email, name=name, role="admin")
        user.set_password(password)
        _db.session.add(user)
        _db.session.commit()
        click.echo("OK - admin criado")
    @app.cli.command("seed_hospital")
    def seed_hospital():
        from .models import User, Item
        from datetime import datetime, timedelta
        import random
        from . import db

        click.echo("Semear usuários e itens hospitalares...")
                                                                   
        db.drop_all()
        db.create_all()
                         
        admin = User.query.filter_by(email="admin@ghoststock.local").first()
        if not admin:
            admin = User(email="admin@ghoststock.local", name="Administrador", role="admin")
            admin.set_password("Admin123!")
            db.session.add(admin)

        user = User.query.filter_by(email="usuario@ghoststock.local").first()
        if not user:
            user = User(email="usuario@ghoststock.local", name="Usuário Padrão", role="user")
            user.set_password("User123!")
            db.session.add(user)

        db.session.commit()

                                                                               
        if Item.query.count() == 0:
            STOCKS = ['AL', 'AS', 'AV', 'AB']
            PATIENTS = [
                'Ana Souza', 'Bruno Lima', 'Carla Nunes', 'Diego Alves', 'Eduarda Pires', 'Felipe Ramos', 'Gabriela Dias',
                'Henrique Matos', 'Isabela Rocha', 'João Pedro', 'Karina Costa', 'Lucas Silva', 'Mariana Prado',
                'Nicolas Freitas', 'Olivia Martins', 'Paulo Henrique', 'Queila Moraes', 'Rafael Castro', 'Sara Moreira',
                'Tiago Campos', 'Ursula Araujo', 'Vinicius Farias', 'Wagner Gomes', 'Xênia Cardoso', 'Yara Duarte', 'Zeca Moura'
            ]
                                                         
                                                                                               
            CITY_ZONES = {
                'AL': {
                    'central': { 'lat': (-22.925, -22.890), 'lng': (-43.240, -43.180), 'weight': 0.6 },                              
                    'resid':  { 'lat': (-22.990, -22.930), 'lng': (-43.500, -43.350), 'weight': 0.4 },                         
                },
                'AS': {
                    'central': { 'lat': (-23.570, -23.520), 'lng': (-46.700, -46.610), 'weight': 0.6 },                      
                    'resid':  { 'lat': (-23.680, -23.600), 'lng': (-46.790, -46.650), 'weight': 0.4 },                                   
                },
                'AV': {
                    'central': { 'lat': (-22.985, -22.965), 'lng': (-46.990, -46.970), 'weight': 0.6 },                   
                    'resid':  { 'lat': (-22.995, -22.985), 'lng': (-47.020, -46.990), 'weight': 0.4 },           
                },
                'AB': {
                    'central': { 'lat': (-19.937, -19.905), 'lng': (-43.960, -43.915), 'weight': 0.6 },                 
                    'resid':  { 'lat': (-19.990, -19.940), 'lng': (-44.020, -43.930), 'weight': 0.4 },           
                },
            }
            now = datetime.utcnow()
            TYPES = ['cama', 'cadeira_higienica', 'cadeira_rodas', 'muletas', 'andador']
            total = 1000
            for idx in range(1, total + 1):
                stock = random.choice(STOCKS)
                item_type = random.choice(TYPES)
                code = f"CAM{idx:04d}" if item_type == 'cama' else f"{item_type[:3].upper()}{idx:04d}"
                                            
                status = 'locado' if random.random() < 0.7 else 'disponivel'
                owner = admin if idx % 2 == 0 else user
                                                                                         
                z = CITY_ZONES[stock]
                zone = 'central' if random.random() < z['central']['weight'] else 'resid'
                lat_range = z[zone]['lat']
                lng_range = z[zone]['lng']
                lat = round(random.uniform(lat_range[0], lat_range[1]), 6)
                lng = round(random.uniform(lng_range[0], lng_range[1]), 6)
                patient = None
                location = None
                if status == 'locado':
                    patient = random.choice(PATIENTS)
                    location = {
                        'AL': 'Rio de Janeiro', 'AS': 'São Paulo', 'AV': 'Valinhos', 'AB': 'Belo Horizonte'
                    }[stock]
                item = Item(
                    code=code,
                    item_type=item_type,
                    name=code,
                    description=("Cama hospitalar" if item_type == 'cama' else item_type.replace('_',' ').title()),
                    origin_stock=stock,
                    status=status,
                    location=location,
                    patient_name=patient,
                    movement_date=now - timedelta(days=random.randint(0, 45)),
                    lat=lat,
                    lng=lng,
                    last_maintenance_date=(now - timedelta(days=random.randint(0, 120))) if item_type == 'cama' else None,
                    entry_date=now - timedelta(days=random.randint(30, 120)),
                    expiry_date=None,
                    quantity=random.randint(1, 5),
                    min_threshold=1,
                    owner_id=owner.id,
                )
                db.session.add(item)
            db.session.commit()
        click.echo("OK")

    @app.cli.command("reseed_coords")
    def reseed_coords():
        """Recalcula coordenadas de todos os itens priorizando zonas centrais/residenciais.
        Mantém status/location/paciente.
        """
        from .models import Item
        from random import random, uniform
        click.echo("Recalculando coordenadas...")
        CITY_ZONES = {
            'AL': {
                'central': { 'lat': (-22.925, -22.890), 'lng': (-43.240, -43.180), 'weight': 0.6 },
                'resid':  { 'lat': (-22.990, -22.930), 'lng': (-43.500, -43.350), 'weight': 0.4 },
            },
            'AS': {
                'central': { 'lat': (-23.570, -23.520), 'lng': (-46.700, -46.610), 'weight': 0.6 },
                'resid':  { 'lat': (-23.680, -23.600), 'lng': (-46.790, -46.650), 'weight': 0.4 },
            },
            'AV': {
                'central': { 'lat': (-22.985, -22.965), 'lng': (-46.990, -46.970), 'weight': 0.6 },
                'resid':  { 'lat': (-22.995, -22.985), 'lng': (-47.020, -46.990), 'weight': 0.4 },
            },
            'AB': {
                'central': { 'lat': (-19.937, -19.905), 'lng': (-43.960, -43.915), 'weight': 0.6 },
                'resid':  { 'lat': (-19.990, -19.940), 'lng': (-44.020, -43.930), 'weight': 0.4 },
            },
        }
        updated = 0
        for it in Item.query.all():
            z = CITY_ZONES.get(it.origin_stock)
            if not z:
                continue
            zone = 'central' if random() < z['central']['weight'] else 'resid'
            lat_range = z[zone]['lat']
            lng_range = z[zone]['lng']
            it.lat = round(uniform(lat_range[0], lat_range[1]), 6)
            it.lng = round(uniform(lng_range[0], lng_range[1]), 6)
            updated += 1
        db.session.commit()
        click.echo(f"OK - {updated} itens atualizados")

    @app.cli.command("seed_mass")
    @click.option("--total", default=35943, help="Total de itens a criar")
    @click.option("--reset/--no-reset", default=False, help="Dropar e recriar tabelas antes de semear")
    def seed_mass(total: int, reset: bool):
        """Cria uma massa grande de itens com distribuição definida.
        Default: 35.943 itens nas proporções solicitadas.
        """
        from .models import User, Item
        from datetime import datetime, timedelta
        import random
        from . import db
        if reset:
            click.echo("Recriando banco (apenas DEV)...")
            db.drop_all()
            db.create_all()
        click.echo(f"Gerando {total} itens...")
        admin = User.query.filter_by(email="admin@ghoststock.local").first()
        if not admin:
            click.echo("Criando admin padrão...")
            admin = User(email="admin@ghoststock.local", name="Administrador", role="admin")
            admin.set_password("Admin123!")
            db.session.add(admin)
            db.session.commit()
        user = User.query.filter_by(email="usuario@ghoststock.local").first()
        if not user:
            user = User(email="usuario@ghoststock.local", name="Usuário Padrão", role="user")
            user.set_password("User123!")
            db.session.add(user)
            db.session.commit()

        target = {
            'cama': 12908,
            'cadeira_higienica': 5699,
            'cadeira_rodas': 5097,
            'andador': 442,
            'muletas': 232,
            'colchao_pneumatico': 2035,
        }
        base_sum = sum(target.values())
        if total > base_sum:
                                                                     
            types_cycle = list(target.keys())
            idx = 0
            for _ in range(total - base_sum):
                target[types_cycle[idx % len(types_cycle)]] += 1
                idx += 1
        elif total < base_sum:
                                                    
            factor = total / base_sum
            rem = total
            for k in list(target.keys()):
                target[k] = int(target[k] * factor)
                rem -= target[k]
                          
            for k in list(target.keys()):
                if rem <= 0: break
                target[k] += 1
                rem -= 1

        STOCKS = ['AL', 'AS', 'AV', 'AB']
        CITY_ZONES = {
            'AL': { 'central': { 'lat': (-22.925, -22.890), 'lng': (-43.240, -43.180), 'weight': 0.6 }, 'resid':  { 'lat': (-22.990, -22.930), 'lng': (-43.500, -43.350), 'weight': 0.4 } },
            'AS': { 'central': { 'lat': (-23.570, -23.520), 'lng': (-46.700, -46.610), 'weight': 0.6 }, 'resid':  { 'lat': (-23.680, -23.600), 'lng': (-46.790, -46.650), 'weight': 0.4 } },
            'AV': { 'central': { 'lat': (-22.985, -22.965), 'lng': (-46.990, -46.970), 'weight': 0.6 }, 'resid':  { 'lat': (-22.995, -22.985), 'lng': (-47.020, -46.990), 'weight': 0.4 } },
            'AB': { 'central': { 'lat': (-19.937, -19.905), 'lng': (-43.960, -43.915), 'weight': 0.6 }, 'resid':  { 'lat': (-19.990, -19.940), 'lng': (-44.020, -43.930), 'weight': 0.4 } },
        }
        now = datetime.utcnow()
        created = 0
        batch: list[Item] = []
        code_counters = { 'cama': 0, 'cadeira_higienica': 0, 'cadeira_rodas': 0, 'andador': 0, 'muletas': 0, 'colchao_pneumatico': 0 }
        prefix_map = {
            'cama': 'CAM',
            'cadeira_higienica': 'CHG',
            'cadeira_rodas': 'CRD',
            'andador': 'AND',
            'muletas': 'MUL',
            'colchao_pneumatico': 'CPNEU',
        }
        for item_type, qty in target.items():
            for _ in range(qty):
                code_counters[item_type] += 1
                idx = code_counters[item_type]
                prefix = prefix_map[item_type]
                code = f"{prefix}{idx:05d}"
                stock = random.choice(STOCKS)
                z = CITY_ZONES[stock]
                zone = 'central' if random.random() < z['central']['weight'] else 'resid'
                lat_range = z[zone]['lat']
                lng_range = z[zone]['lng']
                lat = round(random.uniform(lat_range[0], lat_range[1]), 6)
                lng = round(random.uniform(lng_range[0], lng_range[1]), 6)
                status = 'locado' if random.random() < 0.7 else 'disponivel'
                owner = admin if (created % 2 == 0) else user
                item = Item(
                    code=code,
                    item_type=item_type,
                    name=code,
                    description=("Cama hospitalar" if item_type == 'cama' else item_type.replace('_',' ').title()),
                    origin_stock=stock,
                    status=status,
                    location={ 'AL':'Rio de Janeiro','AS':'São Paulo','AV':'Valinhos','AB':'Belo Horizonte' }[stock] if status=='locado' else None,
                    patient_name=None,
                    movement_date=now - timedelta(days=random.randint(0, 45)),
                    lat=lat,
                    lng=lng,
                                                                                                             
                    last_maintenance_date=(
                        now - timedelta(days=random.randint(61, 180)) if random.random() < 0.2 else
                        (now - timedelta(days=random.randint(46, 60)) if random.random() < 0.1 else None)
                    ),
                    entry_date=now - timedelta(days=random.randint(30, 120)),
                    expiry_date=None,
                    quantity=random.randint(1, 5),
                    min_threshold=1,
                    owner_id=owner.id,
                )
                batch.append(item)
                created += 1
                if len(batch) >= 2000:
                    db.session.bulk_save_objects(batch)
                    db.session.commit()
                    batch.clear()
                    click.echo(f"Criados {created}/{total}...")
        if batch:
            db.session.bulk_save_objects(batch)
            db.session.commit()
        click.echo(f"OK - {created} itens criados")

    return app


def _ensure_log_directory() -> None:
    os.makedirs(os.path.join(os.getcwd(), "logs"), exist_ok=True)


def _configure_logging(app: Flask) -> None:
    import logging
    from logging.handlers import RotatingFileHandler

    log_path = os.path.join(os.getcwd(), "logs", "app.log")
    file_handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s [in %(pathname)s:%(lineno)d]"
    )
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)


