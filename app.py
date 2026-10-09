import os
import tempfile
import json
import uuid
from flask import Flask, render_template, request, jsonify
from core.audio import analisar_som
from supabase import create_client, Client

app = Flask(__name__)

# === CONFIGURAÇÃO DO SUPABASE ===
# Usamos os.environ.get para proteger as chaves no GitHub
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Só conecta se as chaves existirem (evita erro local se esquecer de configurar)
if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

# Criar pasta temporária para segurar os áudios até o feedback
PASTA_TEMP = "temp_audio"
os.makedirs(PASTA_TEMP, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analisar-audio', methods=['POST'])
def receber_audio():
    if 'audio' not in request.files:
        return jsonify({"erro": "Nenhum áudio enviado"}), 400
        
    arquivo_audio = request.files['audio']
    extensao = os.path.splitext(arquivo_audio.filename)[1] or ".webm"
    
    # Gera um ID único para este áudio
    audio_id = str(uuid.uuid4())
    caminho_local = os.path.join(PASTA_TEMP, f"{audio_id}{extensao}")
    
    # Salva o arquivo localmente
    arquivo_audio.save(caminho_local)
    
    resultado = analisar_som(caminho_local)
    
    if resultado.get("status") == "sucesso":
        resultado["problema_identificado"] = "partida"
        resultado["audio_id"] = f"{audio_id}{extensao}" # Envia o ID para o Front-end
    
    return jsonify(resultado)

@app.route('/perguntas/<categoria_problema>', methods=['GET'])
def obter_perguntas(categoria_problema):
    diretorio_base = os.path.dirname(os.path.abspath(__file__))
    caminho_arquivo = os.path.join(diretorio_base, 'data', 'perguntas', f'{categoria_problema}.json')
    
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        return jsonify({"status": "sucesso", "dados": dados})
    except FileNotFoundError:
        return jsonify({"status": "erro", "mensagem": "Questionário não encontrado."}), 404

@app.route('/diagnostico', methods=['POST'])
def calcular_diagnostico():
    dados = request.json
    respostas = dados.get('respostas', {})
    
    pontos = {"Bateria": 10, "Motor de Partida": 5, "Alternador": 2}
    
    if respostas.get('p1') == 'Sim': pontos["Bateria"] += 50
    elif respostas.get('p1') == 'Não': pontos["Motor de Partida"] += 20
        
    if respostas.get('p2') == 'Não': pontos["Bateria"] += 30
        
    if respostas.get('p3') == "Um 'clique' único e seco": pontos["Motor de Partida"] += 60
    elif respostas.get('p3') == "Vários estalos rápidos (tec-tec-tec)": pontos["Bateria"] += 50
    elif respostas.get('p3') == "O motor gira, mas muito pesado/lento": 
        pontos["Bateria"] += 30
        pontos["Motor de Partida"] += 30

    total_pontos = sum(pontos.values())
    resultados = []
    
    for defeito, valor in pontos.items():
        probabilidade = int((valor / total_pontos) * 100)
        if probabilidade > 0:
            if defeito == "Bateria": desc = "Baseado na queda de energia e no som relatado, a causa mais provável é a bateria."
            elif defeito == "Motor de Partida": desc = "O som indica que o motor de arranque não consegue atracar e girar o volante do motor."
            else: desc = "O sistema elétrico (como o alternador) pode não estar a recarregar corretamente a bateria."
                
            resultados.append({"defeito": defeito, "probabilidade": probabilidade, "descricao": desc})
            
    resultados = sorted(resultados, key=lambda x: x['probabilidade'], reverse=True)
    return jsonify({"status": "sucesso", "diagnostico": resultados})

# NOVA ROTA: O Cérebro da Retroalimentação (Agora à prova de testes locais!)
@app.route('/feedback', methods=['POST'])
def receber_feedback():
    dados = request.json
    audio_id = dados.get('audio_id')
    diagnostico_app = dados.get('diagnostico_app')
    feedback_usuario = dados.get('feedback_usuario')
    defeito_real = dados.get('defeito_real')
    
    try:
        # 1. Faz upload do áudio apenas se ele existir e NÃO for o teste falso
        if audio_id and audio_id != "audio-falso-para-testes.webm":
            caminho_local = os.path.join(PASTA_TEMP, audio_id)
            if os.path.exists(caminho_local):
                with open(caminho_local, 'rb') as f:
                    supabase.storage.from_("audios_inspecao").upload(audio_id, f)
                os.remove(caminho_local) # Limpa o áudio local
            else:
                print(f"Aviso: Áudio real {audio_id} não encontrado na pasta temporária.")
        else:
            print("Teste local detetado! Gravando apenas os textos no Supabase.")

        # 2. Regista os dados na tabela 'feedbacks' (Isto vai acontecer sempre!)
        supabase.table("feedbacks").insert({
            "audio_nome": audio_id,
            "diagnostico_app": diagnostico_app,
            "feedback_usuario": feedback_usuario,
            "defeito_real": defeito_real
        }).execute()
        
        return jsonify({"status": "sucesso"})
    except Exception as e:
        print(f"Erro no Supabase: {e}")
        return jsonify({"status": "erro", "mensagem": str(e)}), 500
if __name__ == '__main__':
    app.run(debug=True, port=5000)