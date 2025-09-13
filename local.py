from flask import Flask, request, render_template_string, redirect, url_for
import subprocess
import os
import random
num=""
for n in range(10):
   numbers=random.randrange(99999999)
   num=num+hex(numbers)
num1="/"+num
print(num)

app = Flask(__name__)

# Carregar comandos do ficheiro progman.ini
COMMANDS = []
INI_FILE = "progman.ini"

if os.path.exists(INI_FILE):
    with open(INI_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:  # ignora linhas vazias
                COMMANDS.append(line)
else:
    COMMANDS = ["echo Ficheiro progman.ini não encontrado"]

# HTML da página inicial (lista de botões)
HTML_MENU = """
<!doctype html>
<html>
<head>
    <title>Shell Local</title>
</head>
<body style="background-color: yellow; color: black; font-family: monospace;">
    <h2>Menu de Comandos</h2>
    <form method="POST" action="/run">
        {% for cmd in commands %}
            <button type="submit" name="cmd" value="{{ cmd }}" style="display:block; margin:5px; padding:10px;">
                {{ cmd }}
            </button>
        {% endfor %}
    </form>
</body>
</html>
"""
HTML_MENU=HTML_MENU.replace("/run",num1)
# HTML do resultado
HTML_RESULT = """
<!doctype html>
<html>
<head>
    <title>Resultado</title>
</head>
<body style="background-color: yellow; color: black; font-family: monospace;">
    <h2>Resultado de "{{ cmd }}"</h2>
    <pre>{{ output }}</pre>
    <a href="/">Voltar</a>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_MENU, commands=COMMANDS)

@app.route(num1, methods=["POST"])
def run_command():
    # Verificar se vem de localhost (IPv4 ou IPv6)
    if request.remote_addr not in ["127.0.0.1", "::1"]:
        return "Acesso negado: apenas localhost pode executar comandos.", 403

    cmd = request.form.get("cmd", "")
    if not cmd:
        return redirect(url_for("index"))

    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError as e:
        output = f"Erro ao executar o comando:\n{e.output}"

    return render_template_string(HTML_RESULT, cmd=cmd, output=output)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

