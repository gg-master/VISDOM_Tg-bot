from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ConversationHandler, MessageHandler, Filters, \
    CommandHandler, CallbackContext

from modules.dialogs_shortcuts.start_shortcuts import SEND_USER_DATA_PAT, END
from modules.users_classes import PatientUser, PatronageUser
from tools.decorators import registered_patronages


class PatronageJob(ConversationHandler):
    def __init__(self):
        super().__init__(
            name=self.__class__.__name__,
            entry_points=[
                MessageHandler(Filters.regex('^Получить данные по пациенту$'),
                               PatronageJob.send_user_file),
                MessageHandler(
                    Filters.regex('^Получить данные по всем пользователям$'),
                    PatronageJob.send_users_data),
                MessageHandler(Filters.regex('^Получить список пациентов$'),
                               PatronageJob.send_patients_list)
            ],
            states={
                SEND_USER_DATA_PAT: [
                    MessageHandler(Filters.text & ~Filters.command,
                                   self.send_user_data)
                ]
            },
            fallbacks=[CommandHandler('stop', self.stop)],
        )

    @staticmethod
    def default_job(update: Update, context: CallbackContext):
        text = "Для использовния базовго функционала нажмите на" \
               " одну из нужных кнопок:"
        keyboard = ReplyKeyboardMarkup(
            [['Получить данные по пациенту',
              'Получить данные по всем пользователям'],
             ['Получить список пациентов']], row_width=1, resize_keyboard=True)

        update.effective_chat.send_message(text=text, reply_markup=keyboard)

    @staticmethod
    @registered_patronages
    def send_user_file(update: Update, context: CallbackContext):
        text = 'Введите код пациента'
        update.effective_chat.send_message(text)
        return SEND_USER_DATA_PAT

    @staticmethod
    @registered_patronages
    def send_user_data(update: Update, context: CallbackContext):
        user_code = update.message.text
        patient = PatientUser.get_patient_by_id(user_code)
        if patient:
            PatronageUser.make_file_by_patient(patient)
            update.effective_chat.send_document(
                open(f'static/{patient.user_code}.xlsx', 'rb'))
        else:
            update.message.reply_text('Пациента с таким кодом не существует')
        return END

    @staticmethod
    @registered_patronages
    def send_users_data(update: Update, context: CallbackContext):
        PatronageUser.make_file_patients()
        update.effective_chat.send_document(
            open(f'static/statistics.xlsx', 'rb'))
        return END

    @staticmethod
    @registered_patronages
    def send_patients_list(update: Update, context: CallbackContext):
        update.effective_chat.send_message("send_patients_list")
        return END

    @staticmethod
    def stop(update: Update, context: CallbackContext):
        text = 'Выполнение команды прервано.'
        update.effective_chat.send_message(text)
        return END
