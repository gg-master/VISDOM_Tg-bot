import logging

from telegram import Update
from telegram.ext import (
    CommandHandler, Updater, MessageHandler, Filters, Defaults
)

from modules.restore import Restore
from modules.start_dialogs import StartDialog, PatronageJob
from modules.settings_dialogs import SettingsDialog
from modules.notification_dailogs import PillTakingDialog, DataCollectionDialog
from modules.timer import *
from tools.tools import get_from_env
from tools.prepared_answers import *

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')


def unknown(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Извините, я не понял эту команду.")


def help_msg(update: Update, context: CallbackContext):
    update.message.reply_text("Справка")


def echo(update: Update, context: CallbackContext):
    date: dt.datetime = update.message.date
    print(date, end=' - ')
    print(date.hour, date.tzinfo)
    print(update.message.location)
    print(update.message.chat_id, '-', update.effective_user.id, '-', update.effective_chat.id)
    update.message.reply_text(update.message.text)


def main():
    # chat_id = 721698752
    updater = Updater(get_from_env('TOKEN'),
                      use_context=True, defaults=Defaults(run_async=True))

    dp = updater.dispatcher

    # Восстановление уведомлений после перезапуска бота
    Restore(dp)

    dp.add_handler(StartDialog())

    dp.add_handler(PillTakingDialog())
    dp.add_handler(DataCollectionDialog())

    dp.add_handler(SettingsDialog())

    dp.add_handler(PatronageJob())

    dp.add_handler(CommandHandler("help", help_msg))
    dp.add_handler(MessageHandler(Filters.regex('^Справка$'), help_msg))

    dp.add_handler(MessageHandler(Filters.command, unknown))
    dp.add_handler(MessageHandler(Filters.text, echo))

    updater.start_polling()
    # Ждём завершения приложения.
    # (например, получения сигнала SIG_TERM при нажатии клавиш Ctrl+C)
    updater.idle()


# Запускаем функцию main() в случае запуска скрипта.
if __name__ == '__main__':
    main()
