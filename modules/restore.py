import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext


from db_api import get_accept_time_by_patient, get_all_patients, \
    get_patient_by_chat_id, get_all_patronages
from tools.decorators import not_registered_users


class Restore:
    def __init__(self, dispatcher):
        self.context = CallbackContext(dispatcher)

        # Восстановление всех пациентов, которые зарегистрированны и участвуют
        self.restore_all_patients()

        # Восстановление патронажа
        self.restore_patronage(self.context)

    def restore_all_patients(self):
        patients = get_all_patients()
        for patient in patients:
            if patient.chat_id != 394 and patient.member:
                accept_times = get_accept_time_by_patient(patient)
                self.restore_patient(patient, accept_times)

    def restore_patient(self, patient, accept_times):
        from modules.users_classes import PatientUser

        times = {'MOR': accept_times[0].time, 'EVE': accept_times[1].time}
        p = PatientUser(patient.chat_id)
        p.restore(times, patient.time_zone)

        # Восстановление обычных Daily тасков
        p.recreate_notification(self.context)

        # Восстановление цикличных тасков. Если для них соответствует время
        if not self.context.job_queue.get_jobs_by_name(
                f'{p.chat_id}-rep_task'):
            p.restore_repeating_task(self.context)

        logging.info(f'RESTORED PATIENT NOTIFICATIONS: {p.chat_id}')
        Restore.restore_patient_msg(self.context, chat_id=patient.chat_id)

    @staticmethod
    def restore_patronage(context):
        patronages = get_all_patronages()
        if patronages:
            Restore.restore_patronage_msg(context,
                                          chat_id=patronages[0].chat_id)

    @staticmethod
    def restore_patient_msg(context, **kwargs):
        text = 'Уважаемый пользователь, чат-бот был перезапущен.\n' \
               'Приносим свои извенения за доставленные неудобства.\n' \
               'Уведомления были востановлены.\n' \
               'Чтобы получить доступ к основным функциям нажмите ' \
               '"Восстановить доступ"'
        buttons = [
            [InlineKeyboardButton(text='Восстановить доступ',
                                  callback_data=f'RESTORE_PATIENT')],
        ]
        keyboard = InlineKeyboardMarkup(buttons)
        context.bot.send_message(
            kwargs['chat_id'], text=text, reply_markup=keyboard)

    @staticmethod
    def restore_patronage_msg(context, **kwargs):
        text = 'Уважаемый пользователь, чат-бот был перезапущен.\n' \
               'Приносим свои извенения за доставленные неудобства.\n' \
               'Чтобы получить доступ к основным функциям нажмите ' \
               '"Восстановить доступ"'
        buttons = [
            [InlineKeyboardButton(text='Восстановить доступ',
                                  callback_data=f'RESTORE_PATRONAGE')],
        ]
        keyboard = InlineKeyboardMarkup(buttons)
        context.bot.send_message(
            kwargs['chat_id'], text=text, reply_markup=keyboard)


@not_registered_users
def patient_restore_handler(update: Update, context: CallbackContext):
    from modules.users_classes import PatientUser
    from modules.start_dialogs import PatientRegistrationDialog

    p = get_patient_by_chat_id(update.effective_chat.id)
    accept_times = get_accept_time_by_patient(p)

    context.user_data['user'] = PatientUser(update.effective_chat.id)
    context.user_data['user'].restore(
        times={'MOR': accept_times[0].time, 'EVE': accept_times[1].time},
        tz_str=p.time_zone,
        accept_times={'MOR': accept_times[0].id,
                      'EVE': accept_times[1].id}
    )

    logging.info(f'RESTORED PATIENT: {p.chat_id}')
    update.callback_query.delete_message()
    update.effective_chat.send_message(
        'Доступ восстановлен. Теперь Вы можете добавить ответ на уведомления, '
        'к которым не было доступа.')
    PatientRegistrationDialog.restore_main_msg(update, context)


@not_registered_users
def patronage_restore_handler(update: Update, context: CallbackContext):
    from modules.users_classes import PatronageUser
    from modules.patronage_dialogs import PatronageJob

    p = context.user_data['user'] = PatronageUser(update.effective_chat.id)
    p.restore(context)
    logging.info(f'RESTORED PATRONAGE: {p.chat_id}')
    update.callback_query.delete_message()
    update.effective_chat.send_message(
        'Доступ восстановлен.')
    PatronageJob.default_job(update, context)
