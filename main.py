# Импортируем необходимые классы.
import logging
import datetime as dt
from telegram import (
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
    Update,
)

from telegram.ext import Updater, MessageHandler, Filters, Defaults
from telegram.ext import CallbackContext, CommandHandler

from modules.prepared_answers import *
from modules.start_dialogs import StartDialog
from modules.smart_timer import *
from tools.tools import get_from_env

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')


def unknown(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Извините, я не понял эту команду.")


def help_msg(update: Update, context: CallbackContext):
    update.message.reply_text(HELP_MSG)


def echo(update: Update, context: CallbackContext):
    date: dt.datetime = update.message.date
    print(date, end=' - ')
    print(date.hour, date.tzinfo)
    print(update.message.location)
    update.message.reply_text(update.message.text)


def main():
    updater = Updater(get_from_env('TOKEN'),
                      use_context=True, defaults=Defaults(run_async=True))

    dp = updater.dispatcher

    dp.add_handler(StartDialog())

    dp.add_handler(CommandHandler("set", set_timer,
                                  pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))

    # dp.add_handler(CommandHandler("unset", unset_timer,
    #                               pass_chat_data=True))
    dp.add_handler(CommandHandler("help", help_msg))

    dp.add_handler(MessageHandler(Filters.command, unknown))

    dp.add_handler(MessageHandler(Filters.text, echo))
    # dp.add_handler(MessageHandler(Filters.location, Location.add_location))
    updater.start_polling()
    # Ждём завершения приложения.
    # (например, получения сигнала SIG_TERM при нажатии клавиш Ctrl+C)
    updater.idle()


# Запускаем функцию main() в случае запуска скрипта.
if __name__ == '__main__':
    main()
