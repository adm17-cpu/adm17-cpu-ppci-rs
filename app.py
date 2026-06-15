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
st.title("🔥 Consultor e Assessor de PPCI - Rio Grande do Sul")
st.caption("Contagem visual de itens e assessoria normativa baseada nas RTs do CBMRS.")

# Inicializar histórico do chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- BARRA LATERAL: ENVIAR PLANTA E GABARITOS (OPCIONAL) ---
st.sidebar.header("📁 1. Módulo de Planta (Opcional)")
planta_pdf = st.sidebar.file_uploader("Suba a Planta Técnica (PDF):", type=["pdf"])

st.sidebar.header("🎯 2. Módulo de Gabarito (Opcional)")
gabarito_file = st.sidebar.file_uploader(
    "Suba o símbolo recortado (S1, S12, Extintor...) para contar:", 
    type=["png", "jpg", "jpeg"]
)

# Função de Visão Computacional para buscar os símbolos
def contar_simbolo(img_planta_cinza, img_gabarito_cinza, threshold=0.80):
    res = cv2.matchTemplate(img_planta_cinza, img_gabarito_cinza, cv2.TM_CCOEFF_NORMED)
    w, h = img_gabarito_cinza.shape[::-1]
    
    loc = np.where(res >= threshold)
    pontos = list(zip(*loc[::-1]))
    
    pontos_filtrados = []
    for p in pontos:
        if not pontos_filtrados:
            pontos_filtrados.append(p)
        else:
            distancias = [np.linalg.norm(np.array(p) - np.array(pf)) for pf in pontos_filtrados]
            if min(distancias) > max(w, h) * 0.6:
                pontos_filtrados.append(p)
                
    return len(pontos_filtrados)

# Processamento visual se houver arquivos
resultado_contagem = ""
if planta_pdf and gabarito_file:
    with st.sidebar.spinner("Analisando planta visualmente..."):
        try:
            paginas = convert_from_bytes(planta_pdf.read(), dpi=200)
            img_planta = np.array(paginas[0])
            planta_cinza = cv2.cvtColor(img_planta, cv2.COLOR_BGR2GRAY)
            
            img_gab = Image.open(gabarito_file)
            img_gab_np = np.array(img_gab)
            gab_cinza = cv2.cvtColor(img_gab_np, cv2.COLOR_BGR2GRAY)
            
            total = contar_simbolo(planta_cinza, gab_cinza)
            resultado_contagem = f"\n[Resultado da Visão Computacional]: O algoritmo contou {total} unidades do símbolo enviado na planta."
            st.sidebar.success(f"Encontrados na planta: {total}")
        except Exception as e:
            st.sidebar.error(f"Erro no processamento visual: {e}")

st.sidebar.write("---")
st.sidebar.subheader("🎙️ Comando por Voz")
audio_bytes = audio_recorder(text="", recording_color="#e85a4f", neutral_color="#6aa84f", icon_size="2x")

texto_audio_transcrito = ""
if audio_bytes:
    with st.sidebar.spinner("Processando áudio..."):
        try:
            id_audio = ("fala.wav", audio_bytes, "audio/wav")
            transcription = client.audio.transcriptions.create(
                file=id_audio, model="whisper-large-v3", response_format="text"
            )
            texto_audio_transcrito = transcription
            st.sidebar.success("Áudio gravado!")
        except Exception as e:
            st.sidebar.error(f"Erro no áudio: {e}")

# --- EXIBIÇÃO DO CHAT ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Caixa de entrada principal
prompt = st.chat_input("Digite sua dúvida normativa ou comando...")

if texto_audio_transcrito and not prompt:
    prompt = texto_audio_transcrito

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Regras do Sistema Estritas (Citações curtas e respostas sem plantas)
    system_prompt = (
        "Você é um Engenheiro Assessor Técnico de Segurança Contra Incêndio no Rio Grande do Sul (Lei Kiss e RTs do CBMRS).\n"
        "Seu comportamento deve seguir estritamente estas diretrizes:\n"
        "1. Você deve responder perfeitamente a consultas normativas MESMO SE O USUÁRIO NÃO ENVIAR NENHUMA PLANTA (atue como consultor de bolso).\n"
        "2. Se o usuário perguntar sobre dimensões mínimas de acessos, portas, rampas ou escadas, informe os parâmetros técnicos objetivos.\n"
        "3. REGRA OBRIGATÓRIA DE FORMATAÇÃO: Você está proibido de transcrever textos longos ou artigos completos da legislação. "
        "Apenas cite o nome/número da legislação de forma resumida (Exemplo: 'Conforme RT-11/CBMRS, Tabela 2...' ou 'Segundo o Decreto Estadual nº 51.803/14...').\n"
        "4. Seja curto, focado na engenharia prática e direto ao ponto.\n"
        "5. Finalize informando que a consulta não anula a validação no SOL-CBMRS."
    )

    pergunta_final = f"{system_prompt}\n\nMensagem/Dúvida do Usuário: {prompt}\n{resultado_contagem}"

    try:
        with st.spinner("Buscando referências técnicas no CBMRS..."):
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
