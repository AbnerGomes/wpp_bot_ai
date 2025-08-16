from flask import Flask, request, jsonify

from bot.ai_bot import AIBot
from services.waha import Waha
from services.db_service import dbService
import re
from datetime import datetime

app = Flask(__name__)

def ignore_think(texto):
    # Procura a tag </think> e pega tudo que vem depois
    
    partes = re.split(r'</think>', texto, maxsplit=1)
    print(partes)
    if len(partes) > 1:
        return partes[1].strip()
    else:
        return texto.strip()  # se não tiver <think>, retorna o texto todo

def extrair_gasto_da_resposta( texto):
    try:
        data = datetime.now().strftime('%d/%m/%Y')
        print(data)
        gasto = re.search(r'Gasto:\s*([^\n]+)', texto).group(1).strip()
        print(gasto)
        valor = re.search(r'Valor:\s*R\$?\s*([\d,.]+)', texto).group(1).replace(',', '.')
        print(valor)
        # categoria = re.search(r'Categoria:\s*(.+)', texto).group(1).strip()

        # Extrai a linha da categoria
        match = re.search(r'Categoria:\s*(.+)', texto)
        if match:
            categoria_com_emoji = match.group(1).strip()

            # Remove o emoji (tudo que não for letra ou número do começo da string)
            categoria = re.sub(r'^\W+', '', categoria_com_emoji).strip()
        print(categoria)

        return {
            'gasto': gasto,
            'valor_gasto': float(valor),
            'data': datetime.strptime(data, '%d/%m/%Y').date(),
            'categoria': categoria
        }
    except Exception as e:
        print("❌ Não foi possível extrair dados:", e)
        return None
    
#endpoints    
@app.route('/chatbot/webhook', methods=['GET','POST'])
def webhook():
    data = request.json
    chat_id = data['payload']['from']
    received_message = data['payload']['body']
    is_group = '@g.us' in chat_id

    user = (data['payload']['_data']['notifyName'])

    print(chat_id)

    if is_group:
        return jsonify({'status': 'success', 'message': 'Mensagem de grupo ignorada.'}), 200

    if '81224197' in chat_id:
                usuario = 'abwgomes@gmail.com'
            
    if '80235755' in chat_id:
        usuario ='analidiacadribeiro28@gmail.com'    

    if '96634752' in chat_id:
        usuario ='bi@gmail.com' 

    if '90052767' in chat_id:
        usuario ='lulu@gmail.com'   

    if '91687931' in chat_id:
        usuario ='fernando@gmail.com' 

    waha = Waha()
    ai_bot = AIBot()

    waha.start_typing(chat_id=chat_id)
    history_messages = waha.get_history_messages(
        chat_id=chat_id,
        limit=2,
    )
    response_message = ai_bot.invoke(
        history_messages=history_messages,
        question=received_message,
        user=user,
    )

    clean_response = ignore_think(response_message)
    clean_response = clean_response.replace("[https://my-financess-app.onrender.com](https://my-financess-app.onrender.com)", "https://my-financess-app.onrender.com")

    #remove asteriscos
    clean_response = clean_response.replace('**','*')

    waha.send_message(
        chat_id=chat_id,
        message=clean_response,
    )

    try:
        if  "?" not in received_message: 
            # 🧠 Intercepta a resposta e tenta extrair os dados         

            gasto_extraido = extrair_gasto_da_resposta(clean_response)

            db = dbService()

            if gasto_extraido:
                print("📝 Salvando no PostgreSQL:", gasto_extraido)
                
                print(db.salvar_gasto_postgres(gasto_extraido,usuario))
    except Exception as e:
        print({e} )

    waha.stop_typing(chat_id=chat_id)

    return jsonify({'status': 'success'}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

