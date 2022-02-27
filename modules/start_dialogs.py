from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, error)
from telegram.ext import (CallbackContext, CallbackQueryHandler,
                          CommandHandler, Filters, MessageHandler)

from modules.dialogs_shortcuts.start_shortcuts import *
from modules.patronage_dialogs import DoctorJob, RegionJob, UniJob
from modules.restore import Restore
from modules.users_classes import BasicUser, PatientUser, DoctorUser, \
    RegionUser, UniUser
from tools.decorators import not_registered_users
from tools.exceptions import UserExists, DoctorNotFound, RegionNotFound
from tools.prepared_answers import START_MSG
from tools.tools import get_from_env


def user_separation(func):
    def decorated_func(update: Update, context: CallbackContext):
        user = context.user_data.get('user')
        if not user or not user.registered():
            return func(update, context)
        else:
            if type(user) is PatientUser:
                if not user.member:
                    return func(update, context)
                PatientRegistrationDialog.restore_main_msg(update, context)
            elif type(user) is DoctorUser:
                DoctorJob.default_job(update, context)
            elif type(user) is RegionUser:
                RegionJob.default_job(update, context)
            elif type(user) is UniUser:
                UniJob.default_job(update, context)
            return END

    return decorated_func


def pre_start_check(cls, update, context):
    dct = {
        (BasicUser.USER_IS_PATIENT, BasicUser.USER_EXCLUDED):
            PatientRegistrationDialog,
        (BasicUser.USER_IS_DOCTOR,): DoctorRegistrationDialog,
        (BasicUser.USER_IS_REGION,): RegionRegistrationDialog,
        (BasicUser.USER_IS_UNI,): UniRegistrationDialog,
    }
    res = context.user_data['user'].check_user_reg()
    for k, v in dct.items():
        if res in k:
            if cls is v:
                return res
            return v.pre_start(update, context, res=res)
    return res


class StartDialog(ConversationHandler):
    def __init__(self):
        super().__init__(
            name=self.__class__.__name__,
            entry_points=[CommandHandler('start', self.start)],
            states={
                START_SELECTORS: [PatientRegistrationDialog(),
                                  DoctorRegistrationDialog(),
                                  RegionRegistrationDialog(),
                                  UniRegistrationDialog()],
            },
            fallbacks=[CommandHandler('stop', self.stop),
                       CommandHandler('start', self.restart)])

    @staticmethod
    @user_separation
    def start(update: Update, context: CallbackContext):
        user = context.user_data.get('user')
        print(type(user), end=' - ')
        if not user or not user.registered():
            context.user_data['user'] = BasicUser(update.effective_chat.id)
        print(type(context.user_data.get('user')))
        buttons = [
            [InlineKeyboardButton(text='Я пациент',
                                  callback_data=f'{SIGN_UP_AS_PATIENT}'),
             InlineKeyboardButton(text='Я врач',
                                  callback_data=f'{SIGN_UP_AS_DOCTOR}')
             ],
            [InlineKeyboardButton(text='Я сотрудник',
                                  callback_data=f'{SIGN_UP_AS_REGION}'),
             InlineKeyboardButton(text='ВолгГМУ',
                                  callback_data=f'{SIGN_UP_AS_UNIVERSITY}')
             ]
        ]
        kb = InlineKeyboardMarkup(buttons)

        text = 'Чтобы начать пользоваться Чат-Ботом ' \
               'необходимо зарегистрироваться.'

        if context.user_data.get(START_OVER):
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text,
                                                    reply_markup=kb)
        else:
            try:
                update.message.reply_text(
                    START_MSG, reply_markup=ReplyKeyboardRemove())
                msg = update.message.reply_text(text=text, reply_markup=kb)
                # Сохраняем id стартового сообщения, если войдет Patronage
                context.chat_data['st_msg'] = msg.message_id
            except error.Unauthorized:
                return END
        context.user_data[START_OVER] = False
        return START_SELECTORS

    @staticmethod
    def stop(update: Update, context: CallbackContext):
        context.bot.delete_message(update.effective_chat.id,
                                   context.chat_data['st_msg'])
        keyboard = ReplyKeyboardMarkup([['/start']],
                                       row_width=1, resize_keyboard=True)
        try:
            update.message.reply_text(
                text='Регистрация прервана.\nЧтобы повторно '
                     'начать регистрацию отправьте:\n/start',
                reply_markup=keyboard)
        except error.Unauthorized:
            pass
        return END

    @staticmethod
    def stop_nested(update: Update, context: CallbackContext):
        StartDialog.stop(update, context)
        return STOPPING

    @staticmethod
    def restart(update: Update, context: CallbackContext):
        try:
            context.bot.delete_message(update.effective_chat.id,
                                       context.chat_data['st_msg'])
        except error.TelegramError:
            pass
        finally:
            return StartDialog.start(update, context)


class PatientRegistrationDialog(ConversationHandler):
    post_reg_kb = ReplyKeyboardMarkup([['❔Справка', '⚙️Настройки']],
                                      row_width=1, resize_keyboard=True)

    def __init__(self):
        super().__init__(
            name=self.__class__.__name__,
            entry_points=[CallbackQueryHandler(
                self.pre_start, pattern=f'^{SIGN_UP_AS_PATIENT}$',
                run_async=False)],
            states={
                PATIENT_REGISTRATION_ACTION: [
                    ConfigureTZDialog(),
                    ConfigureNotifTimeDialog(),
                    CallbackQueryHandler(self.conf_code,
                                         pattern=f'^{CONF_CODE}$')
                ],
                TYPING_CODE: [
                    MessageHandler(Filters.text & ~Filters.command,
                                   self.save_code, run_async=False)
                ],
            },
            fallbacks=[
                CallbackQueryHandler(self.back_to_start, pattern=f'^{END}$'),
                CommandHandler('stop', StartDialog.stop_nested,
                               run_async=False),
                CommandHandler('start', StartDialog.restart, run_async=False)
            ],
            map_to_parent={
                STOPPING: END,
                START_SELECTORS: START_SELECTORS
            }
        )

    @staticmethod
    def pre_start(update: Update, context: CallbackContext, res=None):
        res = pre_start_check(PatientRegistrationDialog, update, context) \
            if not res else res
        if res in [BasicUser.USER_EXCLUDED, BasicUser.USER_IS_PATIENT]:
            return PatientRegistrationDialog.cant_registered(
                update, context, res)
        if res == BasicUser.USER_IS_NOT_REGISTERED:
            if type(context.user_data['user']) is BasicUser:
                context.user_data['user'] = PatientUser(
                    update.effective_chat.id)

            return PatientRegistrationDialog.start(update, context)
        return res

    @staticmethod
    def start(update: Update, context: CallbackContext):
        location = context.user_data['user'].p_loc.location
        code = context.user_data['user'].code
        if location and code:
            text = f'Нажмите "Продолжить", ' \
                   f'чтобы перейти к завершиению регистрации.\n' \
                   f'Ваш код: {code}\nВаш часовой пояс: {location}'
        elif location and not code:
            text = f'Чтобы продолжить регистрацию добавьте Ваш ' \
                   f'персональный код.\nВаш часовой пояс: {location}'
        elif not location and code:
            text = f'Чтобы продолжить регистрацию добавьте Ваш ' \
                   f'часовой пояс.\nВаш код: {code}'
        else:
            text = 'Чтобы продолжить регистрацию добавьте Ваш ' \
                   'персональный код и часовой пояс.'

        buttons = [
            [InlineKeyboardButton(text='Продолжить',
                                  callback_data=f'{CONF_NOTIFICATIONS}')]
            if location and code else '',

            [InlineKeyboardButton(text='Добавить код' if not code else
             'Изменить код', callback_data=f'{CONF_CODE}'),

             InlineKeyboardButton(text='Добавить часовой пояс' if not location
             else 'Изменить часовой пояс', callback_data=f'{CONF_TZ}')],

            # [InlineKeyboardButton(text='Назад', callback_data=f'{END}')]
        ]
        kb = InlineKeyboardMarkup(buttons)

        if not context.user_data.get(START_OVER):
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text,
                                                    reply_markup=kb)
        else:
            try:
                msg = update.effective_chat.send_message(
                    text=text, reply_markup=kb)
                context.chat_data['st_msg'] = msg.message_id
            except error.Unauthorized:
                context.user_data[START_OVER] = False
                return STOPPING
        context.user_data[START_OVER] = False
        return PATIENT_REGISTRATION_ACTION

    @staticmethod
    def conf_code(update: Update, context: CallbackContext):
        text = 'Введите Ваш персональный код.\n' \
               'Формат: [КОД_региона (>2сим)][КОД_врача (3-4cим)]' \
               '[КОД_пациента (>3сим)]'

        if not context.user_data.get(START_OVER):
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text)
        else:
            context.user_data[START_OVER] = False
            try:
                update.message.reply_text(text=text)
            except error.Unauthorized:
                return STOPPING
        return TYPING_CODE

    @staticmethod
    def save_code(update: Update, context: CallbackContext):
        try:
            if update.message:
                context.user_data['user'].set_code(update.message.text)

                context.user_data[START_OVER] = True
                return PatientRegistrationDialog.start(update, context)
        except ValueError:
            pass
        text = 'Код введен в неправильном формате.'
        try:
            update.message.reply_text(text=text)
        except error.Unauthorized:
            return STOPPING
        context.user_data[START_OVER] = True
        return PatientRegistrationDialog.conf_code(update, context)

    @staticmethod
    def end_reg(update: Update, context: CallbackContext):
        user = context.user_data['user']
        try:
            user.validate_code()
        except UserExists as e:
            kb = ReplyKeyboardMarkup([[e.args[1]]], one_time_keyboard=True,
                                     row_width=1, resize_keyboard=True)
            update.callback_query.delete_message()
            update.effective_chat.send_message(text=str(e.args[0]),
                                               reply_markup=kb)
            context.user_data[START_OVER] = True
            return PatientRegistrationDialog.start(update, context)
        except DoctorNotFound as e:
            update.callback_query.edit_message_text(text=str(e))
            context.user_data[START_OVER] = True
            return PatientRegistrationDialog.start(update, context)
        except RegionNotFound as e:
            update.callback_query.edit_message_text(text=str(e))
            context.user_data[START_OVER] = True
            return PatientRegistrationDialog.start(update, context)

        text = f'Поздравляем, вы зарегистрированы в системе!\n\n' \
               f'Теперь каждый день в {user.times.s_times()["MOR"]} ' \
               f'чат-бот напомнит Вам принять ' \
               f'лекарство, а также измерить и сообщить артериальное ' \
               f'давление и частоту сердечных сокращений. \n\n' \
               f'В {user.times.s_times()["EVE"]} ' \
               f'напомнит о необходимости измерить и сообщить ' \
               f'артериальное давление и частоту сердечных сокращений еще раз'

        update.callback_query.answer()
        update.callback_query.delete_message()

        try:
            msg = update.effective_chat.send_message(
                text=text, reply_markup=PatientRegistrationDialog.post_reg_kb)
            # Закрепляем сообщение, чтобы пользователь не потерялся
            update.effective_chat.unpin_all_messages()
            update.effective_chat.pin_message(msg.message_id)
        except error.Unauthorized:
            pass
        # Запускаем регистрацию пользователя
        context.user_data['user'].register(update, context)
        return STOPPING

    @staticmethod
    def cant_registered(update: Update, context: CallbackContext, res):
        context.bot.delete_message(update.effective_chat.id,
                                   context.chat_data['st_msg'])
        try:
            if res == BasicUser.USER_EXCLUDED:
                text = 'Вы были исключены из исследования и не можете ' \
                       'повторно зарегистрироваться.'
                update.effective_chat.send_message(text)
                return STOPPING
            text = 'Вы не можете повторно зарегистрироваться.\n'
            update.effective_chat.send_message(text)
        except error.Unauthorized:
            return STOPPING
        Restore.restore_patient_msg(context, chat_id=update.effective_chat.id)
        return STOPPING

    @staticmethod
    def restore_main_msg(update: Update, context: CallbackContext):
        text = f'Поздравляем, вы зарегистрированы в системе!\n\n' \
               f'Теперь каждый день в ' \
               f'{context.user_data["user"].times.s_times()["MOR"]} ' \
               f'чат-бот напомнит Вам принять ' \
               f'лекарство, а также измерить и сообщить артериальное ' \
               f'давление и частоту сердечных сокращений. \n\n' \
               f'В {context.user_data["user"].times.s_times()["EVE"]} ' \
               f'напомнит о необходимости измерить и сообщить ' \
               f'артериальное давление и частоту сердечных сокращений еще раз'
        try:
            msg = context.bot.send_message(
                update.effective_chat.id, text=text,
                reply_markup=PatientRegistrationDialog.post_reg_kb)
            update.effective_chat.unpin_all_messages()
            update.effective_chat.pin_message(msg.message_id)
        except error.Unauthorized:
            return STOPPING
        context.user_data['user'].enable_user(context)

    @staticmethod
    def back_to_start(update: Update, context: CallbackContext):
        context.user_data[START_OVER] = True
        StartDialog.start(update, context)
        return END


