#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

MAIL_FROM = os.getenv('MAIL_FROM', 'form.yancodekwork@mail.ru')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', 'xwhKnwnWKUHsNbKB6PLv')
MAIL_TO = os.getenv('MAIL_TO', 'form.yancodekwork@mail.ru')
PORT = int(os.getenv('PORT', 5000))

app = Flask(__name__)
CORS(app)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATA_DIR = 'applications'
os.makedirs(DATA_DIR, exist_ok=True)


def send_email(subject, html_body, json_data, filename):
    try:
        msg = MIMEMultipart()
        msg['From'] = MAIL_FROM
        msg['To'] = MAIL_TO
        msg['Subject'] = subject
        
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        json_attachment = MIMEApplication(json_data, _subtype='json')
        json_attachment.add_header('Content-Disposition', 'attachment', filename=filename)
        msg.attach(json_attachment)
        
        with smtplib.SMTP_SSL('smtp.mail.ru', 465) as server:
            server.login(MAIL_FROM, MAIL_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Email отправлен на {MAIL_TO}")
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки email: {e}")
        return False



@app.route('/api/submit', methods=['POST', 'OPTIONS'])
def submit_application():
    
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        
        if not data or 'raw' not in data:
            return jsonify({'success': False, 'error': 'Некорректные данные'}), 400
        
        anketa_data = data['raw']
        timestamp = int(datetime.now().timestamp() * 1000)
        filename = f'application_{timestamp}.json'
        filepath = os.path.join(DATA_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(anketa_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Сохранена заявка: {filename}")
        
        answers = anketa_data['answers']
        full_name = answers['step1_general'].get('fullName', 'Без имени')
        
        subject = f"🆕 Новая заявка: {full_name}"
        html_body = format_email_html(answers, timestamp)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            json_data = f.read()
        
        email_sent = send_email(
            subject, 
            html_body, 
            json_data, 
            f"Заявка_{full_name}_{timestamp}.json"
        )
        
        if email_sent:
            logger.info("Email успешно отправлен")
        else:
            logger.warning("Email не отправлен, но заявка сохранена")
        
        return jsonify({
            'success': True,
            'message': 'Заявка успешно отправлена',
            'applicationId': timestamp
        })
        
    except Exception as e:
        logger.error(f"Ошибка обработки заявки: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



def format_email_html(answers, timestamp):
    date = datetime.fromtimestamp(timestamp / 1000).strftime('%d.%m.%Y %H:%M')
    
    monthly_expenses = answers['step3_children'].get('monthlyExpenses')
    expenses_html = f'<div class="field"><span class="label">Расходы:</span> <span class="value">{monthly_expenses:,} ₽/мес</span></div>' if monthly_expenses else ''
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; color: #333; }}
            .header {{ background: #f26649; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .section {{ margin-bottom: 20px; border-left: 3px solid #f26649; padding-left: 15px; }}
            .section h3 {{ color: #f26649; margin: 0 0 10px 0; }}
            .field {{ margin: 5px 0; }}
            .label {{ font-weight: bold; color: #68311f; }}
            .value {{ color: #333; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🆕 НОВАЯ ЗАЯВКА</h1>
            <p>📅 {date}</p>
        </div>
        <div class="content">
            <div class="section">
                <h3>👤 ОБЩИЕ СВЕДЕНИЯ</h3>
                <div class="field"><span class="label">ФИО:</span> <span class="value">{answers['step1_general'].get('fullName', 'Не указано')}</span></div>
                <div class="field"><span class="label">Регион:</span> <span class="value">{answers['step1_general'].get('region', 'Не указан')}</span></div>
                <div class="field"><span class="label">Был банкротом:</span> <span class="value">{'Да' if answers['step1_general'].get('wasBankrupt') else 'Нет'}</span></div>
            </div>
            
            <div class="section">
                <h3>👨‍👩‍👧 СЕМЬЯ</h3>
                <div class="field"><span class="label">В браке:</span> <span class="value">{'Да' if answers['step2_family'].get('isMarried') else 'Нет'}</span></div>
            </div>
            
            <div class="section">
                <h3>👶 ДЕТИ</h3>
                <div class="field"><span class="label">Количество:</span> <span class="value">{answers['step3_children'].get('childrenCount', 'Не указано')}</span></div>
                {expenses_html}
            </div>
            
            <div class="section">
                <h3>💰 ДОЛГИ</h3>
                <div class="field"><span class="label">Общая сумма:</span> <span class="value">{(answers['step4_debts'].get('totalDebt', 0)):,} ₽</span></div>
                <div class="field"><span class="label">Неспис. долги:</span> <span class="value">{answers['step4_debts'].get('nonDischargeable', 'Нет')}</span></div>
            </div>
            
            <div class="section">
                <h3>🏦 БАНКИ</h3>
                <div class="field"><span class="label">Количество:</span> <span class="value">{len(answers['step5_banks'].get('selectedBanks', []))}</span></div>
                <div class="field"><span class="value">{', '.join(answers['step5_banks'].get('selectedBanks', [])[:5])}</span></div>
            </div>
            
            <div class="section">
                <h3>💵 ДОХОДЫ</h3>
                <div class="field"><span class="label">Ежемесячный:</span> <span class="value">{(answers['step9_income'].get('monthlyIncome', 0)):,} ₽</span></div>
                <div class="field"><span class="label">Офиц. работа:</span> <span class="value">{'Да' if answers['step9_income'].get('hasOfficialJob') else 'Нет'}</span></div>
            </div>
            
            <div class="section">
                <h3>📊 РАСХОДЫ</h3>
                <div class="field"><span class="label">Просрочки:</span> <span class="value">{'Да' if answers['step10_expensesAndBehavior'].get('hasOverdue') else 'Нет'}</span></div>
            </div>
            
            <p style="margin-top: 30px; padding: 15px; background: #f9f9f9; border-left: 3px solid #f26649;">
                📎 Полные данные во вложенном JSON файле
            </p>
        </div>
    </body>
    </html>
    """
    
    return html


@app.route('/')
def index():
    return '''
    <h1>Email сервис для приёма заявок</h1>
    <p>Статус: ✅ Работает</p>
    <p>API endpoint: <code>/api/submit</code></p>
    '''


if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("🚀 Запуск email-сервиса для приёма заявок")
    logger.info(f"📧 Email от: {MAIL_FROM}")
    logger.info(f"📧 Email кому: {MAIL_TO}")
    logger.info(f"🌐 Port: {PORT}")
    logger.info(f"💾 Папка для заявок: {DATA_DIR}")
    logger.info("=" * 50)
    
    app.run(host='0.0.0.0', port=PORT, debug=False)
