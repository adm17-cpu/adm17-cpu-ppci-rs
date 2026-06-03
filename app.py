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

# --- TRUQUE PARA FORÇAR O ÍCONE NO CELULAR ---
# Usamos um link de um ícone de fogo em alta definição (formato PNG) para o celular reconhecer
link_icone_fogo = "https://cdn-icons-png.flaticon.com/512/785/785116.png"

st.markdown(
    f"""
    <head>
        <link rel="apple-touch-icon" href="{link_icone_fogo}">
        <link rel="icon" type="image/png" href="{link_icone_fogo}">
    </head>
    """,
    unsafe_allow_html=True
)

st.title("🔥 Consultor PPCI - Rio Grande do Sul")
st.caption("Orientador técnico baseado na Lei Kiss e RTs do CBMRS (Suporta Texto, Áudio e Arquivos).")

# Inicializar o histórico do chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Exibir mensagens anteriores
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- BARRA LATERAL: ANEXAR ARQUIVOS E GRAVAR ÁUDIO ---
st.sidebar.header("📁 Central de Anexos")

# Botão para Anexar Arquivos Reais (PDF ou Imagens promocionais/tabelas em formato texto)
uploaded_file = st.sidebar.file_uploader(
    "Anexe um documento ou relatório (PDF, PNG, JPG):", 
    type=["pdf", "png", "jpg", "jpeg"]
)

conteudo_arquivo = ""
if uploaded_file is not None:
    st.sidebar.success(f"Arquivo '{uploaded_file.name}' carregado!")
    
    # Se for PDF, extrai o texto para ajudar a IA
    if uploaded_file.name.endswith(".pdf"):
        try:
            reader = PdfReader(uploaded_file)
            texto_pdf = ""
            for page in reader.pages:
                texto_pdf += page.extract_text() or ""
            conteudo_arquivo = f"\n[Texto extraído do documento anexo {uploaded_file.name}]:\n{texto_pdf[:4000]}" # Limita tamanho
        except Exception:
            conteudo_arquivo = f"\n[O usuário anexou o PDF {uploaded_file.name}, mas não foi possível extrair o texto automaticamente.]"
    else:
        conteudo_arquivo = f"\n[O usuário anexou uma imagem chamada {uploaded_file.name} para referência técnica.]"

st.sidebar.write("---")
st.sidebar.subheader("🎙️ Gravar Pergunta por Voz")
st.sidebar.write("Clique no microfone abaixo, fale sua dúvida e clique novamente para encerrar:")

# Gravador de áudio nativo na barra lateral
audio_bytes = audio_recorder(
    text="",
    recording_color="#e85a4f",
    neutral_color="#6aa84f",
    icon_size="2x"
)

texto_audio_transcrito = ""
if audio_bytes:
    st.sidebar.audio(audio_bytes, format="audio/wav")
    with st.sidebar.spinner("Transcrevendo sua voz..."):
        try:
            # Envia o áudio gravado para o modelo Whisper da Groq (100% gratuito e ultra preciso)
            id_audio = ("fala.wav", audio_bytes, "audio/wav")
            transcription = client.audio.transcriptions.create(
                file=id_audio,
                model="whisper-large-v3",
                prompt="Termos técnicos sobre PPCI, bombeiros, Lei Kiss, RT, CBMRS, CLCB, PSPCI.",
                response_format="text"
            )
            texto_audio_transcrito = transcription
            st.sidebar.success("Áudio transcrito com sucesso!")
            st.sidebar.info(f"Identificado: \"{texto_audio_transcrito}\"")
        except Exception as e:
            st.sidebar.error(f"Erro ao transcrever áudio: {e}")

# --- PROCESSAMENTO DA MENSAGEM ---
# O prompt do usuário pode vir tanto da caixa de texto padrão quanto do microfone lateral
prompt = st.chat_input("Digite sua dúvida aqui...")

# Se o usuário usou o áudio e não digitou nada, assume o texto do áudio como o prompt principal
if texto_audio_transcrito and not prompt:
    prompt = texto_audio_transcrito

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Instrução de sistema fixa
    system_prompt = (
        "Você é um Engenheiro especialista em Segurança Contra Incêndio, atuando estritamente sob as regras "
        "do Estado do Rio Grande do Sul (Lei Complementar nº 14.376/2013, Decreto nº 51.803/2014 e Resoluções Técnicas do CBMRS).\n"
        "Diretrizes:\n"
        "1. Identifique se o caso trata-se de CLCB, PSPCI ou PPCI Completo.\n"
        "2. Sempre cite a Lei, Decreto ou número da Resolução Técnica (RT) correspondente na resposta.\n"
        "3. Se houver dados de arquivos anexados abaixo, use-os para fundamentar sua resposta técnica.\n"
        "4. Inclua o aviso legal informando que a consulta não substitui a responsabilidade técnica no SOL-CBMRS."
    )

    # Junta o comportamento + a pergunta + o texto do arquivo anexado
    pergunta_final = f"{system_prompt}\n\nPergunta do usuário: {prompt}"
    if conteudo_arquivo:
        pergunta_final += f"\n\n{conteudo_arquivo}"

    try:
        with st.spinner("Analisando regulamentações do CBMRS..."):
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
