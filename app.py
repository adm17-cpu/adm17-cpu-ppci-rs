import streamlit as st
import cv2
import numpy as np
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from pdf2image import convert_from_bytes
from PIL import Image
import io

# Configurar o cliente da Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("Erro: A chave 'GROQ_API_KEY' não foi configurada nos Secrets.")

st.set_page_config(page_title="Consultor PPCI-RS", page_icon="🔥", layout="wide")
st.title("🔥 Consultor PPCI - Contagem Visual de Itens")

# Inicializar histórico
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- BARRA LATERAL: ENVIAR PLANTA E GABARITOS ---
st.sidebar.header("📁 1. Enviar Planta Baixa")
planta_pdf = st.sidebar.file_uploader("Suba a Planta Técnica (PDF):", type=["pdf"])

st.sidebar.header("🎯 2. Enviar Blocos da Legenda")
gabarito_file = st.sidebar.file_uploader(
    "Suba a imagem com os símbolos recortados (S1, S12, Extintores...):", 
    type=["png", "jpg", "jpeg"]
)

# Função de Visão Computacional para buscar os símbolos
def contar_simbolo(img_planta_cinza, img_gabarito_cinza, threshold=0.80):
    res = cv2.matchTemplate(img_planta_cinza, img_gabarito_cinza, cv2.TM_CCOEFF_NORMED)
    w, h = img_gabarito_cinza.shape[::-1]
    
    loc = np.where(res >= threshold)
    pontos = list(zip(*loc[::-1]))
    
    # Agrupa pontos muito próximos para evitar contar o mesmo símbolo várias vezes
    pontos_filtrados = []
    for p in pontos:
        if not pontos_filtrados:
            pontos_filtrados.append(p)
        else:
            distancias = [np.linalg.norm(np.array(p) - np.array(pf)) for pf in pontos_filtrados]
            if min(distancias) > max(w, h) * 0.6:  # Distância mínima aceitável
                pontos_filtrados.append(p)
                
    return len(pontos_filtrados), pontos_filtrados, (w, h)

# Processamento visual dos arquivos carregados
resultado_contagem = ""
if planta_pdf and gabarito_file:
    with st.spinner("Processando e convertendo arquivos..."):
        try:
            # 1. Converter PDF para Imagem OpenCV
            paginas = convert_from_bytes(planta_pdf.read(), dpi=200)
            img_planta = np.array(paginas[0])
            planta_cinza = cv2.cvtColor(img_planta, cv2.COLOR_BGR2GRAY)
            
            # 2. Carregar o gabarito enviado
            img_gab = Image.open(gabarito_file)
            img_gab_np = np.array(img_gab)
            gab_cinza = cv2.cvtColor(img_gab_np, cv2.COLOR_BGR2GRAY)
            
            # Executa a contagem genérica usando o bloco fornecido
            total, locais, dim = contar_simbolo(planta_cinza, gab_cinza)
            
            resultado_contagem = f"\n[Análise de Visão Computacional]: Foram detectados aproximadamente {total} elementos correspondentes ao padrão do bloco enviado ao longo da planta."
            st.sidebar.success(f"Análise concluída! Encontrados: {total}")
            
        except Exception as e:
            st.sidebar.error(f"Erro ao processar as imagens: {e}")

# --- EXIBIÇÃO DO CHAT ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ex: Baseado no arquivo, gere o relatório de equipamentos."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    system_prompt = (
        "Você é um Engenheiro de Incêndio especialista na regulamentação do Rio Grande do Sul (Lei Kiss e RTs do CBMRS).\n"
        "O usuário utilizou um módulo de visão computacional integrado para contar os elementos visuais das legendas técnicas "
        "na planta baixa.\n"
        "Seu papel é consolidar essas informações, listar os itens identificados (como S1, S2, S12 ou Extintores), "
        "apresentar o resultado e comentar se a distribuição está em conformidade técnica com o CBMRS (ex: distâncias de caminhamento)."
    )

    pergunta_final = f"{system_prompt}\n\nPergunta: {prompt}\n{resultado_contagem}"

    try:
        with st.spinner("IA consolidando dados técnicos..."):
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": pergunta_final}],
                model="llama-3.3-70b-versatile",
            )
            response_text = chat_completion.choices[0].message.content

        with st.chat_message("assistant"):
            st.markdown(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text})
    except Exception as e:
        st.error(f"Erro na IA: {e}")
