
import os
# Pegando a URL do banco via variável de ambiente
from urllib.parse import urlparse
import psycopg2


DATABASE_URL = os.environ['DATABASE_URL'] 

class dbService:

    def __init__(self):
        pass

    def get_connection(self):
        """Retorna uma conexão com o banco PostgreSQL."""
        try:
            conn = psycopg2.connect(DATABASE_URL)
            return conn
        except Exception as e:
            print("Erro ao conectar ao banco:", e)
            return None

    # Função para salvar o gasto no banco
    def salvar_gasto_postgres(self,gasto_dict,usuario):
        try:
            data = str(gasto_dict['data'])
            gasto = str(gasto_dict['gasto'])
            valor = str(gasto_dict['valor_gasto'])
            categoria = str(gasto_dict['categoria'])
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO Gastos (Gasto, valor_gasto, data, categoria, usuario)
                VALUES (%s, %s, %s, %s, %s)
            ''', (gasto,valor,data,categoria, usuario,))
            conn.commit()
            conn.close()
            return 'OK'
        except Exception as e:
            return e    