import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. Configurar a chave da API do Gemini
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("Erro: A chave 'GEMINI_API_KEY' não foi configurada nos Secrets do Streamlit.")

st.set_page_config(page_title="Consultor PPCI-RS", page_icon="🔥")
st.title("🔥 Consultor PPCI - Rio Grande do Sul")
st.caption("Orientador de normas técnicas baseado na Lei Kiss (LC 14.376/13) e RTs do CBMRS.")

# Inicializar o histórico do chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Exibir mensagens anteriores
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- NOVO: Área de Upload de Imagem na Barra Lateral ---
st.sidebar.header("📁 Enviar Anexo")
uploaded_file = st.sidebar.file_uploader(
    "Envie uma imagem da planta, rascunho ou dúvida técnica (PNG, JPG, JPEG):", 
    type=["png", "jpg", "jpeg"]
)

imagem_pil = None
if uploaded_file is not None:
    # Abre a imagem usando a biblioteca PIL
    imagem_pil = Image.open(uploaded_file)
    # Mostra uma miniatura da imagem na barra lateral para o usuário ver que deu certo
    st.sidebar.image(imagem_pil, caption="Imagem carregada com sucesso!", use_container_width=True)

# Caixa de entrada para o texto do usuário
if prompt := st.chat_input("Digite sua dúvida aqui..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Prompt de sistema injetado para forçar as regras do RS
    system_instruction = (
        "Você é um Engenheiro especialista em Segurança Contra Incêndio, atuando estritamente sob as regras "
        "do Estado do Rio Grande do Sul (Lei Complementar nº 14.376/2013, Decreto nº 51.803/2014 e Resoluções Técnicas do CBMRS).\n\n"
        "Se o usuário enviar uma imagem (como uma planta baixa ou foto), analise-a com cuidado técnica e "
        "relacione o que vê com as exigências de PPCI do RS (ex: saídas de emergência, extintores, sinalização).\n\n"
        "Diretrizes:\n"
        "1. Identifique se o caso trata-se de CLCB, PSPCI ou PPCI Completo.\n"
        "2. Sempre cite a Lei, Decreto ou número da Resolução Técnica (RT) correspondente na resposta.\n"
        "3. Inclua um breve aviso legal pontuando que a consulta não substitui a responsabilidade técnica no SOL-CBMRS."
    )

    try:
        with st.spinner("Analisando dados e normas do CBMRS..."):
            model = genai.GenerativeModel(
                model_name='models/gemini-2.0-flash-latest',
                system_instruction=system_instruction
            )
            
            # Se o usuário carregou uma imagem, enviamos o texto E a imagem juntos para a IA
            if imagem_pil:
                conteudo_envio = [prompt, imagem_pil]
            else:
                conteudo_envio = prompt
                
            response = model.generate_content(conteudo_envio)
            
        with st.chat_message("assistant"):
            st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
    except Exception as e:
        st.error(f"Erro ao chamar a IA: {e}")
