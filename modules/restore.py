import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, error
from telegram.ext import CallbackContext

from db_api import (get_accept_times_by_patient_id, get_all_patients,
                    get_all_doctors)
from modules.patient_list import patient_list
from modules.timer import remove_job_if_exists
from tools.decorators import not_registered_users


class Restore:
    def __init__(self, dispatcher):
        self.context = CallbackContext(dispatcher)

        # Восстановление всех пациентов, которые зарегистрированны и участвуют
        self.restore_all_patients()

        # Восстановление патронажа
        self.restore_doctor(self.context)

    def restore_all_patients(self):
        for patient in filter(lambda x: x.member, get_all_patients()):
            accept_times = get_accept_times_by_patient_id(patient.id)
            self.restore_patient(patient, accept_times)

    def restore_patient(self, patient, accept_times):
        from modules.users_classes import PatientUser

        p = PatientUser(patient.chat_id)
        p.restore(
            code=patient.user_code,
            tz_str=patient.time_zone,
            times={'MOR': accept_times[0].time, 'EVE': accept_times[1].time},
            accept_times={'MOR': accept_times[0].id, 'EVE': accept_times[1].id}
        )
        patient_list[p.chat_id] = p
        # Восстановление обычных Daily тасков
        p.recreate_notification(self.context)

        # Восстановление цикличных тасков. Если для них соответствует время
        p.restore_repeating_task(self.context)

        # Проверяем пациента на время последней записи
        p.check_user_records(self.context)

        logging.info(f'RESTORED PATIENT NOTIFICATIONS: {p.chat_id}')
        Restore.restore_patient_msg(self.context, chat_id=patient.chat_id)

    @staticmethod
    def restore_doctor(context):
        patrs = get_all_doctors()
        if patrs:
            Restore.restore_doctor_msg(context, chat_id=patrs[0].chat_id)

    @staticmethod
    def restore_patient_msg(context, **kwargs):
        text = 'Уважаемый пользователь, чат-бот был перезапущен.\n' \
               'Приносим свои извенения за доставленные неудобства.\n' \
               'Уведомления были востановлены.\n' \
               'Чтобы получить доступ к основным функциям нажмите ' \
               '"Восстановить доступ"'
        buttons = [[InlineKeyboardButton(text='Восстановить доступ',
                                         callback_data=f'RESTORE_PATIENT')]]
        kb = InlineKeyboardMarkup(buttons)
        context.bot.send_message(kwargs['chat_id'], text=text, reply_markup=kb)

    @staticmethod
    def restore_doctor_msg(context, **kwargs):
        text = 'Уважаемый пользователь, чат-бот был перезапущен.\n' \
               'Приносим свои извенения за доставленные неудобства.\n' \
               'Чтобы получить доступ к основным функциям нажмите ' \
               '"Восстановить доступ"'
        buttons = [
            [InlineKeyboardButton(text='Восстановить доступ',
                                  callback_data=f'RESTORE_DOCTOR')],
        ]
        keyboard = InlineKeyboardMarkup(buttons)
        try:
            context.bot.send_message(
                kwargs['chat_id'], text=text, reply_markup=keyboard)
        except Exception as e:
            logging.warning(f"CANT SEND RESTORE_MSG TO DOCTOR. "
                            f"CHAT NOT FOUND. \nMORE: {e}")


@not_registered_users
def patient_restore_handler(update: Update, context: CallbackContext):
    from modules.start_dialogs import PatientRegistrationDialog

    # Устанавливаем в контекст ранее созданный объект пациента
    user = context.user_data['user'] = patient_list[update.effective_chat.id]

    logging.info(f'RESTORED PATIENT: {user.chat_id}')

    # Если уже пришло уведомление, то переотправляем его после восстановления
    if user.msg_to_del:
        # Получаем id сообщения иp пользователя
        try:
            context.bot.delete_message(user.chat_id,
                                       user.msg_to_del.message_id)
        except Exception as e:
            pass

    # Удаляем сообщени с кнопкой восстановления
    update.callback_query.delete_message()
    update.effective_chat.send_message(
        'Доступ восстановлен. Теперь Вы можете добавить ответ на уведомления, '
        'к которым не было доступа.')
    PatientRegistrationDialog.restore_main_msg(update, context)

    # Если уже пришло уведомление, то переотправляем его после восстановления
    if user.msg_to_del:
        # Снова отображаем удаленное уведомление
        user.notification_states[user.state()[0]][
            user.state()[1]].pre_start(
            context, context.job_queue.get_jobs_by_name(
                f'{user.chat_id}-rep_task')[0].context)


@not_registered_users
def doctor_restore_handler(update: Update, context: CallbackContext):
    from modules.users_classes import DoctorUser
    from modules.doctor_dialogs import DoctorJob

    p = context.user_data['user'] = DoctorUser(update.effective_chat.id)
    p.restore(context)
    logging.info(f'RESTORED DOCTOR: {p.chat_id}')
    try:
        update.callback_query.delete_message()
        update.effective_chat.send_message('Доступ восстановлен.')
        DoctorJob.default_job(update, context)
    except Exception as e:
        logging.warning(f"CANT SEND RESTORE_MSG TO PATIENT. CHAT NOT FOUND."
                        f"\nMORE: {e}")
