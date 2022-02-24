import logging
from os import remove

from telegram import ReplyKeyboardMarkup, Update, error
from telegram.ext import (CallbackContext, CallbackQueryHandler,
                          CommandHandler, ConversationHandler, Filters,
                          MessageHandler)

from db_api import (change_patients_membership, get_patient_by_user_code,
                    make_file_by_patient_user_code, make_file_patients,
                    make_patient_list, patient_exists_by_user_code)
from modules.dialogs_shortcuts.start_shortcuts import (END, EXCLUDE_PATIENT,
                                                       SEND_USER_DATA_PAT)
from modules.patient_list import patient_list
from tools.decorators import registered_doctors


class DoctorJob(ConversationHandler):
    def __init__(self):
        super().__init__(
            name=self.__class__.__name__,
            entry_points=[
                MessageHandler(Filters.regex('^Получить данные по пациенту$'),
                               DoctorJob.send_user_file),
                MessageHandler(
                    Filters.regex('^Получить данные по всем пользователям$'),
                    DoctorJob.send_users_data),
                MessageHandler(Filters.regex('^Получить список пациентов$'),
                               DoctorJob.send_patients_list),
                MessageHandler(Filters.regex('^Исключить пациента из'
                                             ' исследования$'),
                               DoctorJob.exclude_patient_state),
                CallbackQueryHandler(self.alarm_send_p_data,
                                     pattern='^A_PATIENT_DATA')
            ],
            states={
                SEND_USER_DATA_PAT: [
                    MessageHandler(Filters.text & ~Filters.command,
                                   self.send_user_data)
                ],
                EXCLUDE_PATIENT: [
                    MessageHandler(Filters.text & ~Filters.command,
                                   self.exclude_patient)
                ]
            },
            fallbacks=[CommandHandler('stop', self.stop)],
        )

    @staticmethod
    def default_job(update: Update, context: CallbackContext):
        text = 'Для использовния базовго функционала нажмите на' \
               ' одну из нужных кнопок. \nЧтобы прервать выполнение ' \
               'команд отправьте /stop.'

        kb = ReplyKeyboardMarkup(
            [['Получить данные по пациенту',
              'Получить данные по всем пользователям'],
             ['Получить список пациентов',
              'Исключить пациента из исследования']],
            row_width=1, resize_keyboard=True)
        try:
            update.effective_chat.send_message(text=text, reply_markup=kb)
        except error.Unauthorized:
            pass

    @staticmethod
    @registered_doctors
    def send_user_file(update: Update, context: CallbackContext):
        text = 'Введите код пациента'
        try:
            update.effective_chat.send_message(text)
            return SEND_USER_DATA_PAT
        except error.Unauthorized:
            return END

    @staticmethod
    @registered_doctors
    def exclude_patient_state(update: Update, context: CallbackContext):
        text = 'Введите код пациента'
        try:
            update.effective_chat.send_message(text)
            return EXCLUDE_PATIENT
        except error.Unauthorized:
            return END

    @staticmethod
    @registered_doctors
    def send_user_data(update: Update, context: CallbackContext):
        user_code = update.message.text
        if patient_exists_by_user_code(
                user_code, doctor_code='034ВВП'):
            try:
                make_file_by_patient_user_code(user_code)
                update.effective_chat.send_document(
                    open(f'static/{user_code}_data.xlsx', 'rb'))

                remove(f'static/{user_code}_data.xlsx')
            except FileNotFoundError as ex:
                logging.info(ex)
                update.message.reply_text(
                    'Файл не найден. Обратитесь к администратору.')
            except error.Unauthorized:
                return END
            except Exception as ex:
                logging.info(ex)
        else:
            update.message.reply_text(
                'Пациента с таким кодом не существует или у вас нет прав'
                ' для просмотра.')
        return END

    @staticmethod
    @registered_doctors
    def exclude_patient(update: Update, context: CallbackContext):
        # user_code = update.message.text
        # patient = get_patient_by_user_code(user_code)
        # try:
        #     if patient:
        #         change_patients_membership(user_code, False)
        #
        #         patient_list[patient.chat_id].change_membership(context)
        #         logging.info(f'Patient {user_code}-{patient.chat_id} EXCLUDE')
        #
        #         context.bot.send_message(
        #             patient.chat_id, 'Вы были исключны из исследования.\n'
        #                              'Если это ошибка, обратитесь к врачу.')
        #         update.message.reply_text(f'Пациент {user_code} был исключен '
        #                                   f'из исследования.')
        #     else:
        #         update.message.reply_text(
        #             'Пациента с таким кодом не существует или у вас нет'
        #             ' прав его удаления')
        # except error.Unauthorized:
        #     pass
        return END

    @staticmethod
    @registered_doctors
    def alarm_send_p_data(update: Update, context: CallbackContext):
        data = update.callback_query.data
        user_code = data[data.find('&') + 1:]
        try:
            make_file_by_patient_user_code(user_code)
            update.effective_chat.send_document(
                open(f'static/{user_code}_data.xlsx', 'rb'))
            context.bot.edit_message_reply_markup(
                update.effective_chat.id, update.effective_message.message_id)
        except error.Unauthorized:
            pass

    @staticmethod
    @registered_doctors
    def send_users_data(update: Update, context: CallbackContext):
        make_file_patients(doctor_code='034ВВП')
        try:
            update.effective_chat.send_document(
                open('static/statistics.csv', 'rb'))
            remove('static/statistics.csv')
        except FileNotFoundError as ex:
            logging.info(ex)
            update.effective_chat.send_message(
                'Файл не найден. Обратитесь к администратору.'
            )
        except error.Unauthorized:
            pass
        except Exception as ex:
            logging.info(ex)
        return END

    @staticmethod
    @registered_doctors
    def send_patients_list(update: Update, context: CallbackContext):
        make_patient_list(doctor_code='034ВВП')
        try:
            update.effective_chat.send_document(
                open('static/Список пациентов.xlsx', 'rb'))
            remove('static/Список пациентов.xlsx')
        except FileNotFoundError as ex:
            logging.info(ex)
            update.effective_chat.send_message(
                'Файл не найден. Обратитесь к администратору.'
            )
        except error.Unauthorized:
            pass
        except Exception as ex:
            logging.info(ex)
        return END

    @staticmethod
    def stop(update: Update, context: CallbackContext):
        try:
            text = 'Выполнение команды прервано.'
            update.effective_chat.send_message(text)
        except error.Unauthorized:
            pass
        return END