class ConfigureTZDialog(ConversationHandler):
    def __init__(self, loc_d=None, **kwargs):
        from modules.location import FindLocationDialog
        super().__init__(
            name=self.__class__.__name__,
            entry_points=[
                CallbackQueryHandler(self.start, pattern=f'^{CONF_TZ}$')],
            states={
                CONF_TZ_ACTION: [
                    FindLocationDialog() if not loc_d else loc_d(),
                    CallbackQueryHandler(self.conf_tz, pattern=f'^{CONF_TZ}$')
                ],
                TYPING_TZ: [
                    MessageHandler(Filters.text & ~Filters.command &
                                   ~Filters.regex('Настройки$'),
                                   self.save_tz, run_async=False)
                ]
            },
            fallbacks=[
                CallbackQueryHandler(self.back, pattern=f'^{END}$'),
                CommandHandler('stop',
                               StartDialog.stop_nested, run_async=False),
                CommandHandler('start', StartDialog.restart, run_async=False),
                *(kwargs['ex_fallbacks'] if kwargs.get('ex_fallbacks') else [])
            ],
            map_to_parent={
                STOPPING: STOPPING,
                START_SELECTORS: START_SELECTORS
            }
        )

    @staticmethod
    def start(update: Update, context: CallbackContext):

        text = 'Выберите способ добавления часового пояса.'

        location = context.user_data['user'].p_loc.location
        buttons = [
            [
                InlineKeyboardButton(
                    text='Ввести число' if not location or not
                    location.time_zone() else 'Изменить число',
                    callback_data=f'{CONF_TZ}'),

                InlineKeyboardButton(
                    text='Указать местоположение' if not location or not
                    location.location() else 'Изменить местоположение',
                    callback_data=f'{CONF_LOCATION}')
            ],
            [InlineKeyboardButton(text='Назад', callback_data=f'{END}')]
        ]
        kb = InlineKeyboardMarkup(buttons)

        if not context.user_data.get(START_OVER):
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text,
                                                    reply_markup=kb)
        else:
            try:
                msg = update.message.reply_text(text=text, reply_markup=kb)
                context.chat_data['st_msg'] = msg.message_id
            except error.Unauthorized:
                return STOPPING
        context.user_data[START_OVER] = False
        return CONF_TZ_ACTION

    @staticmethod
    def conf_tz(update: Update, context: CallbackContext):
        text = 'Введите Ваш часовой пояс в следующем формате:\n ' \
               '+(-){Ваш часовой пояс}\nПример: +3'
        if not context.user_data.get(START_OVER):
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text)
        else:
            context.user_data[START_OVER] = False
            try:
                update.message.reply_text(text=text)
            except error.Unauthorized:
                return STOPPING
        return TYPING_TZ

    @staticmethod
    def save_tz(update: Update, context: CallbackContext, ret=None):
        from modules.location import Location
        msg = update.message.text
        try:
            context.user_data['user'].p_loc.location = Location(tz=msg)

            if not ret:
                context.user_data[START_OVER] = True
                return ConfigureTZDialog.back(update, context)
            return ret(update, context)
        except ValueError:
            text = 'Часовой пояс был введен в неправильном формате. ' \
                   'Попробуйте снова.'
            try:
                update.message.reply_text(text=text)
            except error.Unauthorized:
                return STOPPING

            context.user_data[START_OVER] = True
            return ConfigureTZDialog.conf_tz(update, context)

    @staticmethod
    def back(update: Update, context: CallbackContext):
        PatientRegistrationDialog.start(update, context)
        return END


