import logging
import os
import atexit
from tools.atexit import clear_all_notification

from telegram import Update, error
from telegram.ext import (CommandHandler, Defaults,
                          Filters, MessageHandler, Updater, CallbackContext)

from modules.notification_dailogs import DataCollectionDialog, PillTakingDialog
from modules.patronage_dialogs import BaseJob
from modules.restore import Restore
from modules.settings_dialogs import SettingsDialog
from modules.start_dialogs import StartDialog
from modules.users_list import users_list

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
    from modules.users_classes import BasicUser, PatientUser, DoctorUser, \
        RegionUser, UniUser
    try:
        # Если бот перезапускался
        if not (user := context.user_data.get('user')):
            user = context.user_data['user'] = users_list[
                update.effective_user.id]
        if not user:
            update.message.reply_text(
                "Справка.\nЕсли Вы ранее не регистрировались, то чтобы начать "
                "работу с ботом, введите: /start\n\nЕсли Вы уже "
                "регистрировались, то восстановите доступ c помощью "
                "соответствующего сообщения.")
        elif type(user) is BasicUser:
            update.message.reply_text(
                "Справка.\nЧтобы получить больше возможностей "
                "зарегистрируйтесь.")
        elif type(user) is PatientUser:
            update.message.reply_text("Справка. Команды Для пациента.")
        elif type(user) is DoctorUser:
            update.message.reply_text("Справка. Команды для врача.")
        elif type(user) is RegionUser:
            update.message.reply_text("Справка. Команды для сотрудника.")
        elif type(user) is UniUser:
            update.message.reply_text("Справка. Команды для ВолГМУ.")
    except error.Unauthorized:
        pass


def main():
    if not os.path.isdir("static"):
        os.mkdir("static")

    updater = Updater(get_from_env('TOKEN'),
                      workers=8, use_context=True,
                      defaults=Defaults(run_async=True),
                      request_kwargs={'read_timeout': 20,
                                      'connect_timeout': 20})

    dp = updater.dispatcher

    # При заверении бота удаляем все сообщения с уведомлениями из чатов
    atexit.register(clear_all_notification, CallbackContext(dp))

    # Восстановление уведомлений после перезапуска бота
    Restore(dp)

    dp.add_handler(StartDialog())

    dp.add_handler(PillTakingDialog())
    dp.add_handler(DataCollectionDialog())

    dp.add_handler(SettingsDialog())

    dp.add_handler(BaseJob())

    dp.add_handler(CommandHandler("help", help_msg))
    dp.add_handler(MessageHandler(Filters.regex('Справка$'), help_msg))

    dp.add_handler(MessageHandler(Filters.command, unknown))

    updater.start_polling()

    # Ждём завершения приложения.
    updater.idle()


if __name__ == '__main__':
    main()
