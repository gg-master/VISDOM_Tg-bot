import logging

from telegram import Update
from telegram.ext import CommandHandler, Updater, MessageHandler, \
    Filters, Defaults, CallbackQueryHandler

from modules.restore import Restore, patient_restore_handler, \
    patronage_restore_handler
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
    from modules.users_classes import BasicUser, PatientUser, PatronageUser
    if not context.user_data.get('user'):
        update.message.reply_text(
            "Справка.\nЕсли Вы ранее не регистрировались, то чтобы начать "
            "работу с ботом, введите: /start\n\n"
            "Если Вы уже регистрировались, то восстановите доступ c помощью "
            "соответствующего сообщения.")
    elif type(context.user_data.get('user')) is BasicUser:
        update.message.reply_text(
            "Справка.\nЧтобы получить больше возможностей зарегистрируйтесь.")
    elif type(context.user_data.get('user')) is PatientUser:
        update.message.reply_text("Справка. Команды Для пациента.")
    elif type(context.user_data.get('user')) is PatronageUser:
        update.message.reply_text("Справка. Команды для патронажа.")


# def echo(update: Update, context: CallbackContext):
#     import pytz
#     date = update.message.date
#     tz = pytz.timezone('Etc/Gmt-3')
#     print(tz.normalize(date), '\n', date.astimezone(tz))
#     update.message.reply_text(update.message.text)
#

def main():
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

    dp.add_handler(CallbackQueryHandler(patient_restore_handler,
                                        pattern='^RESTORE_PATIENT$'))
    dp.add_handler(CallbackQueryHandler(patronage_restore_handler,
                                        pattern='^RESTORE_PATRONAGE$'))

    dp.add_handler(CommandHandler("help", help_msg))
    dp.add_handler(MessageHandler(Filters.regex('Справка$'), help_msg))

    dp.add_handler(MessageHandler(Filters.command, unknown))
    dp.add_handler(MessageHandler(Filters.text, echo))

    updater.start_polling()
    # Ждём завершения приложения.
    # (например, получения сигнала SIG_TERM при нажатии клавиш Ctrl+C)
    updater.idle()


# Запускаем функцию main() в случае запуска скрипта.
if __name__ == '__main__':
    main()