class ConfigureNotifTimeDialog(ConversationHandler):
    buttons = [
        [
            InlineKeyboardButton(text='-15 мин', callback_data='-15'),
            InlineKeyboardButton(text='-30 мин', callback_data='-30'),
            InlineKeyboardButton(text='+30 мин', callback_data='+30'),
            InlineKeyboardButton(text='+15 мин', callback_data='+15'),
        ],
        [InlineKeyboardButton(text='Назад', callback_data=f'{END}')]
    ]

    def __init__(self, **kwargs):
        from modules.settings_dialogs import SettingsDialog
        super().__init__(
            name=self.__class__.__name__,
            entry_points=[CallbackQueryHandler(
                self.start, pattern=f'^{CONF_NOTIFICATIONS}$')],
            states={
                CONF_NOTIF_ACTIONS: [
                    CallbackQueryHandler(self.conf_time,
                                         pattern=f'^MORNING_TIME$|'
                                                 f'^EVENING_TIME$')
                ],
                TIME_CHANGE: [
                    CallbackQueryHandler(self.time_change,
                                         pattern='[-+]\\d{2}'),
                    CallbackQueryHandler(self.start, pattern=f'^{END}$')
                ]
            },
            fallbacks=[
                CallbackQueryHandler(PatientRegistrationDialog.end_reg,
                                     pattern=f'^{FINISH_REGISTRATION}$',
                                     run_async=False),
                CallbackQueryHandler(self.back, pattern=f'^{END}$'),
                CommandHandler('stop', StartDialog.stop_nested if not
                               kwargs.get('stop_cb') else
                               kwargs.get('stop_cb'), run_async=False),
                CommandHandler('start', StartDialog.restart, run_async=False),
                MessageHandler(Filters.regex('Настройки$'),
                               SettingsDialog.restart, run_async=False)

            ],
            map_to_parent={
                STOPPING: STOPPING,
                START_SELECTORS: START_SELECTORS,
                PATIENT_REGISTRATION_ACTION: PATIENT_REGISTRATION_ACTION,
            }
        )

    @staticmethod
    def start(update: Update, context: CallbackContext, t=None):

        text = f'Настройте время получения напоминаний (время МЕСТНОЕ) или ' \
               f'завершите регистрацию, нажав кнопку \n' \
               f'"Завершить регистрацию" \n\n' \
               f'Время получения утреннего уведомления: ' \
               f'{context.user_data["user"].times.s_times()["MOR"]}\n' \
               f'Время получения вечернего уведомления: ' \
               f'{context.user_data["user"].times.s_times()["EVE"]}' \
            if not t else t

        buttons = [
            [InlineKeyboardButton(text='Завершить регистрацию',
                                  callback_data=f'{FINISH_REGISTRATION}')]
            if not t else '',

            [InlineKeyboardButton(text='Изменить утреннее время',
                                  callback_data=f'MORNING_TIME'),
             InlineKeyboardButton(text='Изменить вечернее время',
                                  callback_data=f'EVENING_TIME')],

            [InlineKeyboardButton(text='Назад', callback_data=f'{END}')]
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text,
                                                reply_markup=keyboard)
        return CONF_NOTIF_ACTIONS

    @staticmethod
    def conf_time(update: Update, context: CallbackContext):
        tm = update.callback_query.data[:3]
        context.user_data['tm'] = tm

        if tm == 'MOR':
            text = f'Изменение времени получения утренних уведомлений.\n'
        else:
            text = f'Изменение времени получения вечерних уведомлений.\n'
        text += f'Время: {context.user_data["user"].times.s_times()[tm]}'

        keyboard = InlineKeyboardMarkup(ConfigureNotifTimeDialog.buttons)

        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text,
                                                reply_markup=keyboard)
        return TIME_CHANGE

    @staticmethod
    def time_change(update: Update, context: CallbackContext):
        tm = context.user_data['tm']
        res = context.user_data['user'].times.add_minutes(
            tm, update.callback_query.data)

        text = f'''Изменение времени получения {"вечерних" 
        if tm == "EVE" else "утренних"} уведомлений.\n'''

        if not res and context.user_data.get('lim'):
            return TIME_CHANGE

        if not res:
            text += f'Крайне время: ' \
                    f'{context.user_data["user"].times.s_times()[tm]}'
            context.user_data['lim'] = True
        else:
            text += f'Время: {context.user_data["user"].times.s_times()[tm]}'
            context.user_data['lim'] = False

        keyboard = InlineKeyboardMarkup(ConfigureNotifTimeDialog.buttons)

        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text,
                                                reply_markup=keyboard)
        return TIME_CHANGE

    @staticmethod
    def back(update: Update, context: CallbackContext):
        PatientRegistrationDialog.start(update, context)
        return END


