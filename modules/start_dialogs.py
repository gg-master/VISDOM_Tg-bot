from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, \
    InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    CallbackContext, CommandHandler, MessageHandler,
    Filters, CallbackQueryHandler,
)

from modules.users_classes import BasicUser, PatientUser
from tools.prepared_answers import START_MSG
from modules.dialogs_shortcuts.start_shortcuts import *
from tools.decorators import not_registered_users


class StartDialog(ConversationHandler):
    def __init__(self):
        super().__init__(
            name=self.__class__.__name__,
            entry_points=[CommandHandler('start', self.start)],
            states={
                START_SELECTORS: [PatientRegistrationDialog(),
                                  PatronageRegistrationDialog()],
            },
            fallbacks=[CommandHandler('stop', self.stop)])

    @staticmethod
    @not_registered_users
    def start(update: Update, context: CallbackContext):
        if not context.user_data.get('user'):
            context.user_data['user'] = BasicUser()

        buttons = [
            [InlineKeyboardButton(text='Зарегистрироваться',
                                  callback_data=f'{SIGN_UP_AS_PATIENT}')],
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        text = 'Чтобы начать пользоваться Чат-Ботом ' \
               'необходимо зарегистрироваться.'

        if context.user_data.get(START_OVER):
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text,
                                                    reply_markup=keyboard)
        else:
            update.message.reply_text(
                START_MSG, reply_markup=ReplyKeyboardRemove())
            msg = update.message.reply_text(text=text, reply_markup=keyboard)
            context.chat_data['st_msg'] = msg.message_id
        context.user_data[START_OVER] = False
        return START_SELECTORS

    @staticmethod
    def stop(update: Update, context: CallbackContext):
        keyboard = ReplyKeyboardMarkup([['/start']])
        update.message.reply_text(text='Регистрация прервана.\nЧтобы повторно '
                                       'начать регистрацию отправьте:\n/start',
                                  reply_markup=keyboard)
        return END

    @staticmethod
    def stop_nested(update: Update, context: CallbackContext):
        StartDialog.stop(update, context)
        return STOPPING


class PatientRegistrationDialog(ConversationHandler):
    def __init__(self):
        super().__init__(
            name=self.__class__.__name__,
            entry_points=[CallbackQueryHandler(
                self.start, pattern=f'^{SIGN_UP_AS_PATIENT}$')],
            states={
                PATIENT_REGISTRATION_ACTION: [
                    ConfigureTZDialog(),
                    ConfigureNotifTimeDialog(),
                    CallbackQueryHandler(self.conf_code,
                                         pattern=f'^{CONF_CODE}$'),
                    CallbackQueryHandler(self.end_reg,
                                         pattern=f'^{FINISH_REGISTRATION}$',
                                         run_async=False),
                ],
                TYPING_CODE: [
                    MessageHandler(Filters.text & ~Filters.command,
                                   self.save_code)
                ],
            },
            fallbacks=[
                CallbackQueryHandler(self.back_to_start, pattern=f'^{END}$'),
                CommandHandler('stop', StartDialog.stop_nested,
                               run_async=False),
            ],
            map_to_parent={
                STOPPING: END,
            }
        )

    @staticmethod
    def start(update: Update, context: CallbackContext):
        if type(context.user_data['user']) is BasicUser:
            context.user_data['user'] = PatientUser()

        location = context.user_data['user'].location
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
            [InlineKeyboardButton(text="Продолжить",
                                  callback_data=f'{CONF_NOTIFICATIONS}')]
            if location and code else '',

            [InlineKeyboardButton(text='Добавить код' if not code else
             'Изменить код', callback_data=f'{CONF_CODE}'),

             InlineKeyboardButton(text='Добавить часовой пояс' if not location
             else 'Изменить часовой пояс', callback_data=f'{CONF_TZ}')],

            # [InlineKeyboardButton(text='Назад', callback_data=f'{END}')]
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        if not context.user_data.get(REGISTRATION_OVER):
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text,
                                                    reply_markup=keyboard)
        else:
            update.message.reply_text(text=text, reply_markup=keyboard)

        context.user_data[REGISTRATION_OVER] = False
        return PATIENT_REGISTRATION_ACTION

    @staticmethod
    def conf_code(update: Update, context: CallbackContext):
        text = 'Введите Ваш персональный код'
        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text)
        return TYPING_CODE

    @staticmethod
    def save_code(update: Update, context: CallbackContext):
        context.user_data['user'].code = update.message.text
        context.user_data[REGISTRATION_OVER] = True
        return PatientRegistrationDialog.start(update, context)

    @staticmethod
    def end_reg(update: Update, context: CallbackContext):
        text = f"Поздравляем, вы зарегистрированы в системе!\n\n" \
               f"Теперь каждый день в " \
               f"{context.user_data['user'].times()['MOR']} " \
               f"чат-бот напомнит Вам принять " \
               f"лекарство, а также измерить и сообщить артериальное " \
               f"давление и частоту сердечных сокращений. \n\n" \
               f"В {context.user_data['user'].times()['EVE']} " \
               f"напомнит о необходимости измерить и сообщить " \
               f"артериальное давление и частоту сердечных сокращений еще раз"

        update.callback_query.answer()
        update.callback_query.delete_message()

        # TODO добавить кнопки для обычного общения с системой
        keyboard = ReplyKeyboardMarkup(
            [['Справка', 'Настройки']], row_width=1, resize_keyboard=True)

        context.bot.send_message(
            update.effective_chat.id, text=text, reply_markup=keyboard)

        context.user_data['user'].register(update, context)
        return STOPPING

    @staticmethod
    def back_to_start(update: Update, context: CallbackContext):
        context.user_data[START_OVER] = True
        StartDialog.start(update, context)
        return END


