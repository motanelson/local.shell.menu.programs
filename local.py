# secure_shell.py
from flask import Flask, request, render_template_string, redirect, url_for, session, make_response
import subprocess
import os
import random
import json
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

# ---------- Config / caminhos ----------
APP_HOST = "127.0.0.1"
APP_PORT = 5000
CRED_FILE = "creds.json"      # contém {"user": "...", "pw_hash": "..."}
SECRET_FILE = "secret.key"    # para persistir a secret_key entre reinícios

# ---------- Gera / carrega secret_key para sessões persistentes ----------
def load_or_create_secret():
    if os.path.exists(SECRET_FILE):
        with open(SECRET_FILE, "rb") as f:
            return f.read()
    else:
        key = secrets.token_bytes(32)
        with open(SECRET_FILE, "wb") as f:
            f.write(key)
        return key

# ---------- Gera rota aleatória (igual ao seu original) ----------
num = ""
for n in range(10):
   numbers = random.randrange(99999999)
   num = num + hex(numbers)
num1 = "/" + num
print("Rota aleatória para /run:", num1)

# ---------- Flask app ----------
app = Flask(__name__)
app.secret_key = load_or_create_secret()

# ---------- Carrega comandos do progman.ini (como no seu original) ----------
COMMANDS = []
INI_FILE = "progman.ini"
if os.path.exists(INI_FILE):
    with open(INI_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                COMMANDS.append(line)
else:
    COMMANDS = ["echo Ficheiro progman.ini não encontrado"]

# ---------- HTML ----------
HTML_LOGIN = """
<!doctype html>
<html>
<head><title>Login</title></head>
<body style="background-color: yellow; color: black; font-family: monospace;">
  <h2>Login inicial</h2>
  <form method="POST" action="/login">
    <label>Utilizador: <input name="username" required></label><br><br>
    <label>Password: <input name="password" type="password" required></label><br><br>
    <button type="submit">Entrar / Registar</button>
  </form>
  <p>Nota: na 1ª vez este formulário regista as credenciais (guarda apenas um hash seguro).</p>
</body>
</html>
"""

HTML_MENU = """
<!doctype html>
<html>
<head>
    <title>Shell Local</title>
</head>
<body style="background-color: yellow; text-align: center; color: black; font-family: monospace;margin: 0 auto">
    <h2>Menu de Comandos</h2>
    <form method="POST" action="{{ run_path }}">
        {% for cmd in commands %}
            <button type="submit" name="cmd" value="{{ cmd }}" style="display:block; padding:10px; margin:8px auto;">
                {{ cmd }}
            </button>
        {% endfor %}
    </form>
</body>
</html>
"""

HTML_RESULT = """
<!doctype html>
<html>
<head><title>Resultado</title></head>
<body style="background-color: yellow; color: black; font-family: monospace;">
  <h2>Resultado de "{{ cmd }}"</h2>
  <pre>{{ output }}</pre>
  <a href="/">Voltar</a>
</body>
</html>
"""

# ---------- Helpers credenciais ----------
def creds_exist():
    return os.path.exists(CRED_FILE)

def load_creds():
    with open(CRED_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_creds(username, pw_hash):
    with open(CRED_FILE, "w", encoding="utf-8") as f:
        json.dump({"user": username, "pw_hash": pw_hash}, f)

def is_localhost():
    return request.remote_addr in ("127.0.0.1", "::1")

def require_login_redirect():
    # Se não existem credenciais, força login (primeira vez)
    if not creds_exist():
        return redirect(url_for("login"))
    # Se existem credenciais, verifica sessão
    if "user" not in session:
        return redirect(url_for("login"))
    # Verifica que a sessão bate com o user guardado
    stored = load_creds()
    if session.get("user") != stored["user"]:
        session.clear()
        return redirect(url_for("login"))
    return None

# ---------- Rotas ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    # só localhost pode registar / login para maior segurança
    if not is_localhost():
        return "Acesso negado: apenas localhost pode aceder.", 403

    if request.method == "GET":
        # Se credenciais já existem e sessão válida -> redireciona para index
        if creds_exist() and "user" in session:
            return redirect(url_for("index"))
        return render_template_string(HTML_LOGIN)

    # POST: tentativa de login / registo inicial
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if not username or not password:
        return "Utilizador ou password em falta", 400

    if not creds_exist():
        # 1ª vez: regista (guarda apenas hash)
        pw_hash = generate_password_hash(password)
        save_creds(username, pw_hash)
        session["user"] = username
        # redireciona para index (agora disponível)
        return redirect(url_for("index"))
    else:
        # Verifica login vs hash guardado
        stored = load_creds()
        if username != stored["user"] or not check_password_hash(stored["pw_hash"], password):
            return "Credenciais inválidas", 403
        # sucesso: cria sessão
        session["user"] = username
        return redirect(url_for("index"))

@app.route("/", methods=["GET"])
def index():
    # Só localhost pode usar o servidor de execução
    if not is_localhost():
        return "Acesso negado: apenas localhost pode executar comandos.", 403

    # Se não existe credencial, força login (1ª vez)
    if not creds_exist():
        return redirect(url_for("login"))

    # Se existe credencial, exige sessão válida
    if "user" not in session:
        return redirect(url_for("login"))

    # Tudo ok: mostra menu
    return render_template_string(HTML_MENU, commands=COMMANDS, run_path=num1)

@app.route(num1, methods=["POST"])
def run_command():
    # restringe a localhost
    if not is_localhost():
        return "Acesso negado: apenas localhost pode executar comandos.", 403

    # exige que exista credencial guardada
    if not creds_exist():
        return redirect(url_for("login"))

    # exige sessão válida
    if "user" not in session:
        return redirect(url_for("login"))

    # confirma que sessão corresponde às credenciais guardadas
    stored = load_creds()
    if session.get("user") != stored["user"]:
        session.clear()
        return redirect(url_for("login"))

    # obtém comando e executa
    cmd = request.form.get("cmd", "")
    if not cmd:
        return redirect(url_for("index"))
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True, universal_newlines=True)
    except subprocess.CalledProcessError as e:
        output = f"Erro ao executar o comando:\n{e.output}"
    return render_template_string(HTML_RESULT, cmd=cmd, output=output)

@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------- Execução ----------
if __name__ == "__main__":
    # aviso: debug mode activado apenas para desenvolvimento local
    app.run(host=APP_HOST, port=APP_PORT, debug=True)
