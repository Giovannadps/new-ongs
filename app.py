import os
import sqlite3
import base64
import calendar as pycalendar
from datetime import datetime, timezone, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "newongs-chave-secreta")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "newongs.db")


def conectar_banco():
    conexao = sqlite3.connect(DATABASE)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def hoje_brasilia():
    return datetime.now(timezone(timedelta(hours=-3))).date()


def carregar_preferencias(usuario_id):
    padrao = {"tamanho_texto":"normal","cor":"normal","fonte":"normal","tema":"claro","idioma":"pt-BR"}
    if not usuario_id: return padrao
    conexao=conectar_banco()
    row=conexao.execute("SELECT tamanho_texto,cor,fonte,tema,idioma FROM preferencias_acessibilidade WHERE usuario_id=?",(usuario_id,)).fetchone()
    conexao.close()
    return {k:(row[k] or v) for k,v in padrao.items()} if row else padrao


def classes_acessibilidade(p):
    return f"acess-texto-{p['tamanho_texto']} acess-cor-{p['cor']} acess-fonte-{p['fonte']} acess-tema-{p['tema']}"


def criar_banco():
    conexao = conectar_banco()

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            birthdate TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS profissionais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            especialidade TEXT NOT NULL,
            registro_profissional TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS administradores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS palestras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            categoria TEXT NOT NULL,
            video_url TEXT NOT NULL,
            capa_url TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS curtidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            palestra_id INTEGER NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(usuario_id, palestra_id),
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
            FOREIGN KEY(palestra_id) REFERENCES palestras(id) ON DELETE CASCADE
        )
    """)

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS salvos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            palestra_id INTEGER NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(usuario_id, palestra_id),
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
            FOREIGN KEY(palestra_id) REFERENCES palestras(id) ON DELETE CASCADE
        )
    """)

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            mensagem TEXT NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
        )
    """)

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS conversas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            profissional_id INTEGER NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(usuario_id, profissional_id),
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
            FOREIGN KEY(profissional_id) REFERENCES profissionais(id) ON DELETE CASCADE
        )
    """)

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS mensagens_chat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversa_id INTEGER NOT NULL,
            remetente_tipo TEXT NOT NULL CHECK(remetente_tipo IN ('usuario', 'profissional')),
            remetente_id INTEGER NOT NULL,
            mensagem TEXT NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(conversa_id) REFERENCES conversas(id) ON DELETE CASCADE
        )
    """)

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS notificacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, titulo TEXT NOT NULL, mensagem TEXT NOT NULL, lida INTEGER NOT NULL DEFAULT 0, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
        )
    """)
    conexao.execute("""CREATE TABLE IF NOT EXISTS eventos_calendario (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL, tipo TEXT NOT NULL, data_evento TEXT NOT NULL, horario TEXT, local TEXT, descricao TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conexao.execute("""CREATE TABLE IF NOT EXISTS preferencias_acessibilidade (usuario_id INTEGER PRIMARY KEY, tamanho_texto TEXT NOT NULL DEFAULT 'normal', cor TEXT NOT NULL DEFAULT 'normal', fonte TEXT NOT NULL DEFAULT 'normal', tema TEXT NOT NULL DEFAULT 'claro', FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE)""")
    pref_cols={r[1] for r in conexao.execute("PRAGMA table_info(preferencias_acessibilidade)").fetchall()}
    if "idioma" not in pref_cols: conexao.execute("ALTER TABLE preferencias_acessibilidade ADD COLUMN idioma TEXT NOT NULL DEFAULT 'pt-BR'")
    cols={r[1] for r in conexao.execute("PRAGMA table_info(usuarios)").fetchall()}
    if "foto_perfil" not in cols: conexao.execute("ALTER TABLE usuarios ADD COLUMN foto_perfil TEXT")
    cols={r[1] for r in conexao.execute("PRAGMA table_info(feedbacks)").fetchall()}
    if "usuario_id" not in cols: conexao.execute("ALTER TABLE feedbacks ADD COLUMN usuario_id INTEGER")

    admin = conexao.execute(
        "SELECT id FROM administradores WHERE username = ?", ("admin",)
    ).fetchone()
    if admin is None:
        conexao.execute(
            "INSERT INTO administradores (username, password) VALUES (?, ?)",
            ("admin", generate_password_hash("NewOngsAdmin123")),
        )

    conexao.commit()
    conexao.close()


@app.context_processor
def contexto_global():
    p=carregar_preferencias(session.get("usuario_id"))
    return {"acessibilidade_css":classes_acessibilidade(p),"acessibilidade":p,"idioma":p.get("idioma","pt-BR") ,"idioma_html":p.get("idioma","pt-BR")}


def usuario_logado():
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return None
    conexao = conectar_banco()
    usuario = conexao.execute(
        "SELECT * FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()
    conexao.close()
    return usuario


def exigir_login(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("usuario_id"):
            return redirect(url_for("login"))
        if usuario_logado() is None:
            session.pop("usuario_id", None)
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


def exigir_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapper


def pegar_id_youtube(url):
    if not url:
        return None
    if "v=" in url:
        return url.split("v=", 1)[1].split("&", 1)[0]
    if "youtu.be/" in url:
        return url.split("youtu.be/", 1)[1].split("?", 1)[0].split("/", 1)[0]
    if "/embed/" in url:
        return url.split("/embed/", 1)[1].split("?", 1)[0].split("/", 1)[0]
    return None


def buscar_interacoes(usuario_id, palestra_ids=None):
    if not usuario_id:
        return set(), set()
    conexao = conectar_banco()
    parametros = ()
    filtro = ""
    if palestra_ids:
        placeholders = ",".join("?" for _ in palestra_ids)
        filtro = f" AND palestra_id IN ({placeholders})"
        parametros = tuple(palestra_ids)
    curtidas = conexao.execute(
        f"SELECT palestra_id FROM curtidas WHERE usuario_id = ?{filtro}",
        (usuario_id, *parametros),
    ).fetchall()
    salvos = conexao.execute(
        f"SELECT palestra_id FROM salvos WHERE usuario_id = ?{filtro}",
        (usuario_id, *parametros),
    ).fetchall()
    conexao.close()
    return {r["palestra_id"] for r in curtidas}, {r["palestra_id"] for r in salvos}


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/home")
@exigir_login
def home():
    conexao = conectar_banco()
    palestras = conexao.execute(
        "SELECT * FROM palestras ORDER BY criado_em DESC"
    ).fetchall()
    conexao.close()
    ids = [p["id"] for p in palestras]
    curtidas, salvos = buscar_interacoes(session["usuario_id"], ids)
    return render_template("home.html", palestras=palestras, curtidas=curtidas, salvos=salvos)


@app.route("/pesquisa")
@exigir_login
def pesquisa():
    termo = request.args.get("q", "").strip()
    conexao = conectar_banco()
    if termo:
        palestras = conexao.execute("""
            SELECT * FROM palestras
            WHERE titulo LIKE ? OR descricao LIKE ? OR categoria LIKE ?
            ORDER BY criado_em DESC
        """, (f"%{termo}%", f"%{termo}%", f"%{termo}%")).fetchall()
    else:
        palestras = conexao.execute(
            "SELECT * FROM palestras ORDER BY criado_em DESC"
        ).fetchall()
    conexao.close()
    ids = [p["id"] for p in palestras]
    curtidas, salvos = buscar_interacoes(session["usuario_id"], ids)
    return render_template("pesquisa.html", palestras=palestras, termo=termo, curtidas=curtidas, salvos=salvos)


@app.route("/palestra/<int:palestra_id>")
@exigir_login
def assistir_palestra(palestra_id):
    conexao = conectar_banco()
    palestra = conexao.execute(
        "SELECT * FROM palestras WHERE id = ?", (palestra_id,)
    ).fetchone()
    conexao.close()
    if palestra is None:
        return "Palestra não encontrada.", 404
    video_url = palestra["video_url"]
    id_youtube = pegar_id_youtube(video_url)
    if id_youtube:
        idioma_legenda = carregar_preferencias(session["usuario_id"]).get("idioma", "pt-BR")
        legenda_map = {"pt-BR":"pt", "en":"en", "es":"es", "fr":"fr", "it":"it", "de":"de", "ja":"ja", "ko":"ko", "zh-CN":"zh-Hans"}
        cc_lang = legenda_map.get(idioma_legenda, "pt")
        video_url = f"https://www.youtube.com/embed/{id_youtube}?cc_load_policy=1&cc_lang_pref={cc_lang}"
    palestra = dict(palestra)
    palestra["video_url"] = video_url
    curtidas, salvos = buscar_interacoes(session["usuario_id"], [palestra_id])
    return render_template("palestra.html", palestra=palestra, curtida=palestra_id in curtidas, salvo=palestra_id in salvos)


@app.route("/cadastro")
def cadastro():
    return render_template("cadastro.html")


@app.route("/cadastro-usuario", methods=["GET", "POST"])
def cadastro_usuario():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        birthdate = request.form.get("birthdate", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm-password", "")
        if not username or not email or not birthdate or not password:
            return render_template("cadastro_usuario.html", erro="Preencha todos os campos.")
        if password != confirm_password:
            return render_template("cadastro_usuario.html", erro="As senhas não coincidem.")
        if len(password) < 6:
            return render_template("cadastro_usuario.html", erro="A senha deve ter pelo menos 6 caracteres.")
        conexao = conectar_banco()
        try:
            cursor = conexao.execute(
                "INSERT INTO usuarios (username, email, birthdate, password) VALUES (?, ?, ?, ?)",
                (username, email, birthdate, generate_password_hash(password)),
            )
            conexao.commit()
            session.clear()
            session["usuario_id"] = cursor.lastrowid
        except sqlite3.IntegrityError:
            conexao.close()
            return render_template("cadastro_usuario.html", erro="Esse nome de usuário ou e-mail já está cadastrado.")
        conexao.close()
        return redirect(url_for("home"))
    return render_template("cadastro_usuario.html")


@app.route("/cadastro-profissional", methods=["GET", "POST"])
def cadastro_profissional():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        especialidade = request.form.get("especialidade", "").strip()
        registro = request.form.get("registro_profissional", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm-password", "")
        if password != confirm:
            return render_template("cadastro_profissional.html", erro="As senhas não coincidem.")
        if len(password) < 6:
            return render_template("cadastro_profissional.html", erro="A senha deve ter pelo menos 6 caracteres.")
        conexao = conectar_banco()
        try:
            conexao.execute("""
                INSERT INTO profissionais (nome, email, especialidade, registro_profissional, password)
                VALUES (?, ?, ?, ?, ?)
            """, (nome, email, especialidade, registro, generate_password_hash(password)))
            conexao.commit()
        except sqlite3.IntegrityError:
            conexao.close()
            return render_template("cadastro_profissional.html", erro="E-mail ou registro profissional já cadastrado.")
        conexao.close()
        return redirect(url_for("login_profissional"))
    return render_template("cadastro_profissional.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conexao = conectar_banco()
        usuario = conexao.execute(
            "SELECT * FROM usuarios WHERE username = ?", (username,)
        ).fetchone()
        conexao.close()
        if usuario and check_password_hash(usuario["password"], password):
            session.clear()
            session["usuario_id"] = usuario["id"]
            return redirect(url_for("home"))
        return render_template("login.html", erro="Usuário ou senha inválidos.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/perfil")
@exigir_login
def perfil():
    usuario = usuario_logado()
    conexao = conectar_banco()
    curtidos = conexao.execute("""
        SELECT p.* FROM palestras p
        JOIN curtidas c ON c.palestra_id = p.id
        WHERE c.usuario_id = ? ORDER BY c.criado_em DESC
    """, (session["usuario_id"],)).fetchall()
    salvos = conexao.execute("""
        SELECT p.* FROM palestras p
        JOIN salvos s ON s.palestra_id = p.id
        WHERE s.usuario_id = ? ORDER BY s.criado_em DESC
    """, (session["usuario_id"],)).fetchall()
    conexao.close()
    return render_template("perfil.html", usuario=usuario, curtidos=curtidos, salvos=salvos)


@app.route("/curtir/<int:palestra_id>", methods=["POST"])
@exigir_login
def curtir(palestra_id):
    conexao = conectar_banco()
    existe = conexao.execute(
        "SELECT id FROM curtidas WHERE usuario_id = ? AND palestra_id = ?",
        (session["usuario_id"], palestra_id),
    ).fetchone()
    if existe:
        conexao.execute("DELETE FROM curtidas WHERE id = ?", (existe["id"],))
    else:
        conexao.execute(
            "INSERT OR IGNORE INTO curtidas (usuario_id, palestra_id) VALUES (?, ?)",
            (session["usuario_id"], palestra_id),
        )
    conexao.commit()
    conexao.close()
    return redirect(request.referrer or url_for("home"))


@app.route("/salvar/<int:palestra_id>", methods=["POST"])
@exigir_login
def salvar(palestra_id):
    conexao = conectar_banco()
    existe = conexao.execute(
        "SELECT id FROM salvos WHERE usuario_id = ? AND palestra_id = ?",
        (session["usuario_id"], palestra_id),
    ).fetchone()
    if existe:
        conexao.execute("DELETE FROM salvos WHERE id = ?", (existe["id"],))
    else:
        conexao.execute(
            "INSERT OR IGNORE INTO salvos (usuario_id, palestra_id) VALUES (?, ?)",
            (session["usuario_id"], palestra_id),
        )
    conexao.commit()
    conexao.close()
    return redirect(request.referrer or url_for("home"))


@app.route("/profissional")
def profissional():
    return render_template("profissional.html")


@app.route("/login-profissional", methods=["GET", "POST"])
def login_profissional():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conexao = conectar_banco()
        profissional = conexao.execute(
            "SELECT * FROM profissionais WHERE email = ?", (email,)
        ).fetchone()
        conexao.close()
        if profissional and check_password_hash(profissional["password"], password):
            session.clear()
            session["profissional_id"] = profissional["id"]
            return redirect(url_for("chat_profissional"))
        return render_template("login_profissional.html", erro="E-mail ou senha inválidos.")
    return render_template("login_profissional.html")


@app.route("/admin-login", methods=["GET", "POST"])
@app.route("/login-admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conexao = conectar_banco()
        administrador = conexao.execute(
            "SELECT * FROM administradores WHERE username = ?", (username,)
        ).fetchone()
        conexao.close()
        if administrador and check_password_hash(administrador["password"], password):
            session.clear()
            session["admin_id"] = administrador["id"]
            return redirect(url_for("admin"))
        return render_template("admin_login.html", erro="Usuário ou senha administrativos inválidos.")
    return render_template("admin_login.html")


@app.route("/profissional/logout")
def profissional_logout():
    session.pop("profissional_id", None)
    return redirect(url_for("login_profissional"))


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_id", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
@exigir_admin
def admin():
    conexao=conectar_banco()
    palestras=conexao.execute("SELECT * FROM palestras ORDER BY criado_em DESC").fetchall()
    eventos=conexao.execute("SELECT * FROM eventos_calendario ORDER BY data_evento ASC, id ASC").fetchall()
    notificacoes_admin=conexao.execute("SELECT * FROM notificacoes WHERE usuario_id IS NULL ORDER BY criado_em DESC").fetchall()
    feedbacks=conexao.execute("SELECT f.*,u.username,u.email FROM feedbacks f LEFT JOIN usuarios u ON u.id=f.usuario_id ORDER BY f.criado_em DESC").fetchall()
    conexao.close()
    return render_template("admin.html",palestras=palestras,eventos=eventos,notificacoes_admin=notificacoes_admin,feedbacks=feedbacks)


@app.route("/admin/adicionar", methods=["GET", "POST"])
@exigir_admin
def adicionar_palestra():
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        descricao = request.form.get("descricao", "").strip()
        categoria = request.form.get("categoria", "").strip()
        video_url = request.form.get("video_url", "").strip()
        capa_url = request.form.get("capa_url", "").strip()
        if not titulo or not descricao or not categoria or not video_url:
            return render_template("adicionar_palestra.html", erro="Preencha todos os campos obrigatórios.")
        video_id = pegar_id_youtube(video_url)
        if video_id:
            capa_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        conexao = conectar_banco()
        conexao.execute("""
            INSERT INTO palestras (titulo, descricao, categoria, video_url, capa_url)
            VALUES (?, ?, ?, ?, ?)
        """, (titulo, descricao, categoria, video_url, capa_url))
        conexao.commit()
        conexao.close()
        return redirect(url_for("admin"))
    return render_template("adicionar_palestra.html")


@app.route("/admin/editar/<int:palestra_id>", methods=["GET", "POST"])
@exigir_admin
def editar_palestra(palestra_id):
    conexao = conectar_banco()
    palestra = conexao.execute("SELECT * FROM palestras WHERE id = ?", (palestra_id,)).fetchone()
    if palestra is None:
        conexao.close()
        return "Palestra não encontrada.", 404
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        descricao = request.form.get("descricao", "").strip()
        categoria = request.form.get("categoria", "").strip()
        video_url = request.form.get("video_url", "").strip()
        capa_url = request.form.get("capa_url", "").strip()
        video_id = pegar_id_youtube(video_url)
        if video_id:
            capa_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        conexao.execute("""
            UPDATE palestras SET titulo=?, descricao=?, categoria=?, video_url=?, capa_url=?
            WHERE id=?
        """, (titulo, descricao, categoria, video_url, capa_url, palestra_id))
        conexao.commit()
        conexao.close()
        return redirect(url_for("admin"))
    conexao.close()
    return render_template("editar_palestra.html", palestra=palestra)


@app.route("/admin/excluir/<int:palestra_id>", methods=["POST"])
@exigir_admin
def excluir_palestra(palestra_id):
    conexao = conectar_banco()
    conexao.execute("DELETE FROM curtidas WHERE palestra_id = ?", (palestra_id,))
    conexao.execute("DELETE FROM salvos WHERE palestra_id = ?", (palestra_id,))
    conexao.execute("DELETE FROM palestras WHERE id = ?", (palestra_id,))
    conexao.commit()
    conexao.close()
    return redirect(url_for("admin"))


@app.route("/admin/calendario/adicionar", methods=["POST"])
@exigir_admin
def admin_adicionar_evento():
    titulo=request.form.get("titulo","").strip(); tipo=request.form.get("tipo","Ação").strip(); data_evento=request.form.get("data_evento","").strip(); horario=request.form.get("horario","").strip(); local=request.form.get("local","").strip(); descricao=request.form.get("descricao","").strip()
    try: datetime.strptime(data_evento,"%Y-%m-%d")
    except ValueError: return redirect(url_for("admin")+"#calendario")
    if titulo:
        c=conectar_banco(); c.execute("INSERT INTO eventos_calendario (titulo,tipo,data_evento,horario,local,descricao) VALUES (?,?,?,?,?,?)",(titulo,tipo,data_evento,horario,local,descricao)); c.commit(); c.close()
    return redirect(url_for("admin")+"#calendario")

@app.route("/admin/calendario/editar/<int:evento_id>", methods=["GET","POST"])
@exigir_admin
def admin_editar_evento(evento_id):
    c=conectar_banco(); evento=c.execute("SELECT * FROM eventos_calendario WHERE id=?",(evento_id,)).fetchone()
    if evento is None: c.close(); return "Evento não encontrado.",404
    if request.method=="POST":
        titulo=request.form.get("titulo","").strip(); tipo=request.form.get("tipo","Ação").strip(); data_evento=request.form.get("data_evento","").strip(); horario=request.form.get("horario","").strip(); local=request.form.get("local","").strip(); descricao=request.form.get("descricao","").strip()
        try: datetime.strptime(data_evento,"%Y-%m-%d")
        except ValueError: return render_template("admin_editar_evento.html",evento=evento,erro="Informe uma data válida.")
        if titulo:
            c.execute("UPDATE eventos_calendario SET titulo=?,tipo=?,data_evento=?,horario=?,local=?,descricao=? WHERE id=?",(titulo,tipo,data_evento,horario,local,descricao,evento_id)); c.commit(); c.close(); return redirect(url_for("admin")+"#calendario")
    c.close(); return render_template("admin_editar_evento.html",evento=evento)


@app.route("/admin/calendario/excluir/<int:evento_id>",methods=["POST"])
@exigir_admin
def admin_excluir_evento(evento_id):
    c=conectar_banco(); c.execute("DELETE FROM eventos_calendario WHERE id=?",(evento_id,)); c.commit(); c.close(); return redirect(url_for("admin")+"#calendario")

@app.route("/admin/notificacoes/adicionar",methods=["POST"])
@exigir_admin
def admin_adicionar_notificacao():
    titulo=request.form.get("titulo","").strip(); mensagem=request.form.get("mensagem","").strip()
    if titulo and mensagem:
        c=conectar_banco(); c.execute("INSERT INTO notificacoes(usuario_id,titulo,mensagem) VALUES(NULL,?,?)",(titulo,mensagem)); c.commit(); c.close()
    return redirect(url_for("admin")+"#notificacoes")

@app.route("/admin/notificacoes/editar/<int:notificacao_id>", methods=["GET","POST"])
@exigir_admin
def admin_editar_notificacao(notificacao_id):
    c=conectar_banco(); n=c.execute("SELECT * FROM notificacoes WHERE id=? AND usuario_id IS NULL",(notificacao_id,)).fetchone()
    if n is None: c.close(); return "Notificação não encontrada.",404
    if request.method=="POST":
        titulo=request.form.get("titulo","").strip(); mensagem=request.form.get("mensagem","").strip()
        if titulo and mensagem:
            c.execute("UPDATE notificacoes SET titulo=?,mensagem=? WHERE id=? AND usuario_id IS NULL",(titulo,mensagem,notificacao_id)); c.commit(); c.close(); return redirect(url_for("admin")+"#notificacoes")
    c.close(); return render_template("admin_editar_notificacao.html",notificacao=n)


@app.route("/admin/notificacoes/excluir/<int:notificacao_id>",methods=["POST"])
@exigir_admin
def admin_excluir_notificacao(notificacao_id):
    c=conectar_banco(); c.execute("DELETE FROM notificacoes WHERE id=? AND usuario_id IS NULL",(notificacao_id,)); c.commit(); c.close(); return redirect(url_for("admin")+"#notificacoes")

@app.route("/admin/feedback/excluir/<int:feedback_id>",methods=["POST"])
@exigir_admin
def admin_excluir_feedback(feedback_id):
    c=conectar_banco(); c.execute("DELETE FROM feedbacks WHERE id=?",(feedback_id,)); c.commit(); c.close(); return redirect(url_for("admin")+"#feedbacks")

@app.route("/notificacoes")
@exigir_login
def notificacoes():
    c=conectar_banco(); notificacoes_db=c.execute("SELECT * FROM notificacoes WHERE usuario_id=? OR usuario_id IS NULL ORDER BY criado_em DESC",(session["usuario_id"],)).fetchall(); c.close()
    return render_template("notificacoes.html",notificacoes=notificacoes_db)

@app.route("/calendario")
@exigir_login
def calendario():
    hoje=hoje_brasilia()
    try:
        ano=int(request.args.get("ano",hoje.year)); mes=int(request.args.get("mes",hoje.month)); assert 1<=mes<=12
    except (ValueError,TypeError,AssertionError): ano,mes=hoje.year,hoje.month
    c=conectar_banco(); eventos=c.execute("SELECT * FROM eventos_calendario WHERE substr(data_evento,1,7)=? ORDER BY data_evento,horario,id",(f"{ano:04d}-{mes:02d}",)).fetchall(); c.close()
    eventos_por_dia={}
    for e in eventos: eventos_por_dia.setdefault(int(e["data_evento"].split("-")[2]),[]).append(e)
    first,last=pycalendar.monthrange(ano,mes); semanas=[]; semana=[None]*first
    for d in range(1,last+1):
        semana.append(d)
        if len(semana)==7: semanas.append(semana); semana=[]
    if semana: semana += [None]*(7-len(semana)); semanas.append(semana)
    meses_pt=["","Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
    return render_template("calendario.html",ano=ano,mes=mes,nome_mes=meses_pt[mes],semanas=semanas,eventos_por_dia=eventos_por_dia,hoje=hoje)


@app.route("/chat", methods=["GET", "POST"])
@exigir_login
def chat():
    conexao = conectar_banco()
    profissionais = conexao.execute(
        "SELECT id, nome, especialidade FROM profissionais ORDER BY nome ASC"
    ).fetchall()

    profissional_id = request.form.get("profissional_id", type=int) if request.method == "POST" else request.args.get("profissional_id", type=int)
    mensagem = request.form.get("mensagem", "").strip() if request.method == "POST" else ""
    erro = None

    if profissional_id:
        profissional = conexao.execute(
            "SELECT id, nome, especialidade FROM profissionais WHERE id = ?",
            (profissional_id,),
        ).fetchone()
        if profissional is None:
            profissional_id = None
            erro = "Profissional não encontrado."

    if profissional_id and mensagem:
        conversa = conexao.execute(
            "SELECT id FROM conversas WHERE usuario_id = ? AND profissional_id = ?",
            (session["usuario_id"], profissional_id),
        ).fetchone()
        if conversa is None:
            cursor = conexao.execute(
                "INSERT INTO conversas (usuario_id, profissional_id) VALUES (?, ?)",
                (session["usuario_id"], profissional_id),
            )
            conversa_id = cursor.lastrowid
        else:
            conversa_id = conversa["id"]

        conexao.execute(
            "INSERT INTO mensagens_chat (conversa_id, remetente_tipo, remetente_id, mensagem) VALUES (?, 'usuario', ?, ?)",
            (conversa_id, session["usuario_id"], mensagem),
        )
        conexao.commit()

    conversas = conexao.execute("""
        SELECT c.id, c.profissional_id, p.nome, p.especialidade
        FROM conversas c
        JOIN profissionais p ON p.id = c.profissional_id
        WHERE c.usuario_id = ?
        ORDER BY c.id DESC
    """, (session["usuario_id"],)).fetchall()

    mensagens = []
    profissional_atual = None
    conversa_atual = None
    if profissional_id:
        profissional_atual = conexao.execute(
            "SELECT id, nome, especialidade FROM profissionais WHERE id = ?",
            (profissional_id,),
        ).fetchone()
        if profissional_atual:
            conversa_atual = conexao.execute(
                "SELECT id FROM conversas WHERE usuario_id = ? AND profissional_id = ?",
                (session["usuario_id"], profissional_id),
            ).fetchone()
            if conversa_atual:
                mensagens = conexao.execute("""
                    SELECT m.*,
                           CASE WHEN m.remetente_tipo = 'usuario' THEN u.username ELSE p.nome END AS remetente_nome
                    FROM mensagens_chat m
                    LEFT JOIN usuarios u ON m.remetente_tipo = 'usuario' AND u.id = m.remetente_id
                    LEFT JOIN profissionais p ON m.remetente_tipo = 'profissional' AND p.id = m.remetente_id
                    WHERE m.conversa_id = ?
                    ORDER BY m.criado_em ASC, m.id ASC
                """, (conversa_atual["id"],)).fetchall()

    conexao.close()
    return render_template(
        "chat.html",
        profissionais=profissionais,
        conversas=conversas,
        mensagens=mensagens,
        profissional_atual=profissional_atual,
        profissional_id=profissional_id,
        erro=erro,
    )


@app.route("/chat-profissional", methods=["GET", "POST"])
def chat_profissional():
    profissional_id = session.get("profissional_id")
    if not profissional_id:
        return redirect(url_for("login_profissional"))

    conexao = conectar_banco()
    profissional = conexao.execute(
        "SELECT id, nome, especialidade FROM profissionais WHERE id = ?",
        (profissional_id,),
    ).fetchone()
    if profissional is None:
        session.pop("profissional_id", None)
        conexao.close()
        return redirect(url_for("login_profissional"))

    conversa_id = request.form.get("conversa_id", type=int) if request.method == "POST" else request.args.get("conversa_id", type=int)
    mensagem = request.form.get("mensagem", "").strip() if request.method == "POST" else ""

    if conversa_id:
        conversa = conexao.execute("""
            SELECT c.id, c.usuario_id, u.username
            FROM conversas c
            JOIN usuarios u ON u.id = c.usuario_id
            WHERE c.id = ? AND c.profissional_id = ?
        """, (conversa_id, profissional_id)).fetchone()
        if conversa is None:
            conversa_id = None
        elif mensagem:
            conexao.execute(
                "INSERT INTO mensagens_chat (conversa_id, remetente_tipo, remetente_id, mensagem) VALUES (?, 'profissional', ?, ?)",
                (conversa_id, profissional_id, mensagem),
            )
            conexao.commit()

    conversas = conexao.execute("""
        SELECT c.id, c.usuario_id, u.username, u.email
        FROM conversas c
        JOIN usuarios u ON u.id = c.usuario_id
        WHERE c.profissional_id = ?
        ORDER BY c.id DESC
    """, (profissional_id,)).fetchall()

    conversa_atual = None
    mensagens = []
    if conversa_id:
        conversa_atual = conexao.execute("""
            SELECT c.id, c.usuario_id, u.username, u.email
            FROM conversas c
            JOIN usuarios u ON u.id = c.usuario_id
            WHERE c.id = ? AND c.profissional_id = ?
        """, (conversa_id, profissional_id)).fetchone()
        if conversa_atual:
            mensagens = conexao.execute("""
                SELECT m.*,
                       CASE WHEN m.remetente_tipo = 'usuario' THEN u.username ELSE p.nome END AS remetente_nome
                FROM mensagens_chat m
                LEFT JOIN usuarios u ON m.remetente_tipo = 'usuario' AND u.id = m.remetente_id
                LEFT JOIN profissionais p ON m.remetente_tipo = 'profissional' AND p.id = m.remetente_id
                WHERE m.conversa_id = ?
                ORDER BY m.criado_em ASC, m.id ASC
            """, (conversa_id,)).fetchall()

    conexao.close()
    return render_template(
        "chat_profissional.html",
        profissional=profissional,
        conversas=conversas,
        conversa_atual=conversa_atual,
        mensagens=mensagens,
    )


@app.route("/feedback", methods=["GET","POST"])
@exigir_login
def feedback():
    if request.method=="POST":
        tipo=request.form.get("tipo","").strip(); mensagem=request.form.get("mensagem","").strip()
        if tipo and mensagem:
            c=conectar_banco(); c.execute("INSERT INTO feedbacks(usuario_id,tipo,mensagem) VALUES(?,?,?)",(session["usuario_id"],tipo,mensagem)); c.commit(); c.close()
        return render_template("feedback.html",enviado=True)
    return render_template("feedback.html",enviado=False)


@app.route("/configuracoes")
@exigir_login
def configuracoes():
    return render_template("configuracoes.html", usuario=usuario_logado())


@app.route("/configuracoes/<secao>", methods=["GET","POST"])
@exigir_login
def configuracoes_secao(secao):
    if secao not in ["conta","acessibilidade","privacidade","ajuda","sobre"]: return "Página não encontrada.",404
    c=conectar_banco(); usuario=c.execute("SELECT * FROM usuarios WHERE id=?",(session["usuario_id"],)).fetchone(); mensagem=None
    if secao=="conta" and request.method=="POST":
        username=request.form.get("username","").strip(); email=request.form.get("email","").strip().lower(); birthdate=request.form.get("birthdate","").strip(); foto=request.files.get("foto"); foto_data=None
        if foto and foto.filename:
            raw=foto.read()
            if len(raw)>2*1024*1024: mensagem="A foto deve ter no máximo 2 MB."
            elif foto.mimetype not in {"image/jpeg","image/png","image/webp"}: mensagem="Use uma imagem JPG, PNG ou WEBP."
            else: foto_data=f"data:{foto.mimetype};base64,{base64.b64encode(raw).decode('ascii')}"
        if mensagem is None:
            try:
                if foto_data: c.execute("UPDATE usuarios SET username=?,email=?,birthdate=?,foto_perfil=? WHERE id=?",(username,email,birthdate,foto_data,session["usuario_id"]))
                else: c.execute("UPDATE usuarios SET username=?,email=?,birthdate=? WHERE id=?",(username,email,birthdate,session["usuario_id"]))
                c.commit(); mensagem="Dados atualizados com sucesso."
            except sqlite3.IntegrityError: mensagem="Esse usuário ou e-mail já está sendo utilizado."
    elif secao=="acessibilidade" and request.method=="POST":
        vals={k:request.form.get(k,"normal") for k in ["tamanho_texto","cor","fonte","tema"]}
        if vals["tamanho_texto"] not in {"normal","grande","muito-grande"}: vals["tamanho_texto"]="normal"
        if vals["cor"] not in {"normal","alto-contraste","tons-cinza"}: vals["cor"]="normal"
        if vals["fonte"] not in {"normal","serifada","legivel"}: vals["fonte"]="normal"
        if vals["tema"] not in {"claro","escuro"}: vals["tema"]="claro"
        c.execute("INSERT INTO preferencias_acessibilidade(usuario_id,tamanho_texto,cor,fonte,tema) VALUES(?,?,?,?,?) ON CONFLICT(usuario_id) DO UPDATE SET tamanho_texto=excluded.tamanho_texto,cor=excluded.cor,fonte=excluded.fonte,tema=excluded.tema",(session["usuario_id"],vals["tamanho_texto"],vals["cor"],vals["fonte"],vals["tema"])); c.commit(); mensagem="Preferências de acessibilidade salvas."
    elif secao=="idioma" and request.method=="POST":
        idioma=request.form.get("idioma","pt-BR")
        idiomas_validos={"pt-BR","en","es","fr","it","de","ja","ko","zh-CN"}
        if idioma not in idiomas_validos: idioma="pt-BR"
        c.execute("INSERT INTO preferencias_acessibilidade(usuario_id,idioma) VALUES(?,?) ON CONFLICT(usuario_id) DO UPDATE SET idioma=excluded.idioma",(session["usuario_id"],idioma)); c.commit(); mensagem="Idioma salvo com sucesso."
    elif secao=="privacidade" and request.method=="POST":
        atual=request.form.get("senha_atual",""); nova=request.form.get("nova_senha",""); confirmar=request.form.get("confirmar_senha","")
        if not check_password_hash(usuario["password"],atual): mensagem="A senha atual está incorreta."
        elif nova!=confirmar: mensagem="As novas senhas não coincidem."
        elif len(nova)<6: mensagem="A nova senha deve ter pelo menos 6 caracteres."
        else: c.execute("UPDATE usuarios SET password=? WHERE id=?",(generate_password_hash(nova),session["usuario_id"])); c.commit(); mensagem="Senha alterada com sucesso."
    usuario=c.execute("SELECT * FROM usuarios WHERE id=?",(session["usuario_id"],)).fetchone(); preferencias=carregar_preferencias(session["usuario_id"]); c.close()
    return render_template("configuracao_secao.html",secao=secao,usuario=usuario,mensagem=mensagem,preferencias=preferencias)


criar_banco()

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
