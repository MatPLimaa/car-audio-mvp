import librosa
import numpy as np

def analisar_som(caminho_arquivo):
    """
    Lê o áudio e (no futuro) usará Machine Learning.
    Por enquanto, faz uma leitura básica para provar que o arquivo chegou inteiro.
    """
    try:
        # Tenta carregar o áudio (duração máxima de 5 segundos para ser rápido)
        y, sr = librosa.load(caminho_arquivo, sr=22050, duration=5.0)
        
        # Calcula o volume médio só para ter algum dado real
        volume = np.mean(librosa.feature.rms(y=y))
        
        # Lógica temporária de teste:
        if volume < 0.01:
            return {"status": "sucesso", "categoria": "silencio_ou_clique", "confianca": 80}
        else:
            return {"status": "sucesso", "categoria": "motor_girando", "confianca": 90}
            
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}