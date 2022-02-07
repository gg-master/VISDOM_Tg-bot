from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ConversationHandler, MessageHandler, Filters, \
    CommandHandler, CallbackContext, CallbackQueryHandler

from modules.dialogs_shortcuts.start_shortcuts import SEND_USER_DATA_PAT, END
from modules.users_classes import PatientUser, PatronageUser
from tools.decorators import registered_patronages
from db_api import get_patient_by_chat_id, get_patient_by_user_code, \
    make_file_by_patient_user_code, make_file_patients, make_patient_list


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
                               PatronageJob.send_patients_list),
                CallbackQueryHandler(self.alarm_send_p_data,
                                     pattern='^A_PATIENT_DATA')
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
               " одну из нужных кнопок. \nЧтобы прервать выполнение " \
               "команд отправьте /stop."
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
        try:
            patient = get_patient_by_user_code(user_code)
            if patient:
                make_file_by_patient_user_code(user_code)
                update.effective_chat.send_document(
                    open(f'static/{user_code}_data.xlsx', 'rb'))
            else:
                update.message.reply_text(
                    'Пациента с таким кодом не существует')
        except FileNotFoundError as e:
            print(e)
            update.message.reply_text(
                'Файл не найден. Обратитесь к администратору.')
        except Exception as e:
            print(e)
        finally:
            return END

    @staticmethod
    # @registered_patronages
    def alarm_send_p_data(update: Update, context: CallbackContext):
        # TODO проработка диалога аларма
        data = update.callback_query.data
        user_code = data[data.find('&') + 1:]

        patient = get_patient_by_user_code(user_code)
        make_file_by_patient_user_code(user_code)
        update.effective_chat.send_document(
            open(f'static/{patient.user_code}.xlsx', 'rb'))

    @staticmethod
    @registered_patronages
    def send_users_data(update: Update, context: CallbackContext):
        make_file_patients()
        update.effective_chat.send_document(
            open('static/statistics.xlsx', 'rb'))
        return END

    @staticmethod
    @registered_patronages
    def send_patients_list(update: Update, context: CallbackContext):
        make_patient_list()
        update.effective_chat.send_document(
            open('static/Список пациентов.txt', 'rb'))
        return END

    @staticmethod
    def stop(update: Update, context: CallbackContext):
        text = 'Выполнение команды прервано.'
        update.effective_chat.send_message(text)
        return END
