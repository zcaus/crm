import streamlit as st
import pandas as pd
import re
import io
import os
from datetime import datetime, timedelta

# Função para formatar valores monetários no padrão brasileiro: "R$ XXX.XXX,XX"
def format_currency_br(value):
    formatted = f"{value:,.2f}"  # Ex: 12,345.67
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"

# **Definição de Perfis, Logins e Senhas**
perfis = {
    "Cláudia Costa": {"login": "Claudia", "senha": "1501", "csv": "perfil1.csv"},
    "Evandro Alexandre": {"login": "Evandro", "senha": "0512", "csv": "perfil2.csv"},
    "Renan": {"login": "Renan", "senha": "1710", "csv": "perfil3.csv"},
    "Cauã Moreira": {"login": "Caua", "senha": "2805", "csv": "perfil4.csv"}
}

# **Inicializar Session State**
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'perfil_selecionado' not in st.session_state:
    st.session_state.perfil_selecionado = None
# Inicializa uma variável para manter o horário selecionado (hora atual - 3 horas)
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
    login = st.text_input("Login")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        perfil = autenticar(login, senha)
        if perfil:
            st.session_state.autenticado = True
            st.session_state.perfil_selecionado = perfil
            st.success(f"Bem-vindo, {perfil}!")
        else:
            st.error("Login ou senha inválidos.")

# **Interface de Cadastro e Gestão (após login)**
if st.session_state.autenticado:
    arquivo_csv = perfis[st.session_state.perfil_selecionado]["csv"]  # Arquivo CSV associado ao perfil

    # Define o cabeçalho, incluindo a coluna "Observação"
    cabecalho = "id,Data,Hora,Nome,Telefone,Fechou?,Valor(R$),CEP,Observação\n"
    if not os.path.exists(arquivo_csv):
        with open(arquivo_csv, 'w', encoding='latin1') as f:
            f.write(cabecalho)
    else:
        try:
            df_temp = pd.read_csv(arquivo_csv, encoding='latin1')
            if df_temp.empty or "id" not in df_temp.columns or "Observação" not in df_temp.columns:
                raise ValueError
        except Exception:
            with open(arquivo_csv, 'w', encoding='latin1') as f:
                f.write(cabecalho)

    # Função para ler os agendamentos com encoding especificado
    def ler_agendamentos():
        try:
            return pd.read_csv(arquivo_csv, encoding='latin1', dtype={'Telefone': str, 'CEP': str})
        except FileNotFoundError:
            return pd.DataFrame(columns=['id', 'Data', 'Hora', 'Nome', 'Telefone', 'Fechou?', 'Valor(R$)', 'CEP', 'Observação'])

    # Função para salvar um novo agendamento
    def salvar_agendamento(agendamento):
        agendamentos = ler_agendamentos()
        if agendamentos.empty:
            agendamento['id'] = 1
        else:
            agendamento['id'] = agendamentos['id'].max() + 1
        novo_df = pd.DataFrame([agendamento])
        agendamentos = pd.concat([agendamentos, novo_df], ignore_index=True)
        agendamentos.to_csv(arquivo_csv, index=False, encoding='latin1')

    # Formulário de Agendamento
    with st.form("agendamento_form"):
        col1, col2 = st.columns(2)
        data_visita = col1.date_input("Selecione a Data da Visita", format="DD/MM/YYYY")
        data_visita_formatada = data_visita.strftime('%d/%m/%Y')
        # Usa o valor armazenado (já com 3 horas a menos) para preencher o campo de hora
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
            # Atualiza o horário selecionado na session state
            st.session_state.hora_selecionada = hora_visita
            # Formatação do telefone e validação do CEP
            telefone_cliente = re.sub(r'(\d{2})(\d{4,5})(\d{4})', r'(\1) \2-\3', telefone_cliente)
            if len(endereco) == 8 and endereco.isdigit():
                endereco_formatado = "{}-{}".format(endereco[:5], endereco[5:])
                agendamento = {
                    'Data': data_visita_formatada,
                    'Hora': hora_visita_formatada,
                    'Nome': nome_cliente,
                    'Telefone': telefone_cliente,
                    'Fechou?': cliente_fechou,
                    'Valor(R$)': sefechou_valor,
                    'CEP': endereco_formatado,
                    'Observação': observacao
                }
                salvar_agendamento(agendamento)
                st.success("Visita realizada com Sucesso!")
            else:
                st.error("CEP inválido. Insira 8 dígitos numéricos.")

    # Ler e exibir os agendamentos
    agendamentos = ler_agendamentos()
    if not agendamentos.empty:
        # Aplica a formatação dos valores monetários
        if 'Valor(R$)' in agendamentos.columns:
            try:
                agendamentos['Valor(R$)'] = agendamentos['Valor(R$)'].apply(
                    lambda x: format_currency_br(
                        float(str(x).replace("R$", "").replace(" ", "").replace(".", "").replace(",", "."))
                    ) if x not in [None, ""] else ""
                )
            except Exception as e:
                st.error(f"Erro na formatação do valor: {e}")

        # Exibe o DataFrame sem a coluna "id"
        df_display = agendamentos.drop("id", axis=1)
        st.markdown("### Agendamentos")
        st.dataframe(df_display)

        # Botão para baixar XLSX (sem a coluna "id" e com a coluna "Usuário")
        @st.cache_data
        def get_excel_buffer(df):
            df_copy = df.copy()
            if "id" in df_copy.columns:
                df_copy.drop("id", axis=1, inplace=True)
            df_copy["Usuário"] = st.session_state.perfil_selecionado
            buffer = io.BytesIO()
            df_copy.to_excel(buffer, index=False)
            buffer.seek(0)
            return buffer

        excel_buffer = get_excel_buffer(agendamentos)
        st.download_button(
            label="Download como XLSX",
            data=excel_buffer.getvalue(),
            file_name="agendamentos.xlsx",
            mime="application/vnd.ms-excel"
        )
    else:
        st.write("Nenhum agendamento realizado até o momento.")

    # Botão para sair com rerun automático
    if st.button("Sair"):
        st.session_state.autenticado = False
        st.session_state.perfil_selecionado = None
        st.info("Você saiu da aplicação.")
        st.rerun()
