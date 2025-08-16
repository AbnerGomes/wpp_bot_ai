import os
from datetime import datetime, timedelta, date

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain_core.documents import Document

import dateparser
from dateparser.search import search_dates

import re

DATABASE_URL = os.environ['DATABASE_URL']

class AIBot:

    def __init__(self):
        print('Inicializando Optimus Grana...')
        self.__chat = ChatGroq(model='deepseek-r1-distill-llama-70b', temperature=0)

        # Configurar conexão com SQLAlchemy
        self.engine = create_engine(
            DATABASE_URL,
            echo=False
        )
        self.Session = sessionmaker(bind=self.engine)

    def __build_messages(self, history_messages, question):
        messages = []
        for message in history_messages:
            message_class = HumanMessage if message.get('fromMe') else AIMessage
            messages.append(message_class(content=message.get('body')))
        messages.append(HumanMessage(content=question))
        return messages

    def __interpretar_periodo(self, question):
        hoje = date.today()
        semana = hoje - timedelta(days=hoje.weekday() + 1)  # último domingo
        primeiro_dia_mes = hoje.replace(day=1)
        ontem = hoje - timedelta(days=1)

        if "semana passada" in question.lower():
            inicio = semana - timedelta(days=7)
            fim = semana - timedelta(days=1)
        elif "desta semana" in question.lower() or "essa semana" in question.lower():
            inicio = semana
            fim = hoje
        elif "deste mês" in question.lower() or "este mês" in question.lower() or "deste mes" in question.lower()  or "este mes" in question.lower()  or "esse mês" in question.lower()  or "esse mes" in question.lower():
            inicio = primeiro_dia_mes
            fim = hoje
        elif "ontem" in question.lower():
            inicio = fim = ontem
        elif "hoje" in question.lower():
            inicio = fim = hoje    
        else:
            # padrão: HOJE
            inicio = fim = None

        if inicio is not None and fim is not None:
            inicio= inicio.strftime('%Y-%m-%d'), 
            fim = fim.strftime('%Y-%m-%d')

        return inicio,fim

    def __parse_data_especifica(self, texto):
        meses_pt_en = {
            "janeiro": "january", "fevereiro": "february", "março": "march",
            "abril": "april", "maio": "may", "junho": "june",
            "julho": "july", "agosto": "august", "setembro": "september",
            "outubro": "october", "novembro": "november", "dezembro": "december"
        }

        texto_normalizado = texto.lower()
        # Substituir nomes de meses em português por inglês
        for pt, en in meses_pt_en.items():
            texto_normalizado = re.sub(rf'\b{pt}\b', en, texto_normalizado)

        print(texto_normalizado)

        # Tentar extrair com dateparser
        resultado = search_dates(
            texto_normalizado.replace('de',''),
            languages=["en"],
            settings={
                'PREFER_DATES_FROM': 'past',
                'RELATIVE_BASE': datetime.now(),
                'DATE_ORDER': 'DMY'
            }
        )

        if resultado:
            return resultado[0][1].date()

        # Fallback manual - detectar "dia 20 de maio"
        regex = r"dia (\d{1,2}) de (\w+)"
        match = re.search(regex, texto.lower())
        if match:
            dia = int(match.group(1))
            mes_pt = match.group(2)
            mes_en = meses_pt_en.get(mes_pt)
            if mes_en:
                try:
                    data_str = f"{dia} {mes_en} {datetime.now().year}"
                    data = datetime.strptime(data_str, "%d %B %Y")
                    if data.date() <= datetime.now().date():  # Não aceitar datas futuras
                        return data.date()
                except:
                    pass

        return None

    def __buscar_gastos_periodo(self, data_inicio, data_fim, email):
        session = self.Session()
        try:
            query = text("""
                SELECT gasto as nome,valor_gasto as valor, categoria, data
                FROM gastos
                WHERE data BETWEEN :inicio AND :fim
                  AND usuario = :usuario
                ORDER BY data, nome
            """)
            result = session.execute(query, {
                'inicio': data_inicio,
                'fim': data_fim,
                'usuario': email
            })
            gastos = [dict(row._mapping) for row in result]
        finally:
            session.close()
        return gastos

    def invoke(self, history_messages, question, user):
        hoje_str = datetime.now()
        data_inicio, data_fim = self.__interpretar_periodo(question)

        print(hoje_str)
        print(data_inicio)

        # Mapeamento de e-mail para nome
        # Original: e-mail -> nome
        nomes_usuarios = {
            'bi@gmail.com': 'Abigail Gomes',
            'abwgomes@gmail.com': 'Abner Gomes',
            'analidiacadribeiro28@gmail.com': 'Ana Lídia',
            'lulu@gmail.com' : 'Ana Luisa',
            'fernando@gmail.com' : 'Fernando Radunz'
        }

        # Invertido: nome -> e-mail
        emails_por_nome = {v: k for k, v in nomes_usuarios.items()}

        email = emails_por_nome.get(user, 'Email não encontrado')       

        if data_fim is None:
            data_especifica = self.__parse_data_especifica(question)

            if data_especifica:
                data_inicio = data_fim = data_especifica

        # Buscar gastos do PostgreSQL para o período identificado
        gastos = self.__buscar_gastos_periodo(data_inicio, data_fim, email)

        if gastos:
            context_data = "\n\n".join([
                f"Data: {g['data'].strftime('%d/%m/%Y')}\n"
                f"Gasto: {g['nome']}\nValor: R$ {g['valor']:.2f}\nCategoria: {g['categoria'] or '📦 Outros'}"
                for g in gastos
            ])
        else:
            context_data = "Não encontrei gastos registrados para esse período!"

        docs = [Document(page_content=context_data)]


        # Prompt com regras
        _temp_template = '''
        Você é Optimus Grana 🤖💸, o assistente financeiro pessoal do(a) {}.

        Seu papel é:
        1. Registrar gastos informados no dia de hoje ({}).
        2. Fornecer relatórios de gastos de qualquer data **somente quando solicitados**. 

        Regras:
        - Não invente ou resuma nada.
        - Mostre todos os gastos conforme registrados.
        - Novos gastos registrados serao sempre de hoje.
        - Sempre que o(a) usuário(a) informar um gasto, responda exatamente assim:

        Gasto adicionado com Sucesso ! ✅🤝🏾


        Gasto: 

        Valor: R$

        Categoria:, dentre as seguintes:

        💰 Dívidas

        🚗 Mobilidade

        🍽️ Alimentação

        🏥 Saúde

        📚 Educação

        🎉 Entretenimento

        📦 Outros (caso não seja possível classificar em nenhuma das anteriores).

        - Voce fornece relatorios de gastos de dias anteriores, mas..
        - quando usuario tentar registrar um novo gasto para datas anteriores, diga:

        > "Não consigo registrar gastos de dias anteriores. Para isso, use o app ou acesse: https://my-financess-app.onrender.com". 
        
        Quando listar dados:
        - Liste todos os gastos com nome, valor e categoria.
        - Categorias:
        💰 Dívidas, 🚗 Mobilidade, 🍽️ Alimentação, 🏥 Saúde, 📚 Educação, 🎉 Entretenimento, 📦 Outros
        - (IMPORTANTE) Quando um relatorio for solicitado, NUNCA responda somente com o valor total de gastos, mas sim com cada gasto com sua descricao categoria e valor (se quiser pode separar por categorias)
        
        Usuários conhecidos:
        - 'bi@gmail.com' = Abigail Gomes
        - 'abwgomes@gmail.com' = Abner Gomes
        - 'analidiacadribeiro28@gmail.com' = Ana Lídia
        - 'lulu@gmail.com' = Ana Luisa
        - 'fernando@gmail.com' = Luiz Fernando

        🎭 Estilo de Resposta:
        - Use um tom engraçado, leve e descontraído (mas sem forçar).
        - Seja sempre claro, direto e útil.
        - Cumprimente o(a) usuário(a) mencionando seu nome e o seu (Optimus Grana) em algumas respostas.
        

        '''.format(user,hoje_str)

        SYSTEM_TEMPLATE = _temp_template + '''
        <context>
        {context}
        </context>
        '''

        # Montar e invocar cadeia do LangChain
        question_answering_prompt = ChatPromptTemplate.from_messages([
            ('system', SYSTEM_TEMPLATE),
            MessagesPlaceholder(variable_name='messages'),
        ])
        document_chain = create_stuff_documents_chain(self.__chat, question_answering_prompt)

        response = document_chain.invoke({
            'context': docs,
            'messages': self.__build_messages(history_messages, question),
        })

        return response
