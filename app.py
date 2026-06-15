import streamlit as st
import cv2
import numpy as np
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from pdf2image import convert_from_bytes
from PIL import Image
import os

# 1. Configurar o cliente da Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("Erro: A chave 'GROQ_API_KEY' não foi configurada nos Secrets.")

st.set_page_config(page_title="Consultor PPCI-RS", page_icon="🔥", layout="wide")
st.title("🔥 Consultor e Assessor de PPCI - Rio Grande do Sul")
st.caption("Módulo Avançado de Contagem e Análise Normativa Automatizada.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- FUNÇÃO DE VISÃO COMPUTACIONAL (OPENCV) ---
def realizar_contagem_visual(planta_bytes, nome_gabarito):
    try:
        # Converte a primeira página do PDF para imagem de alta resolução
        paginas = convert_from_bytes(planta_bytes, dpi=200)
        img_planta = np.array(paginas[0])
        planta_cinza = cv2.cvtColor(img_planta, cv2.COLOR_BGR2GRAY)
        
        # Carrega o gabarito que foi guardado no repositório do GitHub
        if not os.path.exists(nome_gabarito):
            return 0, False
            
        gab_cinza = cv2.imread(nome_gabarito, cv2.IMREAD_GRAYSCALE)
        w, h = gab_cinza.shape[::-1]
        
        # Varre a planta à procura do símbolo
        res = cv2.matchTemplate(planta_cinza, gab_cinza, cv2.TM_CCOEFF_NORMED)
        limiar = 0.80  # 80% de precisão visual
        loc = np.where(res >= limiar)
        pontos = list(zip(*loc[::-1]))
        
        # Agrupa marcações muito próximas para evitar duplicados
        pontos_filtrados = []
        for p in pontos:
            if not pontos_filtrados:
                pontos_filtrados.append(p)
            else:
                distancias = [np.linalg.norm(np.array(p) - np.array(pf)) for pf in pontos_filtrados]
                if min(distancias) > max(w, h) * 0.6:
                    pontos_filtrados.append(p)
                    
        return len(pontos_filtrados), True
    except Exception:
        return 0, False

# --- BARRA LATERAL: ENTRADA DE DADOS ---
st.sidebar.header("📁 Módulo de Análise de Plantas")
planta_pdf = st.sidebar.file_uploader("Carregar Planta Baixa do Projeto (PDF):", type=["pdf"])

relatorio_computacional = ""

if planta_pdf:
    planta_bytes = planta_pdf.read()
    st.sidebar.success("Planta carregada na memória!")
    
    with st.sidebar.spinner("A processar e a contar os símbolos do projeto..."):
        # O algoritmo tenta contar usando as imagens de gabarito guardadas no seu GitHub
        total_s1, ok_s1 = realizar_contagem_visual(planta_bytes, "s1.png")
        total_s2, ok_s2 = realizar_contagem_visual(planta_bytes, "s2.png")
        total_s12, ok_s12 = realizar_contagem_visual(planta_bytes, "s12.png")
        
        # Constrói o texto que será entregue à IA nos bastidores
        relatorio_computacional = "\n\n[DADOS DE CONTAGEM EXTRAÍDOS DA PLANTA VISUALMENTE]:\n"
        if ok_s1 or ok_s2 or ok_s12:
            relatorio_computacional += f"- Símbolos 'S1' (Placa Saída Direita): {total_s1} encontrados.\n"
            relatorio_computacional += f"- Símbolos 'S2' (Placa Saída Esquerda): {total_s2} encontrados.\n"
            relatorio_computacional += f"- Símbolos 'S12' (Placa Saída Frontal): {total_s12} encontrados.\n"
        else:
            relatorio_computacional += (
                "- O utilizador subiu o PDF, mas os ficheiros de gabarito (s1.png, s2.png, s12.png) "
                "não foram encontrados ou mapeados na raiz do GitHub para fazer a contagem automatizada.\n"
            )

st.sidebar.write("---")
st.sidebar.subheader("🎙️ Gravar Dúvida por Voz")
audio_bytes = audio_recorder(text="", recording_color="#e85a4f", neutral_color="#6aa84f", icon_size="2x")

texto_audio_transcrito = ""
if audio_bytes:
    with st.sidebar.spinner("A transcrever áudio..."):
        try:
            id_audio = ("fala.wav", audio_bytes, "audio/wav")
            transcription = client.audio.transcriptions.create(
                file=id_audio, model="whisper-large-v3", response_format="text"
            )
            texto_audio_transcrito = transcription
            st.sidebar.success("Áudio processado!")
        except Exception as e:
            st.sidebar.error(f"Erro no áudio: {e}")

# --- APRESENTAÇÃO DO CHAT ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Digite a sua pergunta técnica ou peça a análise da planta...")

if texto_audio_transcrito and not prompt:
    prompt = texto_audio_transcrito

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Instrução estrita: Consultoria com ou sem plantas + apenas citações curtas
    system_prompt = (
        "Você é um Engenheiro Assessor especialista em Segurança Contra Incêndio no Rio Grande do Sul (Lei Kiss e RTs do CBMRS).\n"
        "Suas diretrizes obrigatórias de resposta:\n"
        "1. Se houver dados de contagem de símbolos anexados abaixo pelo algoritmo, use-os para analisar o projeto do usuário.\n"
        "2. Você deve responder perfeitamente a qualquer dúvida técnica MESMO se o usuário não anexar plantas.\n"
        "3. FORMATO DE CITAÇÃO: Não copie textos longos de leis. Apenas cite de forma curta o número da norma e tabela (Ex: 'Conforme RT-11, Tabela 1...' ou 'Segundo o Dec. Estadual 51.803/14...').\n"
        "4. Seja direto, focado na prática da engenharia e responda no mesmo idioma do usuário.\n"
        "5. Finalize indicando que a consulta não anula o trâmite oficial no SOL-CBMRS."
    )

    pergunta_final = f"{system_prompt}\n\nDúvida/Comando do Utilizador: {prompt}{relatorio_computacional}"

    try:
        with st.spinner("A analisar regulamentações técnicas..."):
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": pergunta_final}],
                model="llama-3.3-70b-versatile",
            )
            response_text = chat_completion.choices[0].message.content

        with st.chat_message("assistant"):
            st.markdown(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text})
    except Exception as e:
        st.error(f"Erro ao gerar a resposta da IA: {e}")
