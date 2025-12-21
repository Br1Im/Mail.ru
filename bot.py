#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot

BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID', 'YOUR_CHAT_ID_HERE')
PORT = int(os.getenv('PORT', 5000))

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
CORS(app)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATA_DIR = 'applications'
os.makedirs(DATA_DIR, exist_ok=True)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    text = (
        "👋 Добро пожаловать!\n\n"
        "Это бот для приёма заявок на анализ банкротства.\n\n"
        f"Ваш Chat ID: `{chat_id}`\n\n"
        "Используйте этот ID в настройках для получения уведомлений."
    )
    bot.reply_to(message, text, parse_mode='Markdown')


@bot.message_handler(commands=['stats'])
def send_stats(message):
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
    bot.reply_to(message, f"📊 Всего заявок: {len(files)}")


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
        
        try:
            answers = anketa_data['answers']
            message_text = format_message(answers, timestamp)
            
            bot.send_message(ADMIN_CHAT_ID, message_text, parse_mode='HTML')
            
            with open(filepath, 'rb') as f:
                full_name = answers['step1_general'].get('fullName', 'Без_имени')
                bot.send_document(
                    ADMIN_CHAT_ID,
                    f,
                    caption=f"📎 Полные данные заявки",
                    visible_file_name=f"Заявка_{full_name}_{timestamp}.json"
                )
            
            logger.info(f"Заявка отправлена в Telegram")
            
        except Exception as e:
            logger.error(f"Ошибка отправки в Telegram: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Заявка успешно отправлена',
            'applicationId': timestamp
        })
        
    except Exception as e:
        logger.error(f"Ошибка обработки заявки: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def format_message(answers, timestamp):
    date = datetime.fromtimestamp(timestamp / 1000).strftime('%d.%m.%Y %H:%M')
    
    msg = f"🆕 <b>НОВАЯ ЗАЯВКА</b>\n"
    msg += f"📅 {date}\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    
    msg += f"<b>👤 ОБЩИЕ СВЕДЕНИЯ</b>\n"
    msg += f"ФИО: {answers['step1_general'].get('fullName', 'Не указано')}\n"
    msg += f"Регион: {answers['step1_general'].get('region', 'Не указан')}\n"
    msg += f"Был банкротом: {'Да' if answers['step1_general'].get('wasBankrupt') else 'Нет'}\n\n"
    
    msg += f"<b>👨‍👩‍👧 СЕМЬЯ</b>\n"
    msg += f"В браке: {'Да' if answers['step2_family'].get('isMarried') else 'Нет'}\n\n"
    
    msg += f"<b>👶 ДЕТИ</b>\n"
    msg += f"Количество: {answers['step3_children'].get('childrenCount', 'Не указано')}\n"
    if answers['step3_children'].get('monthlyExpenses'):
        msg += f"Расходы: {answers['step3_children']['monthlyExpenses']:,} ₽/мес\n"
    msg += f"\n"
    
    total_debt = answers['step4_debts'].get('totalDebt', 0)
    msg += f"<b>💰 ДОЛГИ</b>\n"
    msg += f"Общая сумма: {total_debt:,} ₽\n"
    msg += f"Неспис. долги: {answers['step4_debts'].get('nonDischargeable', 'Нет')}\n\n"
    
    banks = answers['step5_banks'].get('selectedBanks', [])
    msg += f"<b>🏦 БАНКИ ({len(banks)})</b>\n"
    for bank in banks[:5]:
        msg += f"  • {bank}\n"
    if len(banks) > 5:
        msg += f"  ... и ещё {len(banks) - 5}\n"
    msg += f"\n"
    
    msg += f"<b>💵 ДОХОДЫ</b>\n"
    msg += f"Ежемесячный: {answers['step9_income'].get('monthlyIncome', 0):,} ₽\n"
    msg += f"Офиц. работа: {'Да' if answers['step9_income'].get('hasOfficialJob') else 'Нет'}\n\n"
    
    expenses = answers['step10_expensesAndBehavior']
    msg += f"<b>📊 РАСХОДЫ</b>\n"
    msg += f"Просрочки: {'Да' if expenses.get('hasOverdue') else 'Нет'}\n\n"
    
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📎 Полные данные в прикреплённом файле"
    
    return msg


@app.route('/')
def index():
    return '''
    <h1>Бот для приёма заявок</h1>
    <p>Статус: ✅ Работает</p>
    <p>API endpoint: <code>/api/submit</code></p>
    '''


if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("🚀 Запуск бота для приёма заявок")
    logger.info(f"📱 Bot Token: {BOT_TOKEN[:10]}..." if BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE' else "📱 Bot Token: ❌ Не настроен")
    logger.info(f"👤 Admin Chat ID: {ADMIN_CHAT_ID}")
    logger.info(f"🌐 Port: {PORT}")
    logger.info(f"💾 Папка для заявок: {DATA_DIR}")
    logger.info("=" * 50)
    
    import threading
    bot_thread = threading.Thread(target=lambda: bot.polling(none_stop=True))
    bot_thread.daemon = True
    bot_thread.start()
    
    app.run(host='0.0.0.0', port=PORT, debug=False)
