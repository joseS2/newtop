from flask import Flask, render_template_string, request, jsonify
import pyminizip
import requests
import secrets
import string
import os
from datetime import datetime, timedelta

app = Flask(__name__)
# Aumentando o limite para 500MB (O Render Free aguenta bem até uns 100-200MB)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024 

# --- CONFIGURAÇÕES ---
# ⚠️ MUDE ESTA SENHA ANTES DE SUBIR NO GITHUB!
SENHA_DO_SITE = "admin123" 
LOG_FILE = "historico.txt"

def gerar_senha_100_chars():
    chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-="
    return ''.join(secrets.choice(chars) for _ in range(100))

def salvar_no_log(url, senha, arquivo, expira_em_horas):
    agora = datetime.now()
    data_expira = agora + timedelta(hours=expira_em_horas)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        # Formato: DATA_EXPIRACAO|NOME|URL|SENHA
        f.write(f"{data_expira.strftime('%Y-%m-%d %H:%M:%S')}|{arquivo}|{url}|{senha}\n")

def limpar_logs_expirados():
    if not os.path.exists(LOG_FILE): return
    agora = datetime.now()
    linhas_validas = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for linha in f:
            try:
                data_str = linha.split('|')[0]
                data_expira = datetime.strptime(data_str, '%Y-%m-%d %H:%M:%S')
                if data_expira > agora:
                    linhas_validas.append(linha)
            except: continue
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.writelines(linhas_validas)

