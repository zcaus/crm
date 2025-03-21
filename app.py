from dotenv import load_dotenv
import os
import bcrypt
import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime, timedelta
from supabase import create_client

# Carrega as variáveis de ambiente (se estiver usando secrets.toml no Streamlit Cloud, elas já estarão disponíveis)
load_dotenv()

# Inicializa a conexão com o Supabase
@st.cache_resource
def init_connection():
    # Tenta obter credenciais dos secrets do Streamlit primeiro
    if hasattr(st, "secrets") and "connections" in st.secrets and "supabase" in st.secrets.connections:
        url = st.secrets.connections.supabase.SUPABASE_URL
        key = st.secrets.connections.supabase.SUPABASE_KEY
    else:
        # Caso contrário, usa variáveis de ambiente
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError("Credenciais do Supabase não encontradas!")
    
    return create_client(url, key)

# Inicializa a conexão
supabase = init_connection()

# Função para inserir usuários iniciais
def inserir_usuarios_iniciais():
    # Verifica se existem usuários
    response = supabase.table("usuarios").select("count").execute()
    count = 0
    if response.data:
        count = response.data[0]['count']
    
    if count == 0:
        # Usuários iniciais com senhas hasheadas
        usuarios = [
            {"nome": "Cláudia Costa", "login": "Claudia", "senha": bcrypt.hashpw("1501".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')},
            {"nome": "Evandro Alexandre", "login": "Evandro", "senha": bcrypt.hashpw("0512".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')},
            {"nome": "Renan", "login": "Renan", "senha": bcrypt.hashpw("1710".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')},
            {"nome": "Cauã Moreira", "login": "Caua", "senha": bcrypt.hashpw("2805".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')}
        ]
        
        for usuario in usuarios:
            supabase.table("usuarios").insert(usuario).execute()

inserir_usuarios_iniciais()
# Função para autenticar usuário
def autenticar_usuario(login, senha):
    response = supabase.table("usuarios").select("senha, nome").eq("login", login).execute()
    
    if response.data:
        senha_hash = response.data[0]['senha']
        nome = response.data[0]['nome']
        
        if bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8')):
            return nome
    
    return None

# Função para salvar agendamento (usada por usuários que não são "Caua")
def salvar_agendamento(agendamento):
    supabase.table("agendamentos").insert(agendamento).execute()

# Função para ler agendamentos filtrados por usuário
@st.cache_data(ttl=10)  # Cache por 10 segundos
def ler_agendamentos_por_usuario(usuario):
    response = supabase.table("agendamentos").select("*").eq("Usuario", usuario).order("id", desc=True).execute()
    return pd.DataFrame(response.data)

# Função para ler todos os agendamentos (usada pelo usuário "Caua")
@st.cache_data(ttl=10)
def ler_todos_agendamentos():
    response = supabase.table("agendamentos").select("*").order("id", desc=True).execute()
    return pd.DataFrame(response.data)

# Função para formatar valor em real
def format_currency_br(value):
    try:
        formatted = f"{float(value):,.2f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted}"
    except Exception:
        return value

# Função para gerar o buffer do Excel
@st.cache_data
def get_excel_buffer(df):
    df_copy = df.copy()
    if "id" in df_copy.columns:
        df_copy.drop(columns=["id"], inplace=True)
    buffer = io.BytesIO()
    df_copy.to_excel(buffer, index=False)
    buffer.seek(0)
    return buffer

# Inicializar Session State para login e horário selecionado
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'usuario' not in st.session_state:
    st.session_state.usuario = None
if 'hora_selecionada' not in st.session_state:
    st.session_state.hora_selecionada = (datetime.now() - timedelta(hours=3)).time()

# Interface de Login
if not st.session_state.autenticado:
    st.title("Login")
    login_input = st.text_input("Login")
    senha_input = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        nome_usuario = autenticar_usuario(login_input, senha_input)
        if nome_usuario:
            st.session_state.autenticado = True
            st.session_state.usuario = login_input  # Armazena o login para uso posterior
            st.success(f"Bem-vindo(a), {nome_usuario}!")
        else:
            st.error("Login ou senha inválidos.")

# Interface após login
if st.session_state.autenticado:
    # Se o usuário logado for "Caua", exibe somente o acompanhamento com filtros
    if st.session_state.usuario in ["Caua", "Renan"]:
        st.title("Acompanhamento de Visitas")
        
        # Filtros: data e vendedor
        col1, col2 = st.columns(2)
        with col1:
            filtro_data = st.date_input("Filtrar por Data", value=datetime.now().date())
        with col2:
            # Cria uma lista com vendedores a partir dos agendamentos ou uma lista pré-definida
            vendedores_opcoes = ["Todos", "Claudia", "Evandro"]
            filtro_vendedor = st.selectbox("Filtrar por Vendedor", options=vendedores_opcoes)
        
        # Lê todos os agendamentos
        agendamentos = ler_todos_agendamentos()
        
        # Converte a coluna "Data" para datetime, considerando o formato "DD/MM/YYYY"
        if not agendamentos.empty and "Data" in agendamentos.columns:
            agendamentos["Data_dt"] = pd.to_datetime(agendamentos["Data"], format="%d/%m/%Y", errors='coerce')
            # Aplica filtro por data comparando com filtro_data (que já é um objeto date)
            agendamentos = agendamentos[agendamentos["Data_dt"].dt.date == filtro_data]
        
        # Aplica filtro por vendedor, se selecionado
        if filtro_vendedor != "Todos" and "Usuario" in agendamentos.columns:
            agendamentos = agendamentos[agendamentos["Usuario"] == filtro_vendedor]
        
        if not agendamentos.empty:
            if "Valor" in agendamentos.columns:
                try:
                    agendamentos["Valor"] = agendamentos["Valor"].apply(
                        lambda x: format_currency_br(x) if x not in [None, ""] else ""
                    )
                except Exception as e:
                    st.error(f"Erro na formatação do valor: {e}")
            df_display = agendamentos.drop(columns=["id", "Data_dt"], errors='ignore')
            st.markdown("### Visitas")
            st.dataframe(df_display)
            excel_buffer = get_excel_buffer(agendamentos)
            st.download_button(
                label="Download como XLSX",
                data=excel_buffer.getvalue(),
                file_name="agendamentos.xlsx",
                mime="application/vnd.ms-excel"
            )
        else:
            st.write("Nenhuma visita encontrada para os filtros selecionados.")
    
    # Para os demais usuários, exibe a interface de cadastro e visualização de seus agendamentos
    else:
        st.title("Cadastro de Visitas")
        with st.form("agendamento_form"):
            col1, col2 = st.columns(2)
            data_visita = col1.date_input("Selecione a Data da Visita", format="DD/MM/YYYY")
            data_visita_formatada = data_visita.strftime("%d/%m/%Y")
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
                        "Fechou": cliente_fechou,
                        "Valor": sefechou_valor,
                        "CEP": endereco_formatado,
                        "Observacao": observacao,
                        "Usuario": st.session_state.usuario
                    }
                    salvar_agendamento(agendamento)
                    st.success("Visita realizada com Sucesso!")
                else:
                    st.error("CEP inválido. Insira 8 dígitos numéricos.")
        
        # Ler e exibir os agendamentos do usuário logado
        agendamentos = ler_agendamentos_por_usuario(st.session_state.usuario)
        if not agendamentos.empty:
            if "Valor" in agendamentos.columns:
                try:
                    agendamentos["Valor"] = agendamentos["Valor"].apply(
                        lambda x: format_currency_br(x) if x not in [None, ""] else ""
                    )
                except Exception as e:
                    st.error(f"Erro na formatação do valor: {e}")
            df_display = agendamentos.drop("id", axis=1) if "id" in agendamentos.columns else agendamentos.copy()
            st.markdown("### Suas Visitas")
            st.dataframe(df_display)
            excel_buffer = get_excel_buffer(agendamentos)
            st.download_button(
                label="Download como XLSX",
                data=excel_buffer.getvalue(),
                file_name="agendamentos.xlsx",
                mime="application/vnd.ms-excel"
            )
        else:
            st.write("Nenhua visita realizada até o momento.")
    
    if st.button("Sair"):
        st.session_state.autenticado = False
        st.session_state.usuario = None
        st.info("Você saiu da aplicação.")
        st.rerun()
