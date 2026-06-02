import streamlit as st
from groq import Groq
from PIL import Image
import io
import base64

# 1. Configurar o cliente da Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("Erro: A chave 'GROQ_API_KEY' não foi configurada nos Secrets.")

st.set_page_config(page_title="Consultor PPCI-RS", page_icon="🔥")
st.title("🔥 Consultor PPCI - Rio Grande do Sul")
st.caption("Orientador de normas técnicas baseado na Lei Kiss e RTs do CBMRS (via Groq).")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Barra lateral para upload de imagem
st.sidebar.header("📁 Enviar Anexo")
uploaded_file = st.sidebar.file_uploader("Envie uma imagem da dúvida técnica:", type=["png", "jpg", "jpeg"])

base64_image = None
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.sidebar.image(image, caption="Imagem carregada!", use_container_width=True)
    
    # Converte imagem para base64 para enviar à Groq
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    base64_image = base6464encode = base64.b64encode(buffered.getvalue()).decode('utf-8')

if prompt := st.chat_input("Digite sua dúvida aqui..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Instrução do sistema
    system_prompt = (
        "Você é um Engenheiro especialista em Segurança Contra Incêndio, atuando estritamente sob as regras "
        "do Estado do Rio Grande do Sul (Lei Complementar nº 14.376/2013, Decreto nº 51.803/2014 e Resoluções Técnicas do CBMRS).\n"
        "Diretrizes: Identifique se é CLCB, PSPCI ou PPCI Completo. Cite as Leis/RTs. Diga que a consulta não substitui a responsabilidade técnica profissional."
    )

    # Monta a estrutura de conteúdo da mensagem
    content_list = [{"type": "text", "text": f"{system_prompt}\n\nPergunta: {prompt}"}]
    
    if base64_image:
        content_list.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
        })

    try:
        with st.spinner("Consultando regulamentações da Groq..."):
            # Usando o modelo Llama 3 Vision de alta velocidade e gratuito da Groq
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": content_list}],
                model="llama-3.2-90b-vision-preview",
            )
            response_text = chat_completion.choices[0].message.content

        with st.chat_message("assistant"):
            st.markdown(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text})
    except Exception as e:
        st.error(f"Erro ao chamar a IA: {e}")
