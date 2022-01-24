import datetime as dt
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, \
    InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    CallbackContext, CommandHandler, MessageHandler,
    Filters, CallbackQueryHandler,
)

from modules.prepared_answers import START_MSG
from modules.dialogs_shortcuts.start_shortcuts import *
from tools.decorators import not_registered_users


class StartDialog(ConversationHandler):
    def __init__(self):
        super().__init__(
            name=self.__class__.__name__,
            entry_points=[CommandHandler('start', self.start)],
            states={
                START_SELECTORS: [PatientRegistrationDialog(),
                                  CC1RegistrationDialog()],
            },
            fallbacks=[CommandHandler('stop', self.stop)])

    @staticmethod
    @not_registered_users
    def start(update: Update, context: CallbackContext):
        context.user_data['is_registered'] = False

        buttons = [
            [InlineKeyboardButton(text='Зарегистрироваться как пациент',
                                  callback_data=f'{SIGN_UP_AS_PATIENT}')],
            [InlineKeyboardButton(text='Зарегистрироваться как сотрудник',
                                  callback_data=f'{SIGN_UP_AS_CC1}')]
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        text = 'Чтобы продолжить пользоваться Чат-Ботом вам ' \
               'необходимо зарегистрироваться. \n' \
               'Выберите способ входа.'

        if context.user_data.get(START_OVER):
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text,
                                                    reply_markup=keyboard)
        else:
            update.message.reply_text(
                START_MSG, reply_markup=ReplyKeyboardRemove())
            update.message.reply_text(text=text, reply_markup=keyboard)
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
        keyboard = ReplyKeyboardMarkup([['/start']])
        update.message.reply_text(text='Регистрация прервана.\nЧтобы повторно '
                                       'начать регистрацию отправьте:\n/start',
                                  reply_markup=keyboard)
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
        # Если понадобится стирать данные при переключении из диалогов
        # if not context.user_data.get(REGISTRATION_OVER) \
        #         and not context.user_data.get('TIMES'):
        #     context.user_data['location'] = context.user_data['code'] = None

        location = context.user_data.get('location')
        code = context.user_data.get('code')
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

            [InlineKeyboardButton(text='Назад', callback_data=f'{END}')]
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
        update.callback_query.answer()

        text = 'Введите Ваш персональный код'
        update.callback_query.edit_message_text(text=text)
        return TYPING_CODE

    @staticmethod
    def save_code(update: Update, context: CallbackContext):
        context.user_data['code'] = update.message.text
        context.user_data[REGISTRATION_OVER] = True
        return PatientRegistrationDialog.start(update, context)

    @staticmethod
    def end_reg(update: Update, context: CallbackContext):
        context.user_data['is_registered'] = True

        text = f"Поздравляем, вы зарегистрированы в системе!\n\n" \
               f"Теперь каждый день в " \
               f"{context.user_data['TIMES']['MOR'].strftime('%H:%M')} " \
               f"чат-бот напомнит Вам принять " \
               f"лекарство, а также измерить и сообщить артериальное " \
               f"давление и частоту сердечных сокращений. \n\n" \
               f"В {context.user_data['TIMES']['EVE'].strftime('%H:%M')} " \
               f"напомнит о необходимости измерить и сообщить " \
               f"артериальное давление и частоту сердечных сокращений еще раз"

        update.callback_query.answer()
        update.callback_query.delete_message()

        # TODO добавить кнопки для обычного общения с системой
        keyboard = ReplyKeyboardMarkup(
            [['/help', '/settings']], row_width=1, resize_keyboard=True)

        context.bot.send_message(
            update.effective_chat.id, text=text, reply_markup=keyboard)
        return STOPPING

    @staticmethod
    def back_to_start(update: Update, context: CallbackContext):
        context.user_data[START_OVER] = True
        StartDialog.start(update, context)
        return END


