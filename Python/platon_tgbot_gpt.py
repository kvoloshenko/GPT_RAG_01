from telegram.ext import Application, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
from tools_00 import split_text
import os
import platon_chat_gpt as chat_gpt
from loguru import logger

logger.add("Logs/bot_debug.log", format="{time} {level} {message}", level="DEBUG", rotation="100 KB", compression="zip")

# возьмем переменные окружения из .env
load_dotenv()

# загружаем значеняи из файла .env
TOKEN = os.environ.get("TOKEN")

TEXT_BEGINNING = os.environ.get("TEXT_BEGINNING")
logger.debug(f'TEXT_BEGINNING = {TEXT_BEGINNING}')

BOT_START_REPLY = os.environ.get("BOT_START_REPLY")
logger.debug(f'BOT_START_REPLY={BOT_START_REPLY}')

print('Команда для обновления данных: ##reload##')

TEXT_END = os.environ.get("TEXT_END")
logger.debug (f'TEXT_END = {TEXT_END}')

QUESTION_FILTER = os.environ.get("QUESTION_FILTER")
if QUESTION_FILTER is None:
    QUESTION_FILTER = ""


# функция команды /start
async def start(update, context):
  await update.message.reply_text(BOT_START_REPLY)

# функция для текстовых сообщений
async def text(update, context):
    # использование update
    logger.debug('-------------------')
    logger.debug(f'{update.message.date}')
    logger.debug(f'{update.message.message_id}')
    logger.debug(f'{update.message.from_user.first_name}')
    user_name = update.message.from_user.first_name
    logger.debug(f'{update.message.from_user.id}')
    user_id = update.message.from_user.id
    logger.debug(f'{update.message.text}')

    topic = update.message.text
    topic_splited = split_text(topic, 40) # Разбиени строки переводом коретки
    print(f'text: {topic_splited}')

    question_filter_len = len (QUESTION_FILTER)
    topic_first_n = topic[:question_filter_len]

    chat_type = update.message.chat.type

    if (QUESTION_FILTER == topic_first_n) or (chat_type == 'private'):
        if topic=='##reload##':
            # обновление промта и базы знаний
            chat_gpt.PROMPT, chat_gpt.KNOWLEDGE_BASE = chat_gpt.reload_data()
            await update.message.reply_text(f'Данные обновлены!')
        else:
            reply_text = chat_gpt.answer_user_question(topic, user_name, str(user_id))
            response = TEXT_BEGINNING + '\n'
            response = response + reply_text + '\n' + TEXT_END

            await update.message.reply_text(f'{response}')
            reply_text_splited = split_text(reply_text, 40) # Разбиени строки переводом коретки
            logger.debug(f'{reply_text_splited}')
            logger.debug('-------------------')


def main():

    # точка входа в приложение
    application = Application.builder().token(TOKEN).build()
    print('Бот запущен..!')

    # добавляем обработчик команды /start
    application.add_handler(CommandHandler("start", start))

    # добавляем обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT, text))

    # запуск приложения (для остановки нужно нажать Ctrl-C)
    application.run_polling()

    print('Бот остановлен..!')


if __name__ == "__main__":
    main()