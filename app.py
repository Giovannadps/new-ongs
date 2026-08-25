from flask import Flask, render_template, request, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "newongs-chave-secreta"
DATABASE = "newongs.db"

# =========================================================
# CONFIGURAÇÕES
# =========================================================

@app.route("/configuracoes")
def configuracoes():
    return render_template("configuracoes.html")


@app.route("/configuracoes/<secao>", methods=["GET", "POST"])
def configuracoes_secao(secao):

    secoes_validas = [
        "conta",
        "acessibilidade",
        "privacidade",
        "ajuda",
        "sobre"
    ]

    if secao not in secoes_validas:
        return "Página não encontrada.", 404

    conexao = conectar_banco()

    usuario = conexao.execute("""
        SELECT *
        FROM usuarios
        ORDER BY id DESC
        LIMIT 1
    """).fetchone()

    # -----------------------------------------
    # ALTERAÇÃO DE DADOS DA CONTA
    # -----------------------------------------

    if secao == "conta" and request.method == "POST":

        username = request.form["username"].strip()
        email = request.form["email"].strip()
        birthdate = request.form["birthdate"].strip()

        try:

            conexao.execute("""
                UPDATE usuarios
                SET username = ?,
                    email = ?,
                    birthdate = ?
                WHERE id = ?
            """, (
                username,
                email,
                birthdate,
                usuario["id"]
            ))

            conexao.commit()

            usuario = conexao.execute("""
                SELECT *
                FROM usuarios
                WHERE id = ?
            """, (
                usuario["id"],
            )).fetchone()

            mensagem = "Dados atualizados com sucesso."

        except sqlite3.IntegrityError:

            mensagem = "Esse usuário ou e-mail já está sendo utilizado."

        conexao.close()

        return render_template(
            "configuracao_secao.html",
            secao=secao,
            usuario=usuario,
            mensagem=mensagem
        )

    # -----------------------------------------
    # ALTERAÇÃO DE SENHA
    # -----------------------------------------

    if secao == "privacidade" and request.method == "POST":

        senha_atual = request.form["senha_atual"]
        nova_senha = request.form["nova_senha"]
        confirmar_senha = request.form["confirmar_senha"]

        if not check_password_hash(
            usuario["password"],
            senha_atual
        ):

            mensagem = "A senha atual está incorreta."

        elif nova_senha != confirmar_senha:

            mensagem = "As novas senhas não coincidem."

        elif len(nova_senha) < 6:

            mensagem = "A nova senha deve ter pelo menos 6 caracteres."

        else:

            nova_senha_protegida = generate_password_hash(
                nova_senha
            )

            conexao.execute("""
                UPDATE usuarios
                SET password = ?
                WHERE id = ?
            """, (
                nova_senha_protegida,
                usuario["id"]
            ))

            conexao.commit()

            mensagem = "Senha alterada com sucesso."

        conexao.close()

        return render_template(
            "configuracao_secao.html",
            secao=secao,
            usuario=usuario,
            mensagem=mensagem
        )

    conexao.close()

    return render_template(
        "configuracao_secao.html",
        secao=secao,
        usuario=usuario,
        mensagem=None
    )

# =========================================================
# BANCO DE DADOS
# =========================================================

def conectar_banco():
    conexao = sqlite3.connect(DATABASE)
    conexao.row_factory = sqlite3.Row
    return conexao


def criar_banco():

    conexao = conectar_banco()

    # -------------------------
    # Usuários
    # -------------------------

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            birthdate TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # -------------------------
    # Profissionais
    # -------------------------

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

    # -------------------------
    # Administradores
    # -------------------------

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS administradores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    senha_admin = generate_password_hash("NewOngsAdmin123")

    conexao.execute("""
        INSERT OR IGNORE INTO administradores
        (username, password)
        VALUES (?, ?)
    """, (
        "admin",
        senha_admin
    ))

    # -------------------------
    # Palestras
    # -------------------------

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

    # -------------------------
    # Sugestões e Feedback
    # -------------------------

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conexao.commit()
    conexao.close()


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================

def pegar_id_youtube(url):

    if "v=" in url:
        return url.split("v=")[1].split("&")[0]

    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]

    return None


# =========================================================
# PÁGINA INICIAL
# =========================================================

@app.route("/")
def inicio():
    return render_template("index.html")


# =========================================================
# HOME
# =========================================================

