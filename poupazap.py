import csv
from datetime import datetime, timedelta
from flask import Flask, request, send_file
import os
import pandas as pd

app = Flask(__name__)

CSV_CONTAS = "contas.csv"
CSV_GASTOS = "gastos.csv"
EXPORT_CSV = "gastos_mes.csv"

def ler_contas():
    if not os.path.exists(CSV_CONTAS):
        return []
    with open(CSV_CONTAS, newline='', encoding='utf-8') as csvfile:
        return list(csv.DictReader(csvfile))

def contas_vencimento_proximo():
    contas = ler_contas()
    hoje = datetime.now().date()
    hoje_df = []
    amanha_df = []
    sete_dias_df = []

    for conta in contas:
        try:
            vencimento = datetime.strptime(conta['vencimento'], '%Y-%m-%d').date()
            conta['vencimento'] = vencimento
            conta['valor'] = float(conta['valor'])

            if vencimento == hoje:
                hoje_df.append(conta)
            elif vencimento == hoje + timedelta(days=1):
                amanha_df.append(conta)
            elif hoje + timedelta(days=1) < vencimento <= hoje + timedelta(days=7):
                sete_dias_df.append(conta)
        except Exception as e:
            continue

    resposta = "📅 Contas com vencimento:\n\n"

    if hoje_df:
        resposta += "🔔 Hoje:\n"
        for row in hoje_df:
            resposta += f"- 💳 {row['nome']} (R$ {row['valor']:.2f})\n"
    if amanha_df:
        resposta += "\n🔜 Amanhã:\n"
        for row in amanha_df:
            resposta += f"- 💳 {row['nome']} (R$ {row['valor']:.2f})\n"
    if sete_dias_df:
        resposta += "\n📆 Próximos 7 dias:\n"
        for row in sete_dias_df:
            dias = (row['vencimento'] - hoje).days
            resposta += f"- 💦 {row['nome']} (R$ {row['valor']:.2f} - vence em {dias} dias)\n"

    if resposta.strip() == "📅 Contas com vencimento:":
        resposta = "✅ Nenhuma conta com vencimento nos próximos 7 dias."

    return resposta.strip()

def exportar_gastos_mes():
    if not os.path.exists(CSV_GASTOS):
        return "❌ Nenhum gasto registrado ainda."

    df = pd.read_csv(CSV_GASTOS)
    df['data'] = pd.to_datetime(df['data'])
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year
    df_mes = df[(df['data'].dt.month == mes_atual) & (df['data'].dt.year == ano_atual)]

    if df_mes.empty:
        return "✅ Nenhum gasto registrado neste mês."

    df_mes.to_csv(EXPORT_CSV, index=False)
    return f"Gastos do mês exportados para '{EXPORT_CSV}'."

@app.route('/webhook', methods=['POST'])
def webhook():
    incoming_msg = request.values.get('Body', '').strip().lower()

    if 'vencimento' in incoming_msg:
        resposta = contas_vencimento_proximo()
    elif 'exportar' in incoming_msg and 'gastos' in incoming_msg:
        resposta = exportar_gastos_mes()
    else:
        resposta = "🤖 Comando não reconhecido. Tente:\n- 'vencimentos'\n- 'exportar gastos'"

    return resposta, 200

@app.route('/download_gastos_mes', methods=['GET'])
def download_gastos():
    if os.path.exists(EXPORT_CSV):
        return send_file(EXPORT_CSV, as_attachment=True)
    return "Arquivo não encontrado", 404

if __name__ == '__main__':
    app.run(debug=True)
