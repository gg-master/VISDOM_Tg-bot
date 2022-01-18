from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    CallbackContext, ConversationHandler, CommandHandler, MessageHandler,
    Filters,
)


from modules.prepared_answers import REGISTRATION_START_MSG
from tools.decorators import not_registered_users


class RegistrationDialog(ConversationHandler):
    def __init__(self):
        from modules.location import FindLocationDialog
        super().__init__(
            entry_points=[CommandHandler('start', self.start)],
            states={
                2: [MessageHandler(Filters.text, self.first_response)],
                1: [FindLocationDialog()]
            },
            fallbacks=[CommandHandler('stop', self.stop)]
        )

    @staticmethod
    @not_registered_users
    def start(update: Update, context: CallbackContext):
        context.user_data['is_registered'] = False

        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        print(f"{user_id} - {first_name}")

        keyboard = ReplyKeyboardMarkup(
            [
                ['Добавить местоположение']
            ],
            row_width=1, resize_keyboard=True, one_time_keyboard=True)

        context.bot.send_message(update.effective_chat.id,
                                 text=REGISTRATION_START_MSG,
                                 reply_markup=keyboard)
        return 1

    def first_response(self, update: Update, context: CallbackContext):
        print(f'REG - {update.message.text} - {update.message.location}')
        print('end')
        # if update.message.location:
        #     print(update.message.location)
        return self.END

    @staticmethod
    def stop(update: Update, context: CallbackContext):
        pass