class DoctorRegistrationDialog(ConversationHandler):
    def __init__(self, **kwargs):
        super().__init__(
            name=self.__class__.__name__,
            entry_points=[CallbackQueryHandler(self.pre_start,
                          pattern=f'^{SIGN_UP_AS_DOCTOR}$'
                          if not kwargs.get('patt') else kwargs['patt'],
                                               run_async=False)],
            states={
                TYPING_TOKEN: [
                    MessageHandler(Filters.text & ~Filters.command,
                                   self.get_token, run_async=False)],
                TYPING_CODE: [
                    MessageHandler(Filters.text & ~Filters.command,
                                   self.save_code, run_async=False)
                ]
            },
            fallbacks=[
                CommandHandler('stop', StartDialog.stop_nested,
                               run_async=False),
                CallbackQueryHandler(PatientRegistrationDialog.back_to_start,
                                     pattern=f'^{END}$'),
                CommandHandler('start', StartDialog.restart, run_async=False)
            ],
            map_to_parent={
                START_SELECTORS: START_SELECTORS,
                STOPPING: END,
                END: END
            }
        )

    @staticmethod
    @not_registered_users
    def pre_start(update: Update, context: CallbackContext, res=None):
        res = pre_start_check(DoctorRegistrationDialog, update, context)\
            if not res else res
        if res == BasicUser.USER_IS_DOCTOR:
            text = 'Вы не можете повторно зарегистрироваться.\n'
            try:
                context.bot.edit_message_text(text, update.effective_chat.id,
                                              context.chat_data['st_msg'],
                                              reply_markup=None)
            except error.Unauthorized:
                return STOPPING
            Restore.restore_doctor_msg(
                context, chat_id=update.effective_chat.id)
            return STOPPING
        if res == BasicUser.USER_IS_NOT_REGISTERED:
            if type(context.user_data['user']) is BasicUser:
                context.user_data['user'] = DoctorUser(
                    update.effective_chat.id)

            return DoctorRegistrationDialog.start(update, context)
        return res

    @staticmethod
    def start(update: Update, context: CallbackContext):
        text = f'Введите токен для регистрации.'

        context.bot.delete_message(update.effective_chat.id,
                                   context.chat_data['st_msg'])
        try:
            msg = update.effective_chat.send_message(text=text)
            context.chat_data['st_msg'] = msg.message_id
        except error.Unauthorized:
            return STOPPING
        return TYPING_TOKEN

    @classmethod
    def get_token(cls, update: Update, context: CallbackContext):
        token = update.message.text
        try:
            if token == get_from_env('DOCTOR_TOKEN'):
                context.user_data[START_OVER] = True
                return cls.conf_code(update, context)
            update.message.reply_text('Неверный токен.\nПопробуйте снова.')
        except error.Unauthorized:
            return STOPPING
        return TYPING_TOKEN

    @staticmethod
    def conf_code(update: Update, context: CallbackContext):
        text = 'Введите Ваш персональный код.\n' \
               'Формат: [КОД_региона (>2сим)][КОД_врача (3-4сим)]'

        if not context.user_data.get(START_OVER):
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text)
        else:
            context.user_data[START_OVER] = False
            try:
                msg = update.message.reply_text(text=text)
                context.chat_data['st_msg'] = msg.message_id
            except error.Unauthorized:
                return STOPPING
        return TYPING_CODE

    @classmethod
    def save_code(cls, update: Update, context: CallbackContext):
        try:
            if update.message:
                context.user_data['user'].set_code(update.message.text)
                return cls.end_reg(update, context)
        except ValueError as e:
            try:
                update.message.reply_text(text=str(e))
            except error.Unauthorized:
                return STOPPING
            context.user_data[START_OVER] = True
            return cls.conf_code(update, context)

    @classmethod
    def end_reg(cls, update: Update, context: CallbackContext):
        user = context.user_data['user']
        try:
            user.validate_code()
        except UserExists as e:
            kb = ReplyKeyboardMarkup([[e.args[1]]], one_time_keyboard=True,
                                     row_width=1, resize_keyboard=True)
            update.effective_chat.send_message(text=str(e.args[0]),
                                               reply_markup=kb)
            context.user_data[START_OVER] = True
            return cls.conf_code(update, context)
        except (RegionNotFound, ValueError) as e:
            update.effective_chat.send_message(text=str(e))
            context.user_data[START_OVER] = True
            return cls.conf_code(update, context)

        try:
            text = f'Вы успешно зарегестрированы!\n'
            update.effective_chat.send_message(text=text)
            DoctorJob.default_job(update, context)
        except error.Unauthorized:
            pass

        context.user_data['user'].register(update, context)
        return END