class ConfigureTZDialog(ConversationHandler):
    def __init__(self, loc_d=None):
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
                    MessageHandler(Filters.text & ~Filters.command,
                                   self.save_tz)
                ]
            },
            fallbacks=[
                CallbackQueryHandler(self.back, pattern=f'^{END}$'),
                CommandHandler('stop', StartDialog.stop_nested,
                               run_async=False)
            ],
            map_to_parent={STOPPING: STOPPING}
        )

    @staticmethod
    def start(update: Update, context: CallbackContext):

        text = 'Выберите способ добавления часового пояса.'

        location = context.user_data['user'].location
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
        keyboard = InlineKeyboardMarkup(buttons)

        if not context.user_data.get(CONF_TZ_OVER):
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text,
                                                    reply_markup=keyboard)
        else:
            update.message.reply_text(text=text, reply_markup=keyboard)

        context.user_data[CONF_TZ_OVER] = False
        return CONF_TZ_ACTION

    @staticmethod
    def conf_tz(update: Update, context: CallbackContext):
        text = 'Введите Ваш часовой пояс в следующем формате: +3 или -3'
        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text)
        return TYPING_TZ

    @staticmethod
    def save_tz(update: Update, context: CallbackContext, self=None):
        from modules.location import Location
        msg = update.message.text
        try:
            context.user_data['user'].location = Location(tz=msg)

            context.user_data[REGISTRATION_OVER] = True

            if not self:
                return ConfigureTZDialog.back(update, context)
        except ValueError:
            context.user_data[CONF_TZ_OVER] = True
            text = 'Часовой пояс был введен в неправильном формате. ' \
                   'Попробуйте снова.'
            update.message.reply_text(text=text)

            if not self:
                return ConfigureTZDialog.start(update, context)

    @staticmethod
    def back(update: Update, context: CallbackContext):
        PatientRegistrationDialog.start(update, context)
        return END


class ConfigureNotifTimeDialog(ConversationHandler):
    buttons = [
        [
            InlineKeyboardButton(text="-15 мин", callback_data='-15'),
            InlineKeyboardButton(text='-30 мин', callback_data='-30'),
            InlineKeyboardButton(text='+30 мин', callback_data='+30'),
            InlineKeyboardButton(text='+15 мин', callback_data='+15'),
        ],
        [InlineKeyboardButton(text='Назад', callback_data=f'{END}')]
    ]

    def __init__(self):
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
                CallbackQueryHandler(self.back, pattern=f'^{END}$'),
                CommandHandler('stop', StartDialog.stop_nested,
                               run_async=False),
            ],
            map_to_parent={
                STOPPING: STOPPING
            }
        )

    @staticmethod
    def start(update: Update, context: CallbackContext, t=None):

        text = f'Настройте время получения напоминаний (время МЕСТНОЕ) или ' \
               f'завершите регистрацию, нажав кнопку \n' \
               f'"Завершить регистрацию" \n\n' \
               f'Время получения утреннего уведомления: ' \
               f'{context.user_data["user"].times()["MOR"]}\n' \
               f'Время получения вечернего уведомления: ' \
               f'{context.user_data["user"].times()["EVE"]}' \
            if not t else t

        buttons = [
            [InlineKeyboardButton(text="Завершить регистрацию",
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
        text += f'Время: {context.user_data["user"].times()[tm]}'

        keyboard = InlineKeyboardMarkup(ConfigureNotifTimeDialog.buttons)

        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text,
                                                reply_markup=keyboard)
        return TIME_CHANGE

    @staticmethod
    def time_change(update: Update, context: CallbackContext):
        tm = context.user_data['tm']
        res = context.user_data["user"].add_minutes(tm, update.callback_query.data)

        text = f'Изменение времени получения ' \
               f'{"вечерних" if context.user_data["tm"] == "EVE" else "утренних"}' \
               f' уведомлений.\n'

        if not res and context.user_data.get('lim'):
            return TIME_CHANGE

        if not res:
            text += f'Крайне время: {context.user_data["user"].times()[tm]}'
            context.user_data['lim'] = True
        else:
            text += f'Время: {context.user_data["user"].times()[tm]}'
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


class PatronageRegistrationDialog(ConversationHandler):
    def __init__(self):
        super().__init__(
            entry_points=[CallbackQueryHandler(self.start,
                                               pattern=f'^{SIGN_UP_AS_CC1}$'),
                          CommandHandler('reg_patronage', self.start)],
            states={
                PATRONAGE_REGISTRATION_ACTION: [

                ],
            },
            fallbacks=[
                CommandHandler('stop', StartDialog.stop_nested,
                               run_async=False),
                CallbackQueryHandler(PatientRegistrationDialog.back_to_start,
                                     pattern=f'^{END}$')
            ],
            map_to_parent={
                STOPPING: END,
            }
        )

    @staticmethod
    def start(update: Update, context: CallbackContext):
        text = 'Регистрация персонала. (В разработке)'

        # buttons = [
        #     [InlineKeyboardButton(text='Назад', callback_data=f'{END}')]
        # ]
        # keyboard = InlineKeyboardMarkup(buttons)

        if context.user_data.get(REGISTRATION_OVER):
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text)
        else:
            context.bot.delete_message(update.message.chat_id,
                                       context.chat_data['st_msg'])
            update.message.reply_text(text=text)

        context.user_data[REGISTRATION_OVER] = False
        return PATRONAGE_REGISTRATION_ACTION
