import datetime as dt

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, ConversationHandler, \
    CallbackQueryHandler, CommandHandler

from modules.dialogs_shortcuts.start_shortcuts import END
from db_api import get_patient_by_chat_id, get_accept_time_by_patient, get_all_patients


class Restore:
    def __init__(self, dispatcher):
        self.context = CallbackContext(dispatcher)

        self.restore_all_patient()

    def restore_all_patient(self):
        patients = get_all_patients()
        for patient in patients:
            if patient.chat_id != 394:
                accept_times = get_accept_time_by_patient(patient)
                self.restore_patient(patient, accept_times)

    def restore_patient(self, patient, accept_times):
        from modules.users_classes import PatientUser

        times = {'MOR': accept_times[0].time, 'EVE': accept_times[1].time}
        p = PatientUser(patient.chat_id)
        p.restore(times, patient.time_zone)
        p.recreate_notification(self.context)

        Restore.restore_msg(self.context, chat_id=patient.chat_id)

    @staticmethod
    def restore_msg(context, **kwargs):
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


def patient_restore_handler(update: Update, context: CallbackContext):
    from modules.users_classes import PatientUser
    from modules.start_dialogs import PatientRegistrationDialog

    p = get_patient_by_chat_id(update.effective_chat.id)
    accept_times = get_accept_time_by_patient(p)

    context.user_data['user'] = \
        PatientUser(update.effective_chat.id)
    context.user_data['user'].restore(
        {
            'MOR': accept_times[0].time,
            # 'MOR': dt.time(hour=11, minute=45),
            'EVE': accept_times[1].time
        },
        tz_str=p.time_zone,
        accept_times={'MOR': accept_times[0].id,
                      'EVE': accept_times[1].id}
    )
    update.callback_query.delete_message()
    update.effective_chat.send_message('Доступ восстановлен')
    PatientRegistrationDialog.restore_main_msg(update, context)