class RegionRegistrationDialog(DoctorRegistrationDialog):
    def __init__(self):
        super().__init__(patt=f'^{SIGN_UP_AS_REGION}$')

    @staticmethod
    @not_registered_users
    def pre_start(update: Update, context: CallbackContext, res=None):
        res = pre_start_check(RegionRegistrationDialog, update, context) \
            if not res else res
        if res == BasicUser.USER_IS_REGION:
            text = 'Вы не можете повторно зарегистрироваться.\n'
            try:
                context.bot.edit_message_text(text, update.effective_chat.id,
                                              context.chat_data['st_msg'],
                                              reply_markup=None)
            except error.Unauthorized:
                return STOPPING
            Restore.restore_region_msg(
                context, chat_id=update.effective_chat.id)
            return STOPPING
        if res == BasicUser.USER_IS_NOT_REGISTERED:
            if type(context.user_data['user']) is BasicUser:
                context.user_data['user'] = RegionUser(
                    update.effective_chat.id)

            return RegionRegistrationDialog.start(update, context)
        return res

    @classmethod
    def get_token(cls, update: Update, context: CallbackContext):
        token = update.message.text
        try:
            if token == get_from_env('REGION_TOKEN'):
                context.user_data[START_OVER] = True
                return cls.conf_code(update, context)
            update.message.reply_text('Неверный токен.\nПопробуйте снова.')
        except error.Unauthorized:
            return STOPPING
        return TYPING_TOKEN

    @staticmethod
    def conf_code(update: Update, context: CallbackContext):
        text = 'Введите Ваш персональный код.\n' \
               'Формат: [КОД_региона (>2сим)]'

        if not context.user_data.get(START_OVER):
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text)
        else:
            context.user_data[START_OVER] = False
            try:
                msg = update.message.reply_text(text=text)
                context.chat_data['st_msg'] = msg.message_id
            except error.Unauthorized:
                return STOPPING
        return TYPING_CODE

    @classmethod
    def end_reg(cls, update: Update, context: CallbackContext):
        try:
            context.user_data['user'].validate_code()
        except UserExists as e:
            kb = ReplyKeyboardMarkup([[e.args[1]]], one_time_keyboard=True,
                                     row_width=1, resize_keyboard=True)
            update.effective_chat.send_message(text=str(e.args[0]),
                                               reply_markup=kb)
            context.user_data[START_OVER] = True
            return cls.conf_code(update, context)
        except (RegionNotFound, ValueError) as e:
            update.effective_chat.send_message(text=str(e))
            context.user_data[START_OVER] = True
            return cls.conf_code(update, context)

        try:
            text = f'Вы успешно зарегестрированы!\n'
            update.effective_chat.send_message(text=text)
            RegionJob.default_job(update, context)
        except error.Unauthorized:
            pass

        context.user_data['user'].register(update, context)
        return END


