
import csv
from datetime import datetime, timedelta
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import os
import pandas as pd

app = Flask(__name__)

CSV_CONTAS = "contas.csv"
CSV_GASTOS = "gastos.csv"
CSV_USUARIOS = "usuarios.csv"
CSV_LICENCAS = "licencas.csv"
EXPORT_CSV = "gastos_mes.csv"

def verificar_usuario(numero):
    if not os.path.exists(CSV_USUARIOS):
        return False
    with open(CSV_USUARIOS, newline='', encoding='utf-8') as f:
        return any(row['whatsapp'] == numero for row in csv.DictReader(f))

def cadastrar_usuario(numero, nome):
    novo = {
        "whatsapp": numero,
        "nome": nome,
        "data_registro": datetime.now().strftime('%Y-%m-%d')
    }
    existe_header = os.path.exists(CSV_USUARIOS) and os.stat(CSV_USUARIOS).st_size > 0
    with open(CSV_USUARIOS, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["whatsapp", "nome", "data_registro"])
        if not existe_header:
            writer.writeheader()
        writer.writerow(novo)

def verificar_licenca(numero):
    if not os.path.exists(CSV_LICENCAS):
        return False
    with open(CSV_LICENCAS, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['whatsapp'] == numero and row['status'].strip().lower() == 'ativa':
                return True
    return False

def contas_vencimento_proximo():
    if not os.path.exists(CSV_CONTAS):
        return "✅ Nenhuma conta com vencimento nos próximos 7 dias."

    contas = pd.read_csv(CSV_CONTAS)
    hoje = datetime.now().date()
    contas['vencimento'] = pd.to_datetime(contas['vencimento'], errors='coerce').dt.date
    contas = contas.dropna(subset=['vencimento'])

    hoje_df = contas[contas['vencimento'] == hoje]
    amanha_df = contas[contas['vencimento'] == hoje + timedelta(days=1)]
    sete_dias_df = contas[(contas['vencimento'] > hoje + timedelta(days=1)) & 
                          (contas['vencimento'] <= hoje + timedelta(days=7))]

    linhas = []
    if not hoje_df.empty:
        linhas.append("🔔 Hoje:")
        linhas.extend([f"- 💳 {row['nome']} (R$ {row['valor']:.2f})" for _, row in hoje_df.iterrows()])
    if not amanha_df.empty:
        linhas.append("🔜 Amanhã:")
        linhas.extend([f"- 💳 {row['nome']} (R$ {row['valor']:.2f})" for _, row in amanha_df.iterrows()])
    if not sete_dias_df.empty:
        linhas.append("📆 Próximos 7 dias:")
        linhas.extend([f"- 💦 {row['nome']} (R$ {row['valor']:.2f} - vence em {(row['vencimento'] - hoje).days} dias)"
                       for _, row in sete_dias_df.iterrows()])

    return "
".join(linhas) if linhas else "✅ Nenhuma conta com vencimento nos próximos 7 dias."

@app.route('/webhook', methods=['POST'])
def webhook():
    incoming_msg = request.values.get('Body', '').strip().lower()
    numero = request.values.get('From', '').replace("whatsapp:", "")
    resp = MessagingResponse()
    msg = resp.message()

    if not verificar_licenca(numero):
        msg.body("🔒 Seu número ainda não está autorizado a usar o PoupaZap.

Para ativar sua licença, acesse:
👉 https://sualoja.com/poupazap")
        return str(resp)

    if not verificar_usuario(numero):
        if incoming_msg.startswith("me chamo"):
            nome = incoming_msg.replace("me chamo", "").strip().title()
            if nome:
                cadastrar_usuario(numero, nome)
                resposta = f"✅ Cadastro realizado com sucesso, {nome}!

(Comandos disponíveis: ifood 23,90, guardei 100, vencimentos, extrato, exportar gastos...)"
            else:
                resposta = "❌ Nome inválido. Tente novamente com: *me chamo seu nome*"
        else:
            resposta = "👋 Olá! Antes de usar o PoupaZap, por favor diga seu nome com:
*me chamo SEU NOME*"
        msg.body(resposta)
        return str(resp)

    if incoming_msg in ['oi', 'olá', 'menu', 'ajuda']:
        resposta = "👋 Bem-vindo de volta ao PoupaZap! Envie:
- ifood 23,90
- guardei 100
- extrato
- vencimentos
- exportar gastos"
    elif incoming_msg.startswith("guardei"):
        resposta = "💰 Valor guardado com sucesso!"
    elif 'vencimento' in incoming_msg:
        resposta = contas_vencimento_proximo()
    else:
        resposta = "🤖 Comando não reconhecido. Digite *menu* para ver as opções."

    msg.body(resposta)
    return str(resp)
