import os
import shutil
from sqlalchemy import create_engine, Column, String, Float, Date, select,Integer
from sqlalchemy.orm import declarative_base, Session
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


# Configuração do SQLAlchemy
Base = declarative_base()

class Gasto(Base):
    __tablename__ = 'gastos'
    id = Column(Integer, primary_key=True)  # <- chave primária
    gasto = Column(String)
    valor_gasto = Column(Float)
    data = Column(Date)
    categoria = Column(String)

# Conexão com o PostgreSQL via SQLAlchemy
DATABASE_URL = os.environ['DATABASE_URL']
engine = create_engine(DATABASE_URL)

# persist_directory = '/app/chroma_data'

# # ⚠️ Remove tudo que houver no diretório de persistência
# if os.path.exists(persist_directory):
#     shutil.rmtree(persist_directory)

# Iniciar sessão
with Session(engine) as session:
    stmt = select(Gasto)
    result = session.scalars(stmt).all()

    # Criar documentos LangChain
    docs = []
    for row in result:
        content = (
            f"Gasto: {row.gasto}\n"
            f"Valor: R$ {row.valor_gasto:.2f}\n"
            f"Data: {row.data.strftime('%d/%m/%Y')}\n"
            f"Categoria: {row.categoria}"
        )
        docs.append(Document(page_content=content, metadata={"source": "tabela_gastos"}))
        print(f"Gasto: {row.gasto}\n")
        print(f"Valor: R$ {row.valor_gasto:.2f}\n")
        print(f"Data: {row.data.strftime('%d/%m/%Y')}\n")
# Quebra em chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)
chunks = text_splitter.split_documents(docs)

# Persistência no ChromaDB
persist_directory = '/app/chroma_data'

embedding = HuggingFaceEmbeddings()
vector_store = Chroma(
    embedding_function=embedding,
    persist_directory=persist_directory,
)
# vector_store.delete_collection()
# vector_store.initialize()

vector_store.add_documents(chunks)