@app.route("/home")
def home():

    conexao = conectar_banco()

    palestras = conexao.execute("""
        SELECT *
        FROM palestras
        ORDER BY criado_em DESC
    """).fetchall()

    conexao.close()

    return render_template(
        "home.html",
        palestras=palestras
    )


# =========================================================
# PESQUISA
# =========================================================

@app.route("/pesquisa")
def pesquisa():

    termo = request.args.get("q", "").strip()

    conexao = conectar_banco()

    if termo:

        palestras = conexao.execute("""
            SELECT *
            FROM palestras
            WHERE titulo LIKE ?
               OR descricao LIKE ?
               OR categoria LIKE ?
            ORDER BY criado_em DESC
        """, (
            f"%{termo}%",
            f"%{termo}%",
            f"%{termo}%"
        )).fetchall()

    else:

        palestras = conexao.execute("""
            SELECT *
            FROM palestras
            ORDER BY criado_em DESC
        """).fetchall()

    conexao.close()

    return render_template(
        "pesquisa.html",
        palestras=palestras,
        termo=termo
    )


# =========================================================
# ASSISTIR PALESTRA
# =========================================================

@app.route("/palestra/<int:palestra_id>")
def assistir_palestra(palestra_id):

    conexao = conectar_banco()

    palestra = conexao.execute(
        "SELECT * FROM palestras WHERE id = ?",
        (palestra_id,)
    ).fetchone()

    conexao.close()

    if palestra is None:
        return "Palestra não encontrada."

    video_url = palestra["video_url"]

    id_youtube = pegar_id_youtube(video_url)

    if id_youtube:
        video_url = f"https://www.youtube.com/embed/{id_youtube}"

    palestra = dict(palestra)

    palestra["video_url"] = video_url

    return render_template(
        "palestra.html",
        palestra=palestra
    )


# =========================================================
# CADASTRO DE USUÁRIO
# =========================================================

@app.route("/cadastro")
def cadastro():
    return render_template("cadastro.html")

@app.route("/cadastro-usuario", methods=["GET", "POST"])
def cadastro_usuario():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        birthdate = request.form["birthdate"]
        password = request.form["password"]
        confirm_password = request.form["confirm-password"]

        if password != confirm_password:
            return "As senhas não coincidem."

        senha_protegida = generate_password_hash(password)

        conexao = conectar_banco()

        try:

            conexao.execute("""
                INSERT INTO usuarios
                (username, email, birthdate, password)
                VALUES (?, ?, ?, ?)
            """, (
                username,
                email,
                birthdate,
                senha_protegida
            ))

            conexao.commit()

            usuario = conexao.execute(
                "SELECT id FROM usuarios WHERE username = ?",
                (username,)
            ).fetchone()

            session["usuario_id"] = usuario["id"]

        except sqlite3.IntegrityError:

            conexao.close()

            return "Esse nome de usuário ou e-mail já está cadastrado."

        conexao.close()

        return redirect("/home")

    return render_template("cadastro_usuario.html")


@app.route("/cadastro-profissional", methods=["GET", "POST"])
def cadastro_profissional():

    if request.method == "POST":
    

        nome = request.form["nome"]
        email = request.form["email"]
        especialidade = request.form["especialidade"]
        registro_profissional = request.form["registro_profissional"]
        password = request.form["password"]
        confirm_password = request.form["confirm-password"]

        if password != confirm_password:
            return "As senhas não coincidem."

        senha_protegida = generate_password_hash(password)

        conexao = conectar_banco()

        conexao.execute("""
            INSERT INTO profissionais
            (nome, email, especialidade, registro_profissional, password)
            VALUES (?, ?, ?, ?, ?)
        """, (
            nome,
            email,
            especialidade,
            registro_profissional,
            senha_protegida
        ))

        conexao.commit()
        conexao.close()

        return "Conta profissional criada com sucesso!"

    return render_template("cadastro_profissional.html")


# =========================================================
# LOGIN DO USUÁRIO
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conexao = conectar_banco()

        usuario = conexao.execute(
            "SELECT * FROM usuarios WHERE username=?",
            (username,)
        ).fetchone()

        conexao.close()

        if usuario and check_password_hash(
            usuario["password"],
            password
        ):
            return redirect("/home")

        return "Usuário ou senha inválidos."

    return render_template("login.html")


# =========================================================
# PERFIL
# =========================================================