class ConfigureTZDialog(ConversationHandler):
    def __init__(self):
        from modules.location import FindLocationDialog
        super().__init__(
            entry_points=[
                CallbackQueryHandler(self.start, pattern=f'^{CONF_TZ}$')],
            states={
                CONF_TZ_ACTION: [
                    FindLocationDialog(),
                    CallbackQueryHandler(self.conf_tz, pattern=f'^{CONF_TZ}$')
                ],
                TYPING_TZ: [
                    MessageHandler(Filters.text & ~Filters.command,
                                   self.save_tz)
                ]
            },
            fallbacks=[
                CallbackQueryHandler(self.back_to_reg, pattern=f'^{END}$'),
                CommandHandler('stop', StartDialog.stop_nested,
                               run_async=False)
            ],
            map_to_parent={STOPPING: STOPPING}
        )

    @staticmethod
    def start(update: Update, context: CallbackContext):

        text = 'Выберите способ добавления часового пояса.'

        location = context.user_data.get('location')
        buttons = [
            [
                InlineKeyboardButton(
                    text='Ввести число' if not location or not
                    location.get_time_delta()
                    else 'Изменить число', callback_data=f'{CONF_TZ}'),

                InlineKeyboardButton(
                    text='Указать местоположение' if not location or not
                    location.get_location() else 'Изменить местоположение',
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
        update.callback_query.answer()

        text = 'Введите Ваш чаоовой пояс в следующем формате: +3 или -3'
        update.callback_query.edit_message_text(text=text)
        return TYPING_TZ

    @staticmethod
    def save_tz(update: Update, context: CallbackContext):
        from modules.location import Location
        msg = update.message.text

        if msg[0] not in ('+', '-') or not msg[1:].isdigit() or \
                not (-10 <= int(msg[1:]) <= 10):
            context.user_data[CONF_TZ_OVER] = True
            text = 'Часовой пояс был введен в неправильном формате. ' \
                   'Попробуйте снова.'
            update.message.reply_text(text=text)
            return ConfigureTZDialog.start(update, context)

        context.user_data['location'] = Location(time_delta=msg)
        context.user_data[REGISTRATION_OVER] = True
        PatientRegistrationDialog.start(update, context)
        return END

    @staticmethod
    def back_to_reg(update: Update, context: CallbackContext):
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
                    CallbackQueryHandler(self.conf_morning_time,
                                         pattern=f'^{MORNING_TIME}$'),
                    CallbackQueryHandler(self.conf_evening_time,
                                         pattern=f'^{EVENING_TIME}$'),
                ],
                TIME_CHANGE: [
                    CallbackQueryHandler(self.time_change, pattern='[-+]\\d{2}')
                ]
            },
            fallbacks=[
                CallbackQueryHandler(self.back_to_reg, pattern=f'^{END}$'),
                CommandHandler('stop', StartDialog.stop_nested,
                               run_async=False),
            ],
            map_to_parent={
                STOPPING: STOPPING
            }
        )

    @staticmethod
    def start(update: Update, context: CallbackContext):
        if not context.user_data.get('TIMES'):
            mor = dt.datetime(1212, 12, 12, 8, 00, 0)
            eve = dt.datetime(1212, 12, 12, 20, 00, 0)
            context.user_data['TIMES'] = {'MOR': mor, 'EVE': eve}

        text = f'Настройте время получения напоминаний (время МЕСТНОЕ) или ' \
               f'завершите регистрацию, нажав кнопку \n' \
               f'"Завершить регистрацию" \n\n' \
               f'Время получения утреннего уведомления: ' \
               f'{context.user_data["TIMES"]["MOR"].strftime("%H:%M")}\n' \
               f'Время получения вечернего уведомления: ' \
               f'{context.user_data["TIMES"]["EVE"].strftime("%H:%M")}'

        buttons = [
            [InlineKeyboardButton(text="Завершить регистрацию",
                                  callback_data=f'{FINISH_REGISTRATION}')],

            [InlineKeyboardButton(text='Изменить утреннее время',
                                  callback_data=f'{MORNING_TIME}'),
             InlineKeyboardButton(text='Изменить вечернее время',
                                  callback_data=f'{EVENING_TIME}')],

            [InlineKeyboardButton(text='Назад', callback_data=f'{END}')]
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text,
                                                reply_markup=keyboard)
        return CONF_NOTIF_ACTIONS

    @staticmethod
    def conf_morning_time(update: Update, context: CallbackContext):
        context.user_data['TIME_CHANGE'] = 'MOR'

        text = f'Изменение времени получения утренних уведомлений.\n' \
               f'Время: {context.user_data["TIMES"]["MOR"].strftime("%H:%M")}'

        keyboard = InlineKeyboardMarkup(ConfigureNotifTimeDialog.buttons)

        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text,
                                                reply_markup=keyboard)
        return TIME_CHANGE

    @staticmethod
    def conf_evening_time(update: Update, context: CallbackContext):
        context.user_data['TIME_CHANGE'] = 'EVE'

        text = f'Изменение времени получения вечерних уведомлений.\n' \
               f'Время: {context.user_data["TIMES"]["EVE"].strftime("%H:%M")}'

        keyboard = InlineKeyboardMarkup(ConfigureNotifTimeDialog.buttons)

        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text,
                                                reply_markup=keyboard)
        return TIME_CHANGE

    @staticmethod
    def time_change(update: Update, context: CallbackContext):
        delta = dt.timedelta(minutes=int(update.callback_query.data))
        time = context.user_data["TIMES"][context.user_data['TIME_CHANGE']]

        time += delta

        context.user_data['TIMES'][context.user_data['TIME_CHANGE']] = time

        text = f'Изменение времени получения ' \
               f'{"вечерних" if context.user_data["TIME_CHANGE"] == "EVE" else "утренних"}  ' \
               f'уведомлений.\nВремя: {time.strftime("%H:%M")}'

        keyboard = InlineKeyboardMarkup(ConfigureNotifTimeDialog.buttons)

        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text,
                                                reply_markup=keyboard)
        return TIME_CHANGE

    @staticmethod
    def back_to_reg(update: Update, context: CallbackContext):
        return ConfigureNotifTimeDialog.start(update, context)


class CC1RegistrationDialog(ConversationHandler):
    def __init__(self):
        super().__init__(
            entry_points=[CallbackQueryHandler(self.start,
                                               pattern=f'^{SIGN_UP_AS_CC1}$')],
            states={
                CC1_REGISTRATION_ACTION: [

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

        buttons = [
            [InlineKeyboardButton(text='Назад', callback_data=f'{END}')]
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        if not context.user_data.get(REGISTRATION_OVER):
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text,
                                                    reply_markup=keyboard)
        else:
            update.message.reply_text(text=text, reply_markup=keyboard)

        context.user_data[REGISTRATION_OVER] = False
        return CC1_REGISTRATION_ACTION
