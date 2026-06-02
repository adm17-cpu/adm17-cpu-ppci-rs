import streamlit as st
from groq import Groq

# 1. Configurar o cliente da Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("Erro: A chave 'GROQ_API_KEY' não foi configurada nos Secrets.")

st.set_page_config(page_title="Consultor PPCI-RS", page_icon="🔥")
st.title("🔥 Consultor PPCI - Rio Grande do Sul")
st.caption("Orientador de normas técnicas baseado na Lei Kiss e RTs do CBMRS (via Groq Estável).")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Barra lateral alternativa para Links de Imagens (Evita quedas de modelos de visão)
st.sidebar.header("📁 Analisar Imagem")
image_url = st.sidebar.text_input("Cole o link de uma imagem/planta (opcional):", placeholder="https://exemplo.com/imagem.jpg")

if image_url:
    st.sidebar.image(image_url, caption="Visualização do link", use_container_width=True)

if prompt := st.chat_input("Digite sua dúvida aqui..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Instrução do sistema robusta
    system_prompt = (
        "Você é um Engenheiro especialista em Segurança Contra Incêndio, atuando estritamente sob as regras "
        "do Estado do Rio Grande do Sul (Lei Complementar nº 14.376/2013, Decreto nº 51.803/2014 e Resoluções Técnicas do CBMRS).\n"
        "Diretrizes:\n"
        "1. Identifique se é CLCB, PSPCI ou PPCI Completo.\n"
        "2. Sempre cite a Lei, Decreto ou número da Resolução Técnica (RT) correspondente na resposta.\n"
        "3. Se houver um link de imagem anexado, tente contextualizar com base no texto do usuário.\n"
        "4. Diga que a consulta não substitui a responsabilidade técnica profissional no SOL-CBMRS."
    )

    # Prepara a pergunta final
    pergunta_final = f"{system_prompt}\n\nPergunta: {prompt}"
    if image_url:
        pergunta_final += f"\n[O usuário anexou este link de imagem para você analisar: {image_url}]"

    try:
        with st.spinner("Consultando regulamentações da Groq..."):
            # Usando o modelo carro-chefe estável e definitivo da Groq
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": pergunta_final}],
                model="llama-3.3-70b-specdec",
            )
            response_text = chat_completion.choices[0].message.content

        with st.chat_message("assistant"):
            st.markdown(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text})
    except Exception as e:
        st.error(f"Erro ao chamar a IA: {e}")