# --- FRONTEND (HTML/CSS/JS) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Neon Vault | Litterbox Host</title>
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        :root { --primary: #8a2be2; --accent: #00f2ff; --bg: #0a0a0c; }
        body { background: var(--bg); color: #fff; font-family: 'Segoe UI', sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .glass-card { background: rgba(255,255,255,0.05); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.1); border-radius: 24px; padding: 40px; width: 420px; box-shadow: 0 20px 50px rgba(0,0,0,0.8); }
        h2 { text-align: center; background: linear-gradient(to right, var(--primary), var(--accent)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 25px; }
        input, select, button { width: 100%; padding: 14px; margin: 10px 0; border-radius: 12px; border: 1px solid #333; background: rgba(0,0,0,0.4); color: #fff; box-sizing: border-box; outline: none; }
        button { background: linear-gradient(135deg, var(--primary), #4b0082); border: none; font-weight: bold; cursor: pointer; transition: 0.3s; display: flex; align-items: center; justify-content: center; gap: 10px; }
        button:hover { transform: scale(1.02); box-shadow: 0 0 20px rgba(138, 43, 226, 0.5); }
        .result-container { margin-top: 20px; padding: 15px; background: rgba(0,255,150,0.1); border: 1px solid #00ff96; border-radius: 12px; display: none; }
        .password-wrapper { background: #000; padding: 10px; border-radius: 8px; display: flex; align-items: center; justify-content: space-between; margin-top: 8px; border: 1px solid #222; }
        .password-text { font-family: monospace; font-size: 10px; color: #00ff96; overflow: hidden; filter: blur(6px); transition: 0.4s; }
        .password-text.visible { filter: blur(0); }
        .toggle-btn { background: none; border: none; color: #888; cursor: pointer; width: auto; padding: 0; margin-left: 10px; }
        .info-tag { font-size: 10px; color: #ff4757; text-align: center; margin-top: 10px; text-transform: uppercase; letter-spacing: 1px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="glass-card">
        <div id="login-section">
            <h2>🔒 Vault Login</h2>
            <input type="password" id="sitePass" placeholder="Senha do Sistema">
            <button onclick="login()">Desbloquear</button>
        </div>

        <div id="upload-section" style="display:none">
            <h2>Cripto Host</h2>
            <input type="file" id="fileInput">
            <input type="password" id="zipPass" placeholder="Senha ZIP (Vazio = 100 chars)">
            <select id="expireTime">
                <option value="1h">Expira em 1 Hora</option>
                <option value="24h" selected>Expira em 24 Horas</option>
                <option value="72h">Expira em 72 Horas</option>
            </select>
            <button id="mainBtn" onclick="enviar()"><i data-lucide="shield-check"></i> Enviar p/ Nuvem</button>
            <div class="info-tag">Auto-limpeza de logs ativada</div>
            <div id="status" style="text-align:center; font-size:12px; margin-top:10px; color: var(--accent)"></div>
            
            <div id="resultBox" class="result-container">
                <span style="font-size:11px; color:#fff">URL LITTERBOX:</span><br>
                <a id="resLink" href="#" target="_blank" style="color:var(--accent); font-size:13px; word-break:break-all"></a>
                <div class="password-wrapper">
                    <div id="resPass" class="password-text"></div>
                    <button class="toggle-btn" onclick="togglePassword()"><i id="eyeIcon" data-lucide="eye"></i></button>
                </div>
            </div>
        </div>
    </div>

    <script>
        lucide.createIcons();
        let mestre = "";
        function login() { 
            mestre = document.getElementById('sitePass').value; 
            document.getElementById('login-section').style.display='none'; 
            document.getElementById('upload-section').style.display='block'; 
        }
        function togglePassword() {
            const p = document.getElementById('resPass');
            const icon = document.getElementById('eyeIcon');
            p.classList.toggle('visible');
            icon.setAttribute('data-lucide', p.classList.contains('visible') ? 'eye-off' : 'eye');
            lucide.createIcons();
        }
        async function enviar() {
            const file = document.getElementById('fileInput').files[0];
            if(!file) return alert("Selecione um arquivo");
            const btn = document.getElementById('mainBtn');
            btn.disabled = true;
            document.getElementById('status').innerText = "⏳ Criptografando e enviando...";
            
            const formData = new FormData();
            formData.append('file', file);
            formData.append('site_pass', mestre);
            formData.append('zip_pass', document.getElementById('zipPass').value);
            formData.append('time', document.getElementById('expireTime').value);

            try {
                const r = await fetch('/upload', { method:'POST', body:formData });
                const d = await r.json();
                if(d.success) {
                    document.getElementById('resLink').href = d.url;
                    document.getElementById('resLink').innerText = d.url;
                    document.getElementById('resPass').innerText = d.zip_password;
                    document.getElementById('resultBox').style.display = 'block';
                    document.getElementById('status').innerText = "✅ Concluído!";
                } else { alert(d.error); document.getElementById('status').innerText = ""; }
            } catch(e) { alert("Erro de conexão"); }
            finally { btn.disabled = false; }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    limpar_logs_expirados()
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload():
    if request.form.get('site_pass') != SENHA_DO_SITE:
        return jsonify({"success": False, "error": "Senha inválida!"})
    
    file = request.files['file']
    zip_pass = request.form.get('zip_pass') or gerar_senha_100_chars()
    time_str = request.form.get('time')
    horas = int(time_str.replace('h', ''))
    
    temp_raw, temp_zip = file.filename, file.filename + ".zip"

    try:
        file.save(temp_raw)
        pyminizip.compress(temp_raw, None, temp_zip, zip_pass, 0)
        
        with open(temp_zip, 'rb') as f:
            r = requests.post("https://litterbox.catbox.moe/resources/internals/api.php", 
                            data={"reqtype": "fileupload", "time": time_str}, 
                            files={"fileToUpload": f})
        
        if "https" in r.text:
            salvar_no_log(r.text, zip_pass, temp_raw, horas)
            return jsonify({"success": True, "url": r.text, "zip_password": zip_pass})
        return jsonify({"success": False, "error": r.text})
    except Exception as e: return jsonify({"success": False, "error": str(e)})
    finally:
        for f in [temp_raw, temp_zip]:
            if os.path.exists(f): os.remove(f)

if __name__ == '__main__':
    # Porta padrão para plataformas de nuvem
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
