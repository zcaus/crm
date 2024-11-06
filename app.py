import streamlit as st
import csv
import pandas as pd
from datetime import datetime
import re

# **Definição de Perfis, Logins e Senhas**
perfis = {
    "Luis Antônio": {"login": "Luis", "senha": "1710", "csv": "perfil1.csv"},
    "Antônio Pereira": {"login": "Antonio", "senha": "1710", "csv": "perfil2.csv"},
    "Leandro Macedo": {"login": "Leandro", "senha": "1710", "csv": "perfil3.csv"}
}

# **Iniciar Session State**
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'perfil_selecionado' not in st.session_state:
    st.session_state.perfil_selecionado = None

# **Função para Autenticar**
def autenticar(login, senha):
    for perfil, creds in perfis.items():
        if creds["login"] == login and creds["senha"] == senha:
            return perfil
    return None

# **Interface de Login (somente se não autenticado)**
if not st.session_state.autenticado:
    st.title("Login")
    login = st.text_input("Login")
    senha = st.text_input("Senha", type="password")
    #
    if st.button("Entrar"):
        perfil_selecionado = autenticar(login, senha)
        if perfil_selecionado:
            st.session_state.autenticado = True
            st.session_state.perfil_selecionado = perfil_selecionado
            st.success(f"Bem-vindo, {perfil_selecionado}!")
        else:
            st.error("Login ou senha inválidos.")

# **Interface de Cadastro (após login)**
if st.session_state.autenticado:
    arquivo_csv = perfis[st.session_state.perfil_selecionado]["csv"]  # CSV associado ao perfil

    # Criar um cabeçalho para o arquivo CSV se ele estiver vazio
    try:
        pd.read_csv(arquivo_csv)
    except pd.errors.EmptyDataError:
        with open(arquivo_csv, 'w') as arquivo:
            arquivo.write("Data,Hora,Nome,Telefone,Fechou?,Valor(R$),CEP")

    # Função para ler agendamentos do arquivo CSV
    def ler_agendamentos():
        try:
            return pd.read_csv(arquivo_csv, dtype={'Telefone': str, 'CEP': str})
        except FileNotFoundError:
            return pd.DataFrame(columns=['Data', 'Hora', 'Nome', 'Telefone', 'Fechou?', 'Valor(R$)', 'CEP'])

    # Função para salvar agendamento no arquivo CSV
    def salvar_agendamento(agendamento):
        agendamentos = ler_agendamentos()
        if agendamentos.empty:
            agendamento['id'] = 1
        else:
            agendamento['id'] = agendamentos['id'].max() + 1
        agendamentos = agendamentos._append(agendamento, ignore_index=True)
        agendamentos.to_csv(arquivo_csv, index=False)

    # Formulário de Agendamento
    with st.form("agendamento"):
        col1, col2 = st.columns(2)
        data_visita = col1.date_input("Selecione a Data da Visita", format="DD/MM/YYYY")
        data_visita_formatada = data_visita.strftime('%d/%m/%Y')
        hora_visita = col2.text_input("Escreva o Horário")
        nome_cliente = st.text_input("Nome do Cliente")
        telefone_cliente = st.text_input("Telefone do Cliente", placeholder="(00) 00000-0000")
        cliente_fechou = st.selectbox("Cliente fechou?", ["Sim", "Não"])
        col1, col2 = st.columns(2)
        sefechou_valor = col1.text_input("Valor (R$)", placeholder="R$ 0,00")
        endereco = col2.text_input("CEP", placeholder="00000-000")
        submitted = st.form_submit_button("Marcar")

        if submitted:
            telefone_cliente = re.sub(r'(\d{2})(\d{4,5})(\d{4})', r'(\1) \2-\3', telefone_cliente)
        if len(endereco) == 8:  # Supondo que o CEP tenha 8 dígitos (XXXXX-XXX)
            endereco = "{}-{}".format(endereco[:5], endereco[5:])

            agendamento = {
                'Data': data_visita_formatada,
                'Hora': hora_visita,
                'Nome': nome_cliente,
                'Telefone': telefone_cliente,  
                'Fechou?': cliente_fechou,
                'Valor(R$)': sefechou_valor,
                'CEP': endereco
            }
            salvar_agendamento(agendamento)
            st.success("Visita realizada com Sucesso!")
           
    # Limpar os campos usando st.session_state
    st.session_state.data_visita = None
    st.session_state.hora_visita = None
    st.session_state.nome_cliente = None
    st.session_state.telefone_cliente = None
    st.session_state.cliente_fechou = None
    st.session_state.sefechou_valor = None
    st.session_state.endereco = None

    agendamentos = ler_agendamentos()
    if not agendamentos.empty:
        st.write(agendamentos)
    else:
        st.write("Nenhuma visita realizada até o momento.")
    
      # **Botão para Sair**
    if st.button("Sair"):
        st.session_state.autenticado = False
        st.session_state.perfil_selecionado = None
        st.info("Você saiu da aplicação.")
