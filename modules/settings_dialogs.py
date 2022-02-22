from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, error
from telegram.ext import (CallbackContext, CallbackQueryHandler,
                          CommandHandler, ConversationHandler, Filters,
                          MessageHandler)

from modules.dialogs_shortcuts.start_shortcuts import (CONF_NOTIFICATIONS,
                                                       CONF_TZ, END,
                                                       START_OVER, STOPPING)
from modules.start_dialogs import ConfigureNotifTimeDialog, ConfigureTZDialog
from tools.decorators import registered_patient

# State
SETTINGS_ACTION = 'SETTINGS_ACTION'
# Constants
DROP_NOTIF_TIME = 'DROP_NOTIF_TIME'
CONFIRM = 'CONFIRM'


class SettingsDialog(ConversationHandler):
    def __init__(self):
        super().__init__(
            name=self.__class__.__name__,
            entry_points=[MessageHandler(Filters.regex('Настройки$'),
                                         self.start)],
            states={
                SETTINGS_ACTION: [
                    SettingsConfTZDialog(),
                    SettingsConfNotifTimeDialog(),
                    CallbackQueryHandler(self.confirm,
                                         pattern=f'^{CONFIRM}$'),
                    CallbackQueryHandler(self.drop_notif_time,
                                         pattern=f'^{DROP_NOTIF_TIME}$')
                ]
            },
            fallbacks=[
                 CallbackQueryHandler(self.stop, pattern=f'CANCEL'),
                 CommandHandler('stop', self.stop),
                 MessageHandler(Filters.regex('Настройки$'), self.restart)
            ]
        )

    @staticmethod
    @registered_patient
    def start(update: Update, context: CallbackContext):
        user = context.user_data['user']
        text = 'Настройки.\n' \
               'Здесь Вы можете изменить время получения уведомлений или ' \
               'свой часовой пояс. \n' \
               'При необходимости Вы можете сбросить время получения ' \
               'уведомлений до значений по умолчанию.\n' \
               'Чтобы сохранить изменения нажмите "Подтвердить"'

        text += f'\n\nВаши данные:' \
                f'\nЧасовой пояс: {user.location}' \
                f'\nВремя получения утреннего уведомления: ' \
                f'{user.str_times()["MOR"]}\n' \
                f'Время получения вечернего уведомления: ' \
                f'{user.str_times()["EVE"]}' \

        buttons = [
            [
                InlineKeyboardButton(text='Изменить время',
                                     callback_data=f'{CONF_NOTIFICATIONS}'),
                InlineKeyboardButton(text='Изменить часовой пояс',
                                     callback_data=f'{CONF_TZ}'),
            ],
            [
                InlineKeyboardButton(text='Сбросить время уведомлений',
                                     callback_data=f'{DROP_NOTIF_TIME}'),
            ],
            [InlineKeyboardButton(text='Отмена', callback_data='CANCEL'),
             InlineKeyboardButton(text='Подтвердить',
                                  callback_data=f'{CONFIRM}'),
             ]
        ]
        kb = InlineKeyboardMarkup(buttons)

        if context.user_data.get(START_OVER):
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text,
                                                    reply_markup=kb)
        else:
            try:
                msg = update.message.reply_text(text=text, reply_markup=kb)
                context.chat_data['st_msg'] = msg.message_id
            except error.Unauthorized:
                return END
        context.user_data[START_OVER] = False
        return SETTINGS_ACTION

    @staticmethod
    def drop_notif_time(update: Update, context: CallbackContext):
        res = context.user_data['user'].drop_notif_time()
        if res:
            context.user_data[START_OVER] = True
            return SettingsDialog.start(update, context)

    @staticmethod
    def confirm(update: Update, context: CallbackContext):
        from modules.start_dialogs import PatientRegistrationDialog
        update.callback_query.delete_message()
        try:
            context.user_data['user'].save_updating(context)
            # print(context.job_queue.get_jobs_by_name(
            #     f'{context.user_data["user"].chat_id}-EVE')[0].next_t)
            # job1 = context.job_queue.get_jobs_by_name(
            #     f'{context.user_data["user"].chat_id}-rep_task')
            # if job1:
            #     print(job1[0].next_t))
            text = 'Изменения сохранены.'
            update.effective_chat.send_message(
                text=text,
                reply_markup=PatientRegistrationDialog.post_reg_kb)
        except ValueError:
            context.user_data['user'].cancel_updating()
            text = 'Изменения не удалось сохранить.\n' \
                   'Попробуйте снова через некоторое время.'
            update.effective_chat.send_message(
                text=text, reply_markup=PatientRegistrationDialog.post_reg_kb)
        except error.Unauthorized:
            pass
        finally:
            return END

    @staticmethod
    def stop(update: Update, context: CallbackContext):
        from modules.start_dialogs import PatientRegistrationDialog
        context.user_data['user'].cancel_updating()

        text = 'Изменения не были сохранеы.'

        if update.callback_query:
            update.callback_query.delete_message()
        elif context.chat_data.get('st_msg'):
            context.bot.delete_message(update.effective_chat.id,
                                       context.chat_data['st_msg'])
        try:
            update.effective_chat.send_message(
                text=text, reply_markup=PatientRegistrationDialog.post_reg_kb)
        except error.Unauthorized:
            pass
        return END

    @staticmethod
    def stop_nested(update: Update, context: CallbackContext):
        SettingsDialog.stop(update, context)
        return STOPPING

    @staticmethod
    @registered_patient
    def restart(update: Update, context: CallbackContext):
        try:
            context.bot.delete_message(update.effective_chat.id,
                                       context.chat_data['st_msg'])
        except Exception as e:
            print(e)
        finally:
            return SettingsDialog.start(update, context)


class SettingsConfNotifTimeDialog(ConfigureNotifTimeDialog):
    def __init__(self):
        super().__init__(stop_cb=SettingsDialog.stop_nested)
        self.map_to_parent.update({
            SETTINGS_ACTION: SETTINGS_ACTION,
            STOPPING: END,
            END: END,
        })

    @staticmethod
    def start(update: Update, context: CallbackContext, *args):
        text = f'Настройте время получения напоминаний (время МЕСТНОЕ)\n\n' \
               f'Время получения утреннего уведомления: ' \
               f'{context.user_data["user"].str_times()["MOR"]}\n' \
               f'Время получения вечернего уведомления: ' \
               f'{context.user_data["user"].str_times()["EVE"]}'
        return ConfigureNotifTimeDialog.start(update, context, text)

    @staticmethod
    def back(update: Update, context: CallbackContext):
        context.user_data[START_OVER] = True
        SettingsDialog.start(update, context)
        return END


class SettingsConfTZDialog(ConfigureTZDialog):
    def __init__(self):
        from modules.location import ChangeLocationDialog
        super().__init__(ChangeLocationDialog,
                         ex_fallbacks=[
                             CommandHandler('stop',
                                            SettingsDialog.stop_nested,
                                            run_async=False),
                             MessageHandler(Filters.regex('Настройки$'),
                                            SettingsDialog.restart,
                                            run_async=False)
                         ])
        self.map_to_parent.update({
            SETTINGS_ACTION: SETTINGS_ACTION,
            STOPPING: END,
        })

    @staticmethod
    def save_tz(update: Update, context: CallbackContext, *args):
        return ConfigureTZDialog.save_tz(update, context,
                                         SettingsDialog.start)

    @staticmethod
    def back(update: Update, context: CallbackContext):
        context.user_data[START_OVER] = True
        SettingsDialog.start(update, context)
        return END
