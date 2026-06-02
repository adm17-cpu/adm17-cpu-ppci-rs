import streamlit as st
import google.generativeai as genai

# 1. Configurar a chave da API do Gemini obtida nos Secrets do Streamlit
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

# Caixa de entrada para o usuário
if prompt := st.chat_input("Ex: Quais edificações se enquadram como PSPCI?"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Prompt de sistema injetado para forçar as regras do RS
    system_instruction = (
        "Você é um Engenheiro especialista em Segurança Contra Incêndio, atuando estritamente sob as regras "
        "do Estado do Rio Grande do Sul (Lei Complementar nº 14.376/2013, Decreto nº 51.803/2014 e Resoluções Técnicas do CBMRS).\n\n"
        "Diretrizes:\n"
        "1. Identifique se o caso do usuário trata-se de CLCB, PSPCI ou PPCI Completo.\n"
        "2. Sempre cite a Lei, Decreto ou número da Resolução Técnica (RT) correspondente na resposta.\n"
        "3. Se faltarem dados importantes da edificação (como área, altura ou ocupação), peça educadamente.\n"
        "4. Inclua um breve aviso legal em suas respostas pontuando que a consulta não substitui a responsabilidade técnica do profissional habilitado no SOL-CBMRS."
    )

    try:
        with st.spinner("Consultando normas do CBMRS..."):
            model = genai.GenerativeModel(
                model_name='gemini-2.0-flash',
                system_instruction=system_instruction
            )
            response = model.generate_content(prompt)
            
        with st.chat_message("assistant"):
            st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
    except Exception as e:
        st.error(f"Erro ao chamar a IA: {e}")
