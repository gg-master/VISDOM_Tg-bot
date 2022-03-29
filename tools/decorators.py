from telegram import Update, error
from telegram.ext import CallbackContext

from modules.users_list import users_list


def not_registered_users(func):
    def decorated_func(update: Update, context: CallbackContext,
                       *args, **kwargs):

        # Если бот перезапускался
        if not (user := context.user_data.get('user')):
            user = context.user_data['user'] = users_list[
                update.effective_user.id]

        if not (user and user.registered()):
            return func(update, context, *args, **kwargs)
        return just_for_not_registered_msg(update)

    return decorated_func


def registered_patient(func):
    def decorated_func(update: Update, context: CallbackContext,
                       *args, **kwargs):
        from modules.users_classes import PatientUser

        # Если бот перезапускался
        if not (user := context.user_data.get('user')):
            user = context.user_data['user'] = users_list[
                update.effective_user.id]

        # Если пользователь - пациент, зарегистрирован и не исключен
        if type(user) is PatientUser and user.registered() and user.member:
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


def _parametrized(dec):
    def layer(*args, **kwargs):
        def repl(f):
            return dec(f, *args, **kwargs)
        return repl
    return layer


@_parametrized
def registered_patronages(func, *d_args, **d_kwargs):
    def decorator(update: Update, context: CallbackContext, *args, **kwargs):
        from modules.users_classes import DoctorUser, RegionUser, UniUser

        # Если бот перезапускался
        if not (user := context.user_data.get('user')):
            user = context.user_data['user'] = users_list[
                update.effective_user.id]

        dec_args = [DoctorUser, RegionUser, UniUser] if not d_args else d_args

        if type(user) in dec_args and user.registered():
            return func(update, context)
        return unavailable_for_user(update)
    return decorator


def unavailable_for_user(update: Update):
    try:
        update.effective_chat.send_message('Вам недоступнен '
                                           'данный функционал.')
    except error.Unauthorized:
        pass
