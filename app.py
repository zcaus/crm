from dotenv import load_dotenv
import os
from supabase import create_client, Client
import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime, timedelta

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Use os nomes das variáveis de ambiente
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL e Key são obrigatórios!")

# Cria o cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Função para formatar valores monetários no padrão brasileiro: "R$ XXX.XXX,XX"
def format_currency_br(value):
    try:
        formatted = f"{float(value):,.2f}"  # Ex: 12,345.67
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted}"
    except Exception:
        return value

# Função para gerar o buffer do Excel (remove a coluna "id" e adiciona a coluna "Usuário")
@st.cache_data
def get_excel_buffer(df):
    df_copy = df.copy()
    if "id" in df_copy.columns:
        df_copy.drop(columns=["id"], inplace=True)
    df_copy["Usuário"] = st.session_state.perfil_selecionado
    buffer = io.BytesIO()
    df_copy.to_excel(buffer, index=False)
    buffer.seek(0)
    return buffer

# **Definição de Perfis, Logins e Senhas**
perfis = {
    "Cláudia Costa": {"login": "Claudia", "senha": "1501"},
    "Evandro Alexandre": {"login": "Evandro", "senha": "0512"},
    "Renan": {"login": "Renan", "senha": "1710"},
    "Cauã Moreira": {"login": "Caua", "senha": "2805"}
}

# **Inicializar Session State**
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'perfil_selecionado' not in st.session_state:
    st.session_state.perfil_selecionado = None
# Armazena o horário selecionado; por padrão, hora atual - 3 horas
if 'hora_selecionada' not in st.session_state:
    st.session_state.hora_selecionada = (datetime.now() - timedelta(hours=3)).time()

# **Função para Autenticar**
def autenticar(login, senha):
    for perfil, creds in perfis.items():
        if creds["login"] == login and creds["senha"] == senha:
            return perfil
    return None

# **Interface de Login (quando não autenticado)**
if not st.session_state.autenticado:
    st.title("Login")
    login_input = st.text_input("Login")
    senha_input = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        perfil = autenticar(login_input, senha_input)
        if perfil:
            st.session_state.autenticado = True
            st.session_state.perfil_selecionado = perfil
            st.success(f"Bem-vindo, {perfil}!")
        else:
            st.error("Login ou senha inválidos.")

# Funções para interagir com o Supabase
def salvar_agendamento_supabase(agendamento: dict):
    response = supabase.table("agendamentos").insert({
        "Data": agendamento["Data"],
        "Hora": agendamento["Hora"],
        "Nome": agendamento["Nome"],
        "Telefone": agendamento["Telefone"],
        "Fechou": agendamento["Fechou?"],
        "Valor": agendamento["Valor(R$)"],
        "CEP": agendamento["CEP"],
        "Observacao": agendamento["Observação"],
        "Usuario": agendamento["Usuario"]
    }).execute()
    if response.error:
        st.error(f"Erro ao salvar: {response.error.message}")

def ler_agendamentos_supabase(usuario: str):
    response = supabase.table("agendamentos").select("*").eq("Usuario", usuario).execute()
    if response.error:
        st.error(f"Erro ao ler os dados: {response.error.message}")
        return pd.DataFrame()
    return pd.DataFrame(response.data)

# **Interface de Cadastro e Gestão (após login)**
if st.session_state.autenticado:
    with st.form("agendamento_form"):
        col1, col2 = st.columns(2)
        data_visita = col1.date_input("Selecione a Data da Visita", format="DD/MM/YYYY")
        data_visita_formatada = data_visita.strftime("%d/%m/%Y")
        # Usa o valor armazenado (com 3 horas a menos) para preencher o campo de hora
        hora_visita = col2.time_input("Selecione o Horário", value=st.session_state.hora_selecionada)
        hora_visita_formatada = hora_visita.strftime("%H:%M")
        nome_cliente = st.text_input("Nome do Cliente")
        telefone_cliente = st.text_input("Telefone do Cliente", placeholder="(00) 00000-0000")
        cliente_fechou = st.selectbox("Cliente fechou?", ["Sim", "Não", "Em negociação"])
        col1, col2 = st.columns(2)
        sefechou_valor = col1.text_input("Valor (R$)", placeholder="R$ 0,00")
        endereco = col2.text_input("CEP", placeholder="00000000")
        observacao = st.text_area("Observação")
        submitted = st.form_submit_button("Marcar")
        if submitted:
            st.session_state.hora_selecionada = hora_visita
            telefone_cliente = re.sub(r"(\d{2})(\d{4,5})(\d{4})", r"(\1) \2-\3", telefone_cliente)
            if len(endereco) == 8 and endereco.isdigit():
                endereco_formatado = "{}-{}".format(endereco[:5], endereco[5:])
                agendamento = {
                    "Data": data_visita_formatada,
                    "Hora": hora_visita_formatada,
                    "Nome": nome_cliente,
                    "Telefone": telefone_cliente,
                    "Fechou?": cliente_fechou,
                    "Valor(R$)": sefechou_valor,
                    "CEP": endereco_formatado,
                    "Observação": observacao,
                    "Usuario": st.session_state.perfil_selecionado
                }
                salvar_agendamento_supabase(agendamento)
                st.success("Visita realizada com Sucesso!")
            else:
                st.error("CEP inválido. Insira 8 dígitos numéricos.")

    # Ler e exibir os agendamentos do usuário logado
    agendamentos = ler_agendamentos_supabase(st.session_state.perfil_selecionado)
    if not agendamentos.empty:
        if "Valor" in agendamentos.columns:
            try:
                agendamentos["Valor"] = agendamentos["Valor"].apply(
                    lambda x: format_currency_br(x) if x not in [None, ""] else ""
                )
            except Exception as e:
                st.error(f"Erro na formatação do valor: {e}")
        df_display = agendamentos.drop("id", axis=1) if "id" in agendamentos.columns else agendamentos.copy()
        st.markdown("### Agendamentos")
        st.dataframe(df_display)
        excel_buffer = get_excel_buffer(agendamentos)
        st.download_button(
            label="Download como XLSX",
            data=excel_buffer.getvalue(),
            file_name="agendamentos.xlsx",
            mime="application/vnd.ms-excel"
        )
    else:
        st.write("Nenhum agendamento realizado até o momento.")

    if st.button("Sair"):
        st.session_state.autenticado = False
        st.session_state.perfil_selecionado = None
        st.info("Você saiu da aplicação.")
        st.rerun()
