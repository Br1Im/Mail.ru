#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import urllib.request
import zipfile

BOT_TOKEN = os.getenv('BOT_TOKEN', '7502763053:AAEEDOJLKFDjKVxOq_1yqAgxxq6LWjVjn7s')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID', 'YOUR_CHAT_ID_HERE')
PORT = int(os.getenv('PORT', 5000))
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')  # Для Render: https://your-app.onrender.com

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
CORS(app)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATA_DIR = 'applications'
USERS_FILE = 'users.json'
os.makedirs(DATA_DIR, exist_ok=True)


def load_users():
    """Загружает список подписчиков из переменной окружения"""
    users_str = os.getenv('SUBSCRIBERS', '')
    if users_str:
        try:
            return json.loads(users_str)
        except:
            pass
    return []


def save_users_to_env(users):
    """Сохраняет список подписчиков (для локального использования)"""
    # На Render нужно вручную обновить переменную SUBSCRIBERS через UI
    logger.info(f"📝 Текущие подписчики: {users}")
    logger.info(f"💡 Добавьте в Environment на Render: SUBSCRIBERS={json.dumps(users)}")


def save_user(chat_id):
    users = load_users()
    if chat_id not in users:
        users.append(chat_id)
        save_users_to_env(users)
        logger.info(f"✅ Добавлен новый пользователь: {chat_id}")
        logger.info(f"⚠️ ВАЖНО: Обновите переменную SUBSCRIBERS на Render!")
        logger.info(f"   Значение: {json.dumps(users)}")
    return len(users)


