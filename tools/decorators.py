from telegram import Update
from telegram.ext import CallbackContext


def not_registered_users(func):
    def decorated_func(update: Update, context: CallbackContext):
        if 'is_registered' not in context.user_data or \
                not context.user_data['is_registered']:
            return func(update, context)
        return just_for_not_registered_msg(update, context)

    return decorated_func


def registered_users(func):
    def decorated_func(update: Update, context: CallbackContext):
        if 'is_registered' in context.user_data \
                and context.user_data['is_registered']:
            return func(update, context)
        return just_for_registered_msg(update, context)

    return decorated_func


def just_for_not_registered_msg(update: Update, context: CallbackContext):
    context.bot.send_message(update.effective_chat.id,
                             text='Эта возможность предумотрена только для '
                                  'незарегистрированных пользователей')


def just_for_registered_msg(update: Update, context: CallbackContext):
    context.bot.send_message(update.effective_chat.id,
                             text='Эта возможность предумотрена только для '
                                  'зарегистрированных пользователей')
