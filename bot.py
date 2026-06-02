import logging
import uuid
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import config
import database

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Дата тестирования
TEST_START = datetime(2026, 7, 1, 0, 0, 0)  # 01.07.2026 00:00
TEST_DURATION_DAYS = 3

# Состояния диалога
NICKNAME, FRIEND_CODE, DEVICE_NAME, ANDROID_VERSION = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 *Добро пожаловать в тестирование мода Among Us!*\n\n"
        "Чтобы получить ключ доступа, используй команду /getkey\n"
        "Ты введешь:\n"
        "• Никнейм в игре\n"
        "• Френдкод\n"
        "• Имя устройства\n"
        "• Версию Android\n\n"
        f"Осталось мест: {config.MAX_USERS - database.get_tester_count()}\n\n"
        "📅 *Тестирование пройдёт с 01 по 03 июля 2026 года*\n"
        "За час до начала я пришлю напоминание!",
        parse_mode='Markdown'
    )

async def getkey_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    
    if database.user_exists_by_tg(tg_id):
        await update.message.reply_text("❌ Ты уже получил ключ! Один ключ на человека.")
        return ConversationHandler.END
    
    if database.get_tester_count() >= config.MAX_USERS:
        await update.message.reply_text("😞 Набор тестировщиков закончен! Мест больше нет.")
        return ConversationHandler.END
    
    await update.message.reply_text("Введи свой *никнейм в Among Us*:", parse_mode='Markdown')
    return NICKNAME

async def get_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nickname'] = update.message.text.strip()
    await update.message.reply_text("Введи свой *френдкод* (код друга из Among Us):", parse_mode='Markdown')
    return FRIEND_CODE

async def get_friend_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    friend_code = update.message.text.strip()
    
    if database.friend_code_exists(friend_code):
        await update.message.reply_text("❌ Этот френдкод уже используется другим тестировщиком.")
        return FRIEND_CODE
    
    context.user_data['friend_code'] = friend_code
    await update.message.reply_text("Введи *имя своего устройства* (например: Xiaomi Redmi Note 10):", parse_mode='Markdown')
    return DEVICE_NAME

async def get_device_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    device_name = update.message.text.strip()
    
    if database.device_exists(device_name):
        await update.message.reply_text("❌ Это устройство уже зарегистрировано для другого тестировщика.")
        return DEVICE_NAME
    
    context.user_data['device_name'] = device_name
    await update.message.reply_text("Введи *версию Android* (например: 12, 13, 14, 15):", parse_mode='Markdown')
    return ANDROID_VERSION

