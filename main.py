import logging
import os

from telegram import Update, error
from telegram.ext import (CallbackQueryHandler, CommandHandler, Defaults,
                          Filters, MessageHandler, Updater, CallbackContext)

from modules.notification_dailogs import DataCollectionDialog, PillTakingDialog
from modules.patronage_dialogs import BaseJob
from modules.restore import (Restore, patient_restore_handler,
                             doctor_restore_handler, region_restore_handler,
                             uni_restore_handler)
from modules.settings_dialogs import SettingsDialog
from modules.start_dialogs import StartDialog

from tools.tools import get_from_env

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')


def unknown(update: Update, context: CallbackContext):
    try:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Извините, я не понял эту команду.")
    except error.Unauthorized:
        pass


def help_msg(update: Update, context: CallbackContext):
    from modules.users_classes import BasicUser, PatientUser, DoctorUser
    try:
        if not context.user_data.get('user'):
            update.message.reply_text(
                "Справка.\nЕсли Вы ранее не регистрировались, то чтобы начать "
                "работу с ботом, введите: /start\n\nЕсли Вы уже "
                "регистрировались, то восстановите доступ c помощью "
                "соответствующего сообщения.")
        elif type(context.user_data.get('user')) is BasicUser:
            update.message.reply_text(
                "Справка.\nЧтобы получить больше возможностей "
                "зарегистрируйтесь.")
        elif type(context.user_data.get('user')) is PatientUser:
            update.message.reply_text("Справка. Команды Для пациента.")
        elif type(context.user_data.get('user')) is DoctorUser:
            update.message.reply_text("Справка. Команды для патронажа.")
    except error.Unauthorized:
        pass


def main():
    if not os.path.isdir("static"):
        os.mkdir("static")

    updater = Updater(get_from_env('TOKEN'),
                      use_context=True, defaults=Defaults(run_async=True),
                      request_kwargs={'read_timeout': 10,
                                      'connect_timeout': 10})

    dp = updater.dispatcher

    # Восстановление уведомлений после перезапуска бота
    Restore(dp)

    dp.add_handler(StartDialog())

    dp.add_handler(PillTakingDialog())
    dp.add_handler(DataCollectionDialog())

    dp.add_handler(SettingsDialog())

    dp.add_handler(BaseJob())

    dp.add_handler(CallbackQueryHandler(patient_restore_handler,
                                        pattern='^RESTORE_PATIENT$'))
    dp.add_handler(CallbackQueryHandler(doctor_restore_handler,
                                        pattern='^RESTORE_DOCTOR$'))
    dp.add_handler(CallbackQueryHandler(region_restore_handler,
                                        pattern='^RESTORE_REGION$'))
    dp.add_handler(CallbackQueryHandler(uni_restore_handler,
                                        pattern='^RESTORE_UNI$'))

    dp.add_handler(CommandHandler("help", help_msg))
    dp.add_handler(MessageHandler(Filters.regex('Справка$'), help_msg))

    dp.add_handler(MessageHandler(Filters.command, unknown))

    updater.start_polling()

    # Ждём завершения приложения.
    updater.idle()


if __name__ == '__main__':
    main()