@app.route("/perfil")
def perfil():

    conexao = conectar_banco()

    usuario = conexao.execute("""
        SELECT *
        FROM usuarios
        ORDER BY id DESC
        LIMIT 1
    """).fetchone()

    conexao.close()

    if usuario is None:
        return "Nenhum usuário encontrado."

    return render_template(
        "perfil.html",
        usuario=usuario
    )


# =========================================================
# ÁREA PROFISSIONAL
# =========================================================

@app.route("/profissional")
def profissional():
    return render_template("profissional.html")


# =========================================================
# LOGIN DO PROFISSIONAL
# =========================================================

@app.route("/login-profissional", methods=["GET", "POST"])
def login_profissional():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conexao = conectar_banco()

        profissional = conexao.execute(
            "SELECT * FROM profissionais WHERE email=?",
            (email,)
        ).fetchone()

        conexao.close()

        if profissional and check_password_hash(
            profissional["password"],
            password
        ):
            return "Login profissional realizado com sucesso."

        return "E-mail ou senha inválidos."

    return render_template("login_profissional.html")


# =========================================================
# LOGIN ADMINISTRATIVO
# =========================================================

@app.route(
    "/admin-login",
    methods=["GET", "POST"]
)
@app.route(
    "/login-admin",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conexao = conectar_banco()

        administrador = conexao.execute(
            """
            SELECT *
            FROM administradores
            WHERE username=?
            """,
            (username,)
        ).fetchone()

        conexao.close()

        if administrador and check_password_hash(
            administrador["password"],
            password
        ):
            return redirect("/admin")

        return "Usuário ou senha administrativos inválidos."

    return render_template("admin_login.html")


# =========================================================
# ÁREA ADMINISTRATIVA
# =========================================================

@app.route("/admin")
def admin():

    conexao = conectar_banco()

    palestras = conexao.execute("""
        SELECT *
        FROM palestras
        ORDER BY criado_em DESC
    """).fetchall()

    conexao.close()

    return render_template(
        "admin.html",
        palestras=palestras
    )


# =========================================================
# ADICIONAR PALESTRA
# =========================================================

@app.route(
    "/admin/adicionar",
    methods=["GET", "POST"]
)
def adicionar_palestra():

    if request.method == "POST":

        titulo = request.form["titulo"]
        descricao = request.form["descricao"]
        categoria = request.form["categoria"]
        video_url = request.form["video_url"]
        capa_url = request.form["capa_url"]

        id_youtube = pegar_id_youtube(video_url)

        if id_youtube:
            capa_url = (
                f"https://img.youtube.com/vi/"
                f"{id_youtube}/hqdefault.jpg"
            )

        conexao = conectar_banco()

        conexao.execute("""
            INSERT INTO palestras
            (titulo, descricao, categoria, video_url, capa_url)
            VALUES (?, ?, ?, ?, ?)
        """, (
            titulo,
            descricao,
            categoria,
            video_url,
            capa_url
        ))

        conexao.commit()
        conexao.close()

        return redirect("/admin")

    return render_template(
        "adicionar_palestra.html"
    )


# =========================================================
# NOTIFICAÇÕES
# =========================================================

@app.route("/notificacoes")
def notificacoes():
    return render_template("notificacoes.html")


# =========================================================
# CALENDÁRIO
# =========================================================

@app.route("/calendario")
def calendario():
    return render_template("calendario.html")


# =========================================================
# CHAT
# =========================================================

@app.route("/chat")
def chat():
    return render_template("chat.html")


# =========================================================
# SUGESTÕES E FEEDBACK
# =========================================================

@app.route("/feedback", methods=["GET", "POST"])
def feedback():

    if request.method == "POST":

        tipo = request.form["tipo"]
        mensagem = request.form["mensagem"]

        conexao = conectar_banco()

        conexao.execute("""
            INSERT INTO feedbacks
            (tipo, mensagem)
            VALUES (?, ?)
        """, (
            tipo,
            mensagem
        ))

        conexao.commit()
        conexao.close()

        return render_template(
            "feedback.html",
            enviado=True
        )

    return render_template(
        "feedback.html",
        enviado=False
    )


# =========================================================
# INICIALIZAÇÃO
# =========================================================

criar_banco()


if __name__ == "__main__":
    app.run(
        debug=True,
        use_reloader=False
    )


    