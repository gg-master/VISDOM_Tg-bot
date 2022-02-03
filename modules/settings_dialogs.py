from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, \
    ReplyKeyboardMarkup
from telegram.ext import ConversationHandler, MessageHandler, Filters, \
    CommandHandler, CallbackQueryHandler, CallbackContext

from modules.dialogs_shortcuts.start_shortcuts import \
    END, CONF_TZ, CONF_NOTIFICATIONS
from modules.start_dialogs import ConfigureTZDialog, ConfigureNotifTimeDialog

(
    # State
    SETTINGS_ACTION,
    # Constants
    SETTINGS_OVER,
    DROP_NOTIF_TIME,
    CONFIRM
) = map(chr, range(4))


class SettingsDialog(ConversationHandler):
    def __init__(self):
        super().__init__(
            name=self.__class__.__name__,
            entry_points=[MessageHandler(Filters.regex('^Настройки$'),
                                         self.start)],
            states={
                SETTINGS_ACTION: [
                    SettingsConfTZDialog(),
                    SettingsConfNotifTimeDialog(),
                    CallbackQueryHandler(self.confirm, pattern=f'^{CONFIRM}$'),
                    CallbackQueryHandler(self.drop_notif_time,
                                         pattern=f'^{DROP_NOTIF_TIME}$')
                ]
            },
            fallbacks=[
                 CallbackQueryHandler(self.stop, pattern=f'^{END}$'),
                 CommandHandler('stop', self.stop)]
        )

    @staticmethod
    def start(update: Update, context: CallbackContext):
        text = 'Настройки'

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
            [InlineKeyboardButton(text='Отмена', callback_data=f'{END}'),
             InlineKeyboardButton(text='Подтвердить',
                                  callback_data=f'{CONFIRM}'),
             ]
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        if context.user_data.get(SETTINGS_OVER):
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text,
                                                    reply_markup=keyboard)
        else:
            update.message.reply_text(text=text, reply_markup=keyboard)

        context.user_data[SETTINGS_OVER] = False
        return SETTINGS_ACTION

    @staticmethod
    def drop_notif_time(update: Update, context: CallbackContext):
        pass

    @staticmethod
    def stop(update: Update, context: CallbackContext):
        text = "Изменения не были сохранеы."

        keyboard = ReplyKeyboardMarkup(
            [['Справка', 'Настройки']], row_width=1, resize_keyboard=True)

        update.callback_query.delete_message()

        context.bot.send_message(
            update.effective_chat.id, text=text, reply_markup=keyboard)
        return END


class SettingsConfNotifTimeDialog(ConfigureNotifTimeDialog):
    def __init__(self):
        super().__init__()

    @staticmethod
    def start(update: Update, context: CallbackContext, *args):
        text = f'Настройте время получения напоминаний (время МЕСТНОЕ)\n\n' \
               f'Время получения утреннего уведомления: ' \
               f'{context.user_data["user"].times()["MOR"]}\n' \
               f'Время получения вечернего уведомления: ' \
               f'{context.user_data["user"].times()["EVE"]}'
        return ConfigureNotifTimeDialog.start(update, context, text)

    @staticmethod
    def back(update: Update, context: CallbackContext):
        context.user_data[SETTINGS_OVER] = True
        SettingsDialog.start(update, context)
        return END


class SettingsConfTZDialog(ConfigureTZDialog):
    def __init__(self):
        from modules.location import ChangeLocationDialog
        super().__init__(ChangeLocationDialog)

    @staticmethod
    def save_tz(update: Update, context: CallbackContext, *args):
        ConfigureTZDialog.save_tz(update, context, SettingsConfTZDialog)
        SettingsDialog.start(update, context)
        return END

    @staticmethod
    def back(update: Update, context: CallbackContext):
        context.user_data[SETTINGS_OVER] = True
        SettingsDialog.start(update, context)
        return END