class UniRegistrationDialog(ConversationHandler):
    def __init__(self):
        super().__init__(
            name=self.__class__.__name__,
            entry_points=[CallbackQueryHandler(self.pre_start,
                          pattern=f'^{SIGN_UP_AS_UNIVERSITY}$',
                                               run_async=False)],
            states={
                TYPING_TOKEN: [
                    MessageHandler(Filters.text & ~Filters.command,
                                   self.get_token, run_async=False)]
            },
            fallbacks=[
                CommandHandler('stop', StartDialog.stop_nested,
                               run_async=False),
                CallbackQueryHandler(PatientRegistrationDialog.back_to_start,
                                     pattern=f'^{END}$'),
                CommandHandler('start', StartDialog.restart, run_async=False)
            ],
            map_to_parent={
                START_SELECTORS: START_SELECTORS,
                STOPPING: END,
                END: END
            }
        )

    @staticmethod
    @not_registered_users
    def pre_start(update: Update, context: CallbackContext, res=None):
        res = pre_start_check(UniRegistrationDialog, update, context) \
            if not res else res
        if res == BasicUser.USER_IS_UNI:
            text = 'Вы не можете повторно зарегистрироваться.\n'
            try:
                context.bot.edit_message_text(text, update.effective_chat.id,
                                              context.chat_data['st_msg'],
                                              reply_markup=None)
            except error.Unauthorized:
                return STOPPING
            Restore.restore_uni_msg(context, chat_id=update.effective_chat.id)
            return STOPPING
        if res == BasicUser.USER_IS_NOT_REGISTERED:
            if type(context.user_data['user']) is BasicUser:
                context.user_data['user'] = UniUser(update.effective_chat.id)

            return DoctorRegistrationDialog.start(update, context)
        return res

    @classmethod
    def get_token(cls, update: Update, context: CallbackContext):
        token = update.message.text
        try:
            if token == get_from_env('UNIVERSITY_TOKEN'):
                context.user_data[START_OVER] = True

                text = f'Вы успешно зарегестрированы!\n'
                update.effective_chat.send_message(text=text)
                UniJob.default_job(update, context)

                context.user_data['user'].register(update, context)
                return END
            update.message.reply_text('Неверный токен.\nПопробуйте снова.')
        except error.Unauthorized:
            return STOPPING
        return TYPING_TOKEN