async def get_android_version(update: Update, context: ContextTypes.DEFAULT_TYPE):
    android_version = update.message.text.strip()
    
    # Генерируем ключ
    license_key = str(uuid.uuid4())[:8].upper()
    
    # Сохраняем
    tg_id = update.effective_user.id
    tg_username = update.effective_user.username or "без_юзернейма"
    
    database.register_tester(
        tg_id, tg_username,
        context.user_data['nickname'],
        context.user_data['friend_code'],
        context.user_data['device_name'],
        license_key
    )
    
    # Обновляем версию Android в БД (отдельным запросом, т.к. в register_tester нет этого поля)
    import sqlite3
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE testers SET android_version=? WHERE tg_id=?", (android_version, tg_id))
    conn.commit()
    conn.close()
    
    # Отправляем ключ
    await update.message.reply_text(
        f"✅ *Ты зарегистрирован!*\n\n"
        f"📱 Устройство: {context.user_data['device_name']}\n"
        f"🤖 Android: {android_version}\n"
        f"🎮 Никнейм: {context.user_data['nickname']}\n"
        f"🔑 Френдкод: {context.user_data['friend_code']}\n\n"
        f"*Твой ключ:* `{license_key}`\n\n"
        f"📅 Тестирование: 01-03 июля 2026\n"
        f"За час до старта я пришлю напоминание!\n\n"
        f"Спасибо за тестирование! 🙌",
        parse_mode='Markdown'
    )
    
    # Уведомление админу
    await context.bot.send_message(
        chat_id=config.ADMIN_ID,
        text=f"🆕 *Новый тестировщик!*\n"
             f"👤 @{tg_username} (ID: {tg_id})\n"
             f"🎮 {context.user_data['nickname']}\n"
             f"🔑 {context.user_data['friend_code']}\n"
             f"📱 {context.user_data['device_name']}\n"
             f"🤖 Android {android_version}\n"
             f"🔐 Ключ: `{license_key}`\n"
             f"📊 Всего: {database.get_tester_count()}/{config.MAX_USERS}",
        parse_mode='Markdown'
    )
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Регистрация отменена.")
    return ConversationHandler.END

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    time_left = TEST_START - now
    
    if now >= TEST_START:
        days_passed = (now - TEST_START).days
        if days_passed <= TEST_DURATION_DAYS:
            await update.message.reply_text(f"📅 *Тестирование идёт!*\nДень {days_passed + 1} из {TEST_DURATION_DAYS}", parse_mode='Markdown')
        else:
            await update.message.reply_text("📅 *Тестирование завершено!* Спасибо всем участникам!", parse_mode='Markdown')
        return
    
    days = time_left.days
    hours = time_left.seconds // 3600
    
    await update.message.reply_text(
        f"📅 *До начала тестирования:*\n"
        f"⏳ {days} дн. {hours} час.\n"
        f"🗓 Дата: {TEST_START.strftime('%d.%m.%Y %H:%M')}\n"
        f"📊 Участников: {database.get_tester_count()}/{config.MAX_USERS}",
        parse_mode='Markdown'
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID:
        await update.message.reply_text("⛔ Только для администратора.")
        return
    
    total = database.get_tester_count()
    by_version = database.get_tester_count_by_android_version()
    
    msg = f"📊 *Статистика:*\nВсего: {total}\n\n*По версиям Android:*\n"
    for version, count in by_version:
        msg += f"• Android {version}: {count}\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID:
        await update.message.reply_text("⛔ Только для администратора.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Пример: /broadcast Текст сообщения")
        return
    
    message = " ".join(context.args)
    tg_ids = database.get_all_tester_tg_ids()
    
    success = 0
    for tg_id in tg_ids:
        try:
            await context.bot.send_message(chat_id=tg_id, text=f"📢 *Объявление от организатора:*\n{message}", parse_mode='Markdown')
            success += 1
            await asyncio.sleep(0.05)
        except:
            pass
    
    await update.message.reply_text(f"✅ Рассылка завершена: {success}/{len(tg_ids)}")

async def list_testers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID:
        await update.message.reply_text("⛔ Только для администратора.")
        return
    
    import sqlite3
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT nickname, friend_code, device_name, android_version, license_key FROM testers")
    testers = c.fetchall()
    conn.close()
    
    if not testers:
        await update.message.reply_text("Пока нет тестировщиков.")
        return
    
    msg = "📋 *Список тестировщиков:*\n\n"
    for idx, (nick, code, device, android, key) in enumerate(testers, 1):
        msg += f"{idx}. {nick}\n   🔑{code} | 🤖{android}\n   📱{device} | `{key}`\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

# Функция для рассылки за час до теста (запускать отдельно или через job_queue)
async def notify_test_start(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    time_left = TEST_START - now
    
    if 0 < time_left.total_seconds() <= 3600:
        tg_ids = database.get_all_tester_tg_ids()
        for tg_id in tg_ids:
            try:
                await context.bot.send_message(
                    chat_id=tg_id,
                    text="⏰ *ВНИМАНИЕ!*\n\nТестирование мода Among Us начнётся через **1 час**!\n\n"
                         "Подготовьте свои устройства, зайдите в игру и ждите дальнейших инструкций.\n\n"
                         "Удачи всем! 🎮",
                    parse_mode='Markdown'
                )
                await asyncio.sleep(0.05)
            except:
                pass
        logging.info("Напоминание о старте разослано")

def main():
    database.init_db()
    
    app = Application.builder().token(config.TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('getkey', getkey_start)],
        states={
            NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nickname)],
            FRIEND_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_friend_code)],
            DEVICE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_device_name)],
            ANDROID_VERSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_android_version)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('status', status))
    app.add_handler(CommandHandler('stats', stats))
    app.add_handler(CommandHandler('list', list_testers))
    app.add_handler(CommandHandler('broadcast', broadcast))
    
    # Ежечасная проверка на отправку напоминания
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(notify_test_start, interval=3600, first=10)
    
    print("🤖 Бот запущен... Дата теста:", TEST_START.strftime('%d.%m.%Y'))
    app.run_polling()

if __name__ == '__main__':
    main()
