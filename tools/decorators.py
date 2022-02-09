from telegram import Update
from telegram.ext import CallbackContext


def not_registered_users(func):
    def decorated_func(update: Update, context: CallbackContext):
        user = context.user_data.get('user')
        if not (user and user.registered()):
            return func(update, context)
        return just_for_not_registered_msg(update, context)

    return decorated_func


def registered_patient(func):
    def decorated_func(update: Update, context: CallbackContext):
        from modules.users_classes import PatientUser
        user = context.user_data.get('user')
        if type(user) is PatientUser and user.registered():
            return func(update, context)
        return just_for_registered_msg(update, context)

    return decorated_func


def just_for_not_registered_msg(update: Update, context: CallbackContext):
    update.effective_chat.send_message(
        'Эта возможность предумотрена только для '
        'незарегистрированных пользователей.')


def just_for_registered_msg(update: Update, context: CallbackContext):
    update.effective_chat.send_message(
        'Эта возможность предумотрена только для '
        'зарегистрированных пользователей.')


def registered_patronages(func):
    def decorator(update: Update, context: CallbackContext):
        from modules.users_classes import PatronageUser
        user = context.user_data.get('user')
        if type(user) is PatronageUser and user.registered():
            return func(update, context)
        return just_for_patronage(update, context)
    return decorator


def just_for_patronage(update: Update, context: CallbackContext):
    update.effective_chat.send_message(
        'Это возможность предусмотрена только для специальных сотрудников')
