from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, MessageHandler, Filters, \
    CommandHandler, CallbackQueryHandler, CallbackContext

from modules.dialogs_shortcuts.start_shortcuts import END


class SettingsDialog(ConversationHandler):
    def __init__(self):
        super().__init__(
            name=self.__class__.__name__,
            entry_points=[MessageHandler(Filters.regex('^Настройки$'),
                                         self.start)],
            states={
                'SETTINGS_ACTION': [

                ]
                # SETTINGS_ACTION: [
                #     CallbackQueryHandler(self.input_req,
                #                          pattern=f'^SYS$|^DIAS$|^HEART$'),
                #     CallbackQueryHandler(self.end, pattern=f'^{END}$')
                # ],
                # TYPING: [
                #     MessageHandler(Filters.text & ~Filters.command,
                #                    self.save_input)
                # ]
            },
            fallbacks=[CommandHandler('stop', self.stop)]
        )

    @staticmethod
    def start(update: Update, context: CallbackContext):
        text = 'Настройки'
        # location = context.user_data['user'].location

        buttons = [
            [
                InlineKeyboardButton(text='Отмена', callback_data=f'{END}'),
                InlineKeyboardButton(
                    text='Подтвердить', callback_data='1'),
            ],
            [
                InlineKeyboardButton(
                    text='Изменить время', callback_data='1'),
                InlineKeyboardButton(
                    text='Изменить часовой пояс', callback_data='1'),
            ],
            [
                InlineKeyboardButton(
                    text='Сбросить', callback_data='1'),
            ],
            [
             ]
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        if context.user_data.get('SETTINGS_OVER'):
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text,
                                                    reply_markup=keyboard)
        else:
            update.message.reply_text(text=text, reply_markup=keyboard)

        context.user_data['SETTINGS_OVER'] = False
        return 'SETTINGS_ACTION'

    @staticmethod
    def stop(update: Update, context: CallbackContext):
        return END