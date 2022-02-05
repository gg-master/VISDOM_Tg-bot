import datetime as dt

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, ConversationHandler, \
    CallbackQueryHandler, CommandHandler

from modules.dialogs_shortcuts.start_shortcuts import END
from db_api import get_patient_by_chat_id, get_accept_time_by_patient


class Restore:
    def __init__(self, dispatcher):
        self.context = CallbackContext(dispatcher)
        self.users = [(721698752, [dt.time(11, 45, 30), dt.time(11, 26, 0)],
                       'Etc/GMT-3')]
        # self.restore_patient(self.users[0])

    def restore_patient(self, data):
        from modules.users_classes import PatientUser
        chat_id, times, tz = data
        times = {'MOR': times[0], 'EVE': times[1]}
        p = PatientUser(chat_id)
        p.restore(self.context, times, tz)
        Restore.restore_msg(self.context, chat_id=chat_id)

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
        context,
        {
            # 'MOR': accept_times[0].time,
            'MOR': dt.time(hour=11, minute=45),
            'EVE': accept_times[1].time
        },
        tz_str=p.time_zone,
        accept_times={'MOR': accept_times[0].id,
                      'EVE': accept_times[1].id}
    )
    update.callback_query.delete_message()
    update.effective_chat.send_message('Доступ восстановлен')
    PatientRegistrationDialog.restore_main_msg(update, context)


