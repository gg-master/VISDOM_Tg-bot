from telegram import Update, error
from telegram.ext import CallbackContext


def not_registered_users(func):
    def decorated_func(update: Update, context: CallbackContext,
                       *args, **kwargs):
        user = context.user_data.get('user')
        if not (user and user.registered()):
            return func(update, context, *args, **kwargs)
        return just_for_not_registered_msg(update)

    return decorated_func


def registered_patient(func):
    def decorated_func(update: Update, context: CallbackContext,
                       *args, **kwargs):
        from modules.users_classes import PatientUser
        user = context.user_data.get('user')
        if type(user) is PatientUser and user.registered():
            return func(update, context, *args, **kwargs)
        return just_for_registered_msg(update)

    return decorated_func


def just_for_not_registered_msg(update: Update):
    try:
        update.effective_chat.send_message(
            'Эта возможность предумотрена только для '
            'незарегистрированных пользователей.')
    except error.Unauthorized:
        pass


def just_for_registered_msg(update: Update):
    try:
        update.effective_chat.send_message(
            'Эта возможность предумотрена только для '
            'зарегистрированных пользователей.')
    except error.Unauthorized:
        pass


def registered_doctors(func):
    def decorator(update: Update, context: CallbackContext, *args, **kwargs):
        from modules.users_classes import DoctorUser
        user = context.user_data.get('user')
        if type(user) is DoctorUser and user.registered():
            return func(update, context, *args, **kwargs)
        return just_for_doctor(update)
    return decorator


def just_for_doctor(update: Update):
    try:
        update.effective_chat.send_message(
            'Это возможность предусмотрена только для специальных сотрудников')
    except error.Unauthorized:
        pass
