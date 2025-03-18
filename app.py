import streamlit as st
import pandas as pd
import re
import io
import os

# **Definição de Perfis, Logins e Senhas**
perfis = {
    "Cláudia Regina": {"login": "Claudia", "senha": "1501", "csv": "perfil1.csv"},
    "Evandro Alexandre": {"login": "Evandro", "senha": "0512", "csv": "perfil2.csv"},
    "Renan": {"login": "Renan", "senha": "1710", "csv": "perfil3.csv"}
}

# **Inicializar Session State**
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

# **Interface de Login (quando não autenticado)**
if not st.session_state.autenticado:
    st.title("Login")
    login = st.text_input("Login")
    senha = st.text_input("Senha", type="password")
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

    # Se o arquivo não existir, cria com cabeçalho incluindo a coluna 'id'
    if not os.path.exists(arquivo_csv):
        with open(arquivo_csv, 'w') as arquivo:
            arquivo.write("id,Data,Hora,Nome,Telefone,Fechou?,Valor(R$),CEP\n")
    else:
        # Caso o arquivo exista, mas esteja vazio, também cria o cabeçalho
        try:
            df_temp = pd.read_csv(arquivo_csv)
            if df_temp.empty or "id" not in df_temp.columns:
                raise ValueError
        except Exception:
            with open(arquivo_csv, 'w') as arquivo:
                arquivo.write("id,Data,Hora,Nome,Telefone,Fechou?,Valor(R$),CEP\n")

    # Função para ler os agendamentos do arquivo CSV
    def ler_agendamentos():
        try:
            return pd.read_csv(arquivo_csv, dtype={'Telefone': str, 'CEP': str})
        except FileNotFoundError:
            return pd.DataFrame(columns=['id', 'Data', 'Hora', 'Nome', 'Telefone', 'Fechou?', 'Valor(R$)', 'CEP'])

    # Função para salvar agendamento no arquivo CSV utilizando concatenação
    def salvar_agendamento(agendamento):
        agendamentos = ler_agendamentos()
        if agendamentos.empty:
            agendamento['id'] = 1
        else:
            agendamento['id'] = agendamentos['id'].max() + 1
        novo_df = pd.DataFrame([agendamento])
        agendamentos = pd.concat([agendamentos, novo_df], ignore_index=True)
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
        endereco = col2.text_input("CEP", placeholder="00000000")  # CEP sem formatação para validação
        submitted = st.form_submit_button("Marcar")

        if submitted:
            # Formatar telefone
            telefone_cliente = re.sub(r'(\d{2})(\d{4,5})(\d{4})', r'(\1) \2-\3', telefone_cliente)
            # Validar e formatar CEP (deve conter exatamente 8 dígitos)
            if len(endereco) == 8 and endereco.isdigit():
                endereco_formatado = "{}-{}".format(endereco[:5], endereco[5:])
                agendamento = {
                    'Data': data_visita_formatada,
                    'Hora': hora_visita,
                    'Nome': nome_cliente,
                    'Telefone': telefone_cliente,
                    'Fechou?': cliente_fechou,
                    'Valor(R$)': sefechou_valor,
                    'CEP': endereco_formatado
                }
                salvar_agendamento(agendamento)
                st.success("Visita realizada com Sucesso!")
            else:
                st.error("CEP inválido. Insira 8 dígitos numéricos.")

    # Exibir os agendamentos
    agendamentos = ler_agendamentos()
    if not agendamentos.empty:
        st.write(agendamentos)

        @st.cache_data
        def get_excel_buffer(df):
            buffer = io.BytesIO()
            df.to_excel(buffer, index=False)
            buffer.seek(0)  # Resetar o ponteiro do buffer para o início
            return buffer

        excel_buffer = get_excel_buffer(agendamentos)
        st.download_button(
            label="Download como XLSX",
            data=excel_buffer.getvalue(),  # Obter o conteúdo do buffer como bytes
            file_name="agendamentos.xlsx",
            mime="application/vnd.ms-excel"
        )
    else:
        st.write("Nenhuma visita realizada até o momento.")

    # **Botão para Sair**
    if st.button("Sair"):
        st.session_state.autenticado = False
        st.session_state.perfil_selecionado = None
        st.info("Você saiu da aplicação.")
