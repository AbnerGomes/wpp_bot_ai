from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

persist_directory = '/app/chroma_data'
embedding = HuggingFaceEmbeddings()

vector_store = Chroma(
    embedding_function=embedding,
    persist_directory=persist_directory,
)

# Buscar os primeiros 10 documentos
docs = vector_store.get(include=["documents"], ids=None, where=None)
print(docs)