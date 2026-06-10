import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from pypdf import PdfReader
import io

# 1. Configurar o cliente da Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("Erro: A chave 'GROQ_API_KEY' não foi configurada nos Secrets.")

st.set_page_config(page_title="Consultor PPCI-RS", page_icon="🔥")
st.title("🔥 Consultor PPCI - Rio Grande do Sul")
st.caption("Leitor de Plantas, Documentos Técnicos e Normas do CBMRS.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- BARRA LATERAL: CENTRAL DE ANEXOS (PLANTA E DOCUMENTOS) ---
st.sidebar.header("📁 Upload da Planta / Memorial")

uploaded_file = st.sidebar.file_uploader(
    "Anexe a Planta Baixa ou Memorial descritivo (PDF):", 
    type=["pdf"]
)

conteudo_planta = ""
if uploaded_file is not None:
    st.sidebar.success(f"Planta '{uploaded_file.name}' carregada para análise!")
    
    # Processa o PDF em busca de textos estruturados, quadros de áreas e tabelas de equipamentos
    with st.sidebar.spinner("Processando texto e tabelas da planta..."):
        try:
            reader = PdfReader(uploaded_file)
            texto_extraido = ""
            
            # Percorre as páginas buscando dados de legendas e listas de itens
            for idx, page in enumerate(reader.pages):
                texto_pagina = page.extract_text()
                if texto_pagina:
                    texto_extraido += f"\n--- PÁGINA {idx+1} ---\n{texto_pagina}"
            
            # Guarda os dados para enviar à IA
            # Limitamos para os primeiros 6000 caracteres para não estourar o limite técnico
            conteudo_planta = texto_extraido[:6000]
            st.sidebar.info("Dados de texto e tabelas mapeados com sucesso!")
        except Exception as e:
            st.sidebar.error(f"Erro ao processar a estrutura do PDF: {e}")

st.sidebar.write("---")
st.sidebar.subheader("🎙️ Comando por Voz")

audio_bytes = audio_recorder(text="", recording_color="#e85a4f", neutral_color="#6aa84f", icon_size="2x")

texto_audio_transcrito = ""
if audio_bytes:
    with st.sidebar.spinner("Processando voz..."):
        try:
            id_audio = ("fala.wav", audio_bytes, "audio/wav")
            transcription = client.audio.transcriptions.create(
                file=id_audio, model="whisper-large-v3", response_format="text"
            )
            texto_audio_transcrito = transcription
            st.sidebar.success(f"Ouvido: \"{texto_audio_transcrito}\"")
        except Exception as e:
            st.sidebar.error(f"Erro no áudio: {e}")

# --- ENTRADA DE PERGUNTAS ---
prompt = st.chat_input("Ex: 'Faça a contagem e liste os itens de segurança que você encontrou nesta planta'")

if texto_audio_transcrito and not prompt:
    prompt = texto_audio_transcrito

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Instruções rigorosas para o Engenheiro Virtual mapear itens
    system_prompt = (
        "Você é um Engenheiro especialista em Segurança Contra Incêndio no Rio Grande do Sul.\n"
        "O usuário enviou os dados extraídos de uma planta baixa/documento em PDF. Seu objetivo principal é:\n"
        "1. Analisar as tabelas, notas de rodapé, quadros de resumo e legendas textuais fornecidas na planta.\n"
        "2. Identificar e listar detalhadamente todos os itens de segurança encontrados (ex: Extintores, Sinalizações, Hidrantes, Iluminação de Emergência).\n"
        "3. Apresentar uma contagem ou quantitativo estimado baseado puramente nos dados extraídos do documento.\n"
        "4. Cruzar esses dados com as Resoluções Técnicas (RTs) do CBMRS e indicar se a lista parece adequada ou se faltam itens obrigatórios para a edificação.\n"
        "5. Finalizar lembrando que a conferência não substitui a responsabilidade técnica do profissional no SOL-CBMRS."
    )

    # Une o prompt técnico, as instruções de contagem e os dados lidos do PDF da planta
    pergunta_final = f"{system_prompt}\n\nPergunta do usuário: {prompt}"
    if conteudo_planta:
        pergunta_final += f"\n\n[DADOS EXTRAÍDOS DIRETAMENTE DO ARQUIVO DA PLANTA]:\n{conteudo_planta}"
    else:
        pergunta_final += "\n\n[Aviso: O usuário não anexou nenhuma planta em PDF para esta consulta ainda.]"

    try:
        with st.spinner("Mapeando símbolos e gerando quantitativos da planta..."):
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": pergunta_final}],
                model="llama-3.3-70b-versatile",
            )
            response_text = chat_completion.choices[0].message.content

        with st.chat_message("assistant"):
            st.markdown(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text})
    except Exception as e:
        st.error(f"Erro ao chamar a IA: {e}")
