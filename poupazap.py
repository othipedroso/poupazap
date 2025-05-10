
import csv
from datetime import datetime, timedelta
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import os
import pandas as pd

app = Flask(__name__)

CSV_CONTAS = "contas.csv"
CSV_GASTOS = "gastos.csv"
EXPORT_CSV = "gastos_mes.csv"

def classificar_categoria(descricao):
    descricao = descricao.lower()
    if "ifood" in descricao or "ubereats" in descricao:
        return "restaurante"
    elif "farm" in descricao or "drog" in descricao:
        return "farmácia"
    elif "mercado" in descricao or "carrefour" in descricao or "extra" in descricao:
        return "mercado"
    elif "gas" in descricao or "posto" in descricao:
        return "combustível"
    else:
        return "outros"

def salvar_gasto_simples(texto):
    partes = texto.split()
    if len(partes) < 2:
        return "❌ Formato inválido. Tente: ifood 23,90"

    descricao = " ".join(partes[:-1])
    valor_texto = partes[-1].replace(",", ".")
    try:
        valor = float(valor_texto)
    except:
        return "❌ Valor inválido. Ex: ifood 23,90"

    categoria = classificar_categoria(descricao)
    data = datetime.now().strftime('%Y-%m-%d')

    with open(CSV_GASTOS, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if os.stat(CSV_GASTOS).st_size == 0:
            writer.writerow(['data', 'descricao', 'valor', 'categoria'])
        writer.writerow([data, descricao, valor, categoria])

    return f"✅ Gasto registrado: {descricao.title()} - R$ {valor:.2f} ({categoria})"

def salvar_poupanca(texto):
    partes = texto.split()
    if len(partes) != 2:
        return "❌ Use o formato: guardei 100"

    valor_texto = partes[1].replace(",", ".")
    try:
        valor = float(valor_texto)
    except:
        return "❌ Valor inválido. Ex: guardei 100"

    data = datetime.now().strftime('%Y-%m-%d')
    with open(CSV_GASTOS, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if os.stat(CSV_GASTOS).st_size == 0:
            writer.writerow(['data', 'descricao', 'valor', 'categoria'])
        writer.writerow([data, 'poupança', valor, 'poupança'])

    return f"💰 Valor poupado: R$ {valor:.2f} registrado com sucesso."

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

    resposta = "📅 Contas com vencimento:


    if not hoje_df.empty:
        resposta += "🔔 Hoje:
" + "\n".join(
            f"- 💳 {row['nome']} (R$ {row['valor']:.2f})" for _, row in hoje_df.iterrows()
        ) + "\n"
    if not amanha_df.empty:
        resposta += "\n🔜 Amanhã:
" + "\n".join(
            f"- 💳 {row['nome']} (R$ {row['valor']:.2f})" for _, row in amanha_df.iterrows()
        ) + "\n"
    if not sete_dias_df.empty:
        resposta += "\n📆 Próximos 7 dias:
" + "\n".join(
            f"- 💦 {row['nome']} (R$ {row['valor']:.2f} - vence em {(row['vencimento'] - hoje).days} dias)"
            for _, row in sete_dias_df.iterrows()
        ) + "\n"

    return resposta.strip() if resposta.strip() != "📅 Contas com vencimento:" else "✅ Nenhuma conta com vencimento nos próximos 7 dias."

def total_gasto_mes(categoria=None):
    if not os.path.exists(CSV_GASTOS):
        return "❌ Nenhum gasto registrado ainda."

    df = pd.read_csv(CSV_GASTOS)
    if df.empty:
        return "✅ Nenhum gasto registrado neste mês."
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df = df.dropna(subset=['data'])
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year
    df_mes = df[(df['data'].dt.month == mes_atual) & (df['data'].dt.year == ano_atual)]

    if categoria:
        df_cat = df_mes[df_mes['categoria'].str.lower() == categoria.lower()]
        total = df_cat['valor'].sum()
        return f"📊 Total em *{categoria.title()}* no mês: R$ {total:.2f}" if not df_cat.empty else f"📊 Nenhum gasto registrado em *{categoria.title()}*."
    else:
        total = df_mes['valor'].sum()
        return f"📊 Total de gastos em {datetime.now().strftime('%B/%Y')}: R$ {total:.2f}"

def exportar_gastos_mes():
    if not os.path.exists(CSV_GASTOS):
        return "❌ Nenhum gasto registrado ainda."

    df = pd.read_csv(CSV_GASTOS)
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df = df.dropna(subset=['data'])
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year
    df_mes = df[(df['data'].dt.month == mes_atual) & (df['data'].dt.year == ano_atual)]

    if df_mes.empty:
        return "✅ Nenhum gasto registrado neste mês."

    df_mes.to_csv(EXPORT_CSV, index=False)
    return f"Gastos do mês exportados para '{EXPORT_CSV}'."

def menu_principal():
    return (
        "👋 Olá! Eu sou o *PoupaZap* — seu bot de controle financeiro!

"
        "📌 Comandos disponíveis:
"
        "• *ifood 23,90* → Registrar um gasto
"
        "• *guardei 100* → Registrar poupança
"
        "• *vencimentos* → Ver contas a vencer
"
        "• *extrato* ou *extrato farmácia* → Total gasto no mês (geral ou por categoria)
"
        "• *exportar gastos* → Gerar CSV com gastos do mês
"
        "• *ajuda* ou *menu* → Ver este menu novamente
"
    )

@app.route('/webhook', methods=['POST'])
def webhook():
    incoming_msg = request.values.get('Body', '').strip().lower()
    resp = MessagingResponse()
    msg = resp.message()

    if incoming_msg in ['oi', 'olá', 'menu', 'ajuda']:
        resposta = menu_principal()
    elif incoming_msg.startswith("guardei"):
        resposta = salvar_poupanca(incoming_msg)
    elif 'vencimento' in incoming_msg:
        resposta = contas_vencimento_proximo()
    elif 'exportar' in incoming_msg and 'gastos' in incoming_msg:
        resposta = exportar_gastos_mes()
    elif incoming_msg.startswith("extrato"):
        partes = incoming_msg.split()
        if len(partes) == 2:
            resposta = total_gasto_mes(categoria=partes[1])
        else:
            resposta = total_gasto_mes()
    elif any(c.isdigit() for c in incoming_msg) and not incoming_msg.startswith("guardei"):
        resposta = salvar_gasto_simples(incoming_msg)
    else:
        resposta = "🤖 Comando não reconhecido. Digite *menu* para ver as opções."

    msg.body(resposta)
    return str(resp)