def download_fonts_if_needed():
    """Автоматически скачивает шрифты DejaVu если их нет"""
    fonts_needed = ['DejaVuSans.ttf', 'DejaVuSans-Bold.ttf']
    
    # Проверяем, есть ли уже шрифты
    if all(os.path.exists(font) for font in fonts_needed):
        logger.info("✓ Шрифты DejaVu уже установлены")
        return
    
    logger.info("Шрифты не найдены, начинаю загрузку...")
    
    try:
        DEJAVU_URL = 'https://github.com/dejavu-fonts/dejavu-fonts/releases/download/version_2_37/dejavu-fonts-ttf-2.37.zip'
        zip_path = 'dejavu_fonts.zip'
        
        # Скачиваем
        logger.info("Скачивание шрифтов DejaVu...")
        urllib.request.urlretrieve(DEJAVU_URL, zip_path)
        
        # Распаковываем
        logger.info("Распаковка...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for font in fonts_needed:
                font_path = f'dejavu-fonts-ttf-2.37/ttf/{font}'
                try:
                    with zip_ref.open(font_path) as source:
                        with open(font, 'wb') as target:
                            target.write(source.read())
                    logger.info(f"✓ {font} установлен")
                except KeyError:
                    logger.warning(f"Шрифт {font} не найден в архиве")
        
        # Удаляем архив
        os.remove(zip_path)
        logger.info("✅ Шрифты успешно установлены!")
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке шрифтов: {e}")
        logger.warning("Будет использован системный шрифт (возможны проблемы с кириллицей)")


def generate_pdf(answers, timestamp):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    
    # Регистрируем шрифт с поддержкой кириллицы
    try:
        pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'))
        font_name = 'DejaVuSans'
        font_name_bold = 'DejaVuSans-Bold'
    except:
        # Если DejaVu не найден, используем Arial Unicode MS или другой системный шрифт
        try:
            pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
            pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
            font_name = 'Arial'
            font_name_bold = 'Arial-Bold'
        except:
            # В крайнем случае используем Helvetica (без кириллицы)
            font_name = 'Helvetica'
            font_name_bold = 'Helvetica-Bold'
    
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=font_name_bold,
        fontSize=18,
        textColor=colors.HexColor('#f26649'),
        spaceAfter=20,
        alignment=1
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName=font_name_bold,
        fontSize=14,
        textColor=colors.HexColor('#f26649'),
        spaceAfter=10,
        spaceBefore=15
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        textColor=colors.HexColor('#68311f')
    )
    
    date = datetime.fromtimestamp(timestamp / 1000).strftime('%d.%m.%Y %H:%M')
    
    story.append(Paragraph("ЗАЯВКА НА АНАЛИЗ БАНКРОТСТВА", title_style))
    story.append(Paragraph(f"Дата: {date}", normal_style))
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("1. ОБЩИЕ СВЕДЕНИЯ", heading_style))
    story.append(Paragraph(f"<b>ФИО:</b> {answers['step1_general'].get('fullName', 'Не указано')}", normal_style))
    story.append(Paragraph(f"<b>Регион:</b> {answers['step1_general'].get('region', 'Не указан')}", normal_style))
    story.append(Paragraph(f"<b>Был банкротом:</b> {'Да' if answers['step1_general'].get('wasBankrupt') else 'Нет'}", normal_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("2. СЕМЕЙНОЕ ПОЛОЖЕНИЕ", heading_style))
    story.append(Paragraph(f"<b>В браке:</b> {'Да' if answers['step2_family'].get('isMarried') else 'Нет'}", normal_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("3. ДЕТИ", heading_style))
    story.append(Paragraph(f"<b>Количество:</b> {answers['step3_children'].get('childrenCount', 'Не указано')}", normal_style))
    if answers['step3_children'].get('monthlyExpenses'):
        story.append(Paragraph(f"<b>Расходы:</b> {answers['step3_children']['monthlyExpenses']:,} ₽/мес", normal_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("4. ДОЛГИ", heading_style))
    total_debt = answers['step4_debts'].get('totalDebt', 0)
    story.append(Paragraph(f"<b>Общая сумма:</b> {total_debt:,} ₽", normal_style))
    story.append(Paragraph(f"<b>Неспис. долги:</b> {answers['step4_debts'].get('nonDischargeable', 'Нет')}", normal_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("5. БАНКИ", heading_style))
    banks = answers['step5_banks'].get('selectedBanks', [])
    for bank in banks:
        story.append(Paragraph(f"• {bank}", normal_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("6. ДОХОДЫ", heading_style))
    story.append(Paragraph(f"<b>Ежемесячный:</b> {answers['step9_income'].get('monthlyIncome', 0):,} ₽", normal_style))
    story.append(Paragraph(f"<b>Офиц. работа:</b> {'Да' if answers['step9_income'].get('hasOfficialJob') else 'Нет'}", normal_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("7. РАСХОДЫ", heading_style))
    expenses = answers['step10_expensesAndBehavior']
    story.append(Paragraph(f"<b>Просрочки:</b> {'Да' if expenses.get('hasOverdue') else 'Нет'}", normal_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer


@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    save_user(chat_id)
    
    text = (
        "👋 Добро пожаловать!\n\n"
        "Это бот для приёма заявок на анализ банкротства.\n\n"
        "Вы будете получать все новые заявки автоматически!"
    )
    bot.reply_to(message, text)


@bot.message_handler(commands=['stats'])
def send_stats(message):
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
    users = load_users()
    bot.reply_to(message, f"📊 Всего заявок: {len(files)}\n👥 Подписчиков: {len(users)}")


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
        
        # Сохраняем заявку с chat_id всех текущих пользователей
        anketa_data['subscribers'] = load_users()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(anketa_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Сохранена заявка: {filename}")
        
        users = load_users()
        logger.info(f"Отправка заявки {len(users)} подписчикам")
        
        try:
            answers = anketa_data['answers']
            message_text = format_message(answers, timestamp)
            full_name = answers['step1_general'].get('fullName', 'Без_имени')
            
            pdf_buffer = generate_pdf(answers, timestamp)
            
            sent_count = 0
            failed_count = 0
            
            for user_id in users:
                try:
                    bot.send_message(user_id, message_text, parse_mode='HTML')
                    
                    pdf_buffer.seek(0)
                    bot.send_document(
                        user_id,
                        pdf_buffer,
                        caption=f"📎 Заявка в PDF формате",
                        visible_file_name=f"Заявка_{full_name}_{timestamp}.pdf"
                    )
                    
                    with open(filepath, 'rb') as f:
                        bot.send_document(
                            user_id,
                            f,
                            caption=f"📎 Данные в JSON формате",
                            visible_file_name=f"Заявка_{full_name}_{timestamp}.json"
                        )
                    
                    sent_count += 1
                    logger.info(f"Заявка отправлена пользователю {user_id}")
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Ошибка отправки пользователю {user_id}: {e}")
            
            logger.info(f"Заявка отправлена: успешно {sent_count}, ошибок {failed_count}")
            
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


@app.route('/<token>', methods=['POST'])
def webhook(token):
    """Обработчик webhook для Telegram"""
    if token == BOT_TOKEN and request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return '', 403


if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("🚀 Запуск бота для приёма заявок")
    
    # Скачиваем шрифты если нужно
    download_fonts_if_needed()
    
    logger.info(f"📱 Bot Token: {BOT_TOKEN[:10]}..." if BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE' else "📱 Bot Token: ❌ Не настроен")
    logger.info(f"👥 Подписчиков: {len(load_users())}")
    logger.info(f"🌐 Port: {PORT}")
    logger.info(f"💾 Папка для заявок: {DATA_DIR}")
    
    # Определяем режим работы
    if WEBHOOK_URL:
        # Webhook режим для продакшена (Render)
        logger.info(f"🌐 Режим: Webhook")
        logger.info(f"🔗 Webhook URL: {WEBHOOK_URL}/{BOT_TOKEN}")
        
        # Удаляем старый webhook и устанавливаем новый
        bot.remove_webhook()
        import time
        time.sleep(1)
        bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
        logger.info("✅ Webhook установлен")
    else:
        # Polling режим для локальной разработки
        logger.info(f"🌐 Режим: Polling (локальная разработка)")
        bot.remove_webhook()
        
        import threading
        bot_thread = threading.Thread(target=lambda: bot.polling(none_stop=True))
        bot_thread.daemon = True
        bot_thread.start()
        logger.info("✅ Polling запущен")
    
    logger.info("=" * 50)
    app.run(host='0.0.0.0', port=PORT, debug=False)
