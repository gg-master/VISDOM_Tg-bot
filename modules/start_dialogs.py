from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    CallbackContext, ConversationHandler, CommandHandler, MessageHandler,
    Filters, CallbackQueryHandler,
)

from modules.prepared_answers import START_MSG, SUCCESSFUL_REG
from modules.dialog_states.start_states import *
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
            name='PatientRegistrationDialog',
            entry_points=[CallbackQueryHandler(
                self.start, pattern=f'^{SIGN_UP_AS_PATIENT}$')],
            states={
                PATIENT_REGISTRATION_ACTION: [
                    ConfigureTZDialog(),
                    CallbackQueryHandler(self.conf_code,
                                         pattern=f'^{CONF_CODE}$'),
                    CallbackQueryHandler(self.end_reg, pattern=f'^{END}$')
                ],
                TYPING_CODE: [
                    MessageHandler(Filters.text & ~Filters.command,
                                   self.save_code)
                ],
            },
            fallbacks=[
                CallbackQueryHandler(self.back_to_start, pattern=f'^{BACK}$'),
                CommandHandler('stop', StartDialog.stop_nested, run_async=False),
            ],
            map_to_parent={
                STOPPING: END
            }
        )

    @staticmethod
    def start(update: Update, context: CallbackContext):
        location = context.user_data.get('location')
        code = context.user_data.get('code')
        if location and code:
            text = f'Нажмите "Завершить регистрацию", ' \
                   f'чтобы завершить регистрацию.\n' \
                   f'Ваш код: {code}\nВаш часовой пояс: {location}'
        elif location and not code:
            text = f'Чтобы закончить регистрацию добавьте Ваш ' \
                   f'персональный код.\nВаш часовой пояс: {location}'
        elif not location and code:
            text = f'Чтобы закончить регистрацию добавьте Ваш ' \
                   f'часовой пояс.\nВаш код: {code}'
        else:
            text = 'Чтобы закончить регистрацию добавьте Ваш ' \
                   'персональный код и часовой пояс.'

        buttons = [
            [InlineKeyboardButton(text="Завершить регистрацию",
                                  callback_data=f'{END}')]
            if location and code else '',

            [InlineKeyboardButton(text='Добавить код' if not code else
             'Изменить код', callback_data=f'{CONF_CODE}'),

             InlineKeyboardButton(text='Добавить часовой пояс' if not location
             else 'Изменить часовой пояс', callback_data=f'{CONF_TZ}')],

            [InlineKeyboardButton(text='Назад', callback_data=f'{BACK}')]
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

        text = SUCCESSFUL_REG

        update.callback_query.answer()
        update.callback_query.delete_message()

        # TODO добавить кнопки для обычного общения с системой
        keyboard = ReplyKeyboardMarkup(
            [['/help', '/settings']], row_width=1, resize_keyboard=True)

        context.bot.send_message(
            update.effective_chat.id, text=text, reply_markup=keyboard)
        return END

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
                CallbackQueryHandler(self.back_to_reg, pattern=f'^{BACK}$'),
                CommandHandler('stop', StartDialog.stop_nested, run_async=False)
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
            [InlineKeyboardButton(text='Назад', callback_data=f'{BACK}')]
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

        if msg[0] not in ('+', '-') or not msg[1:].isdigit():
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


class CC1RegistrationDialog(ConversationHandler):
    def __init__(self):
        e_points = [CallbackQueryHandler(self.start,
                                         pattern=f'^{SIGN_UP_AS_CC1}$')]
        st = {
            CC1_REGISTRATION_ACTION: [

            ],
        }
        fallbacks = [
            CommandHandler('stop', StartDialog.stop),
            CallbackQueryHandler(PatientRegistrationDialog.back_to_start,
                                 pattern=f'^{END}$')
        ]
        super().__init__(entry_points=e_points, states=st, fallbacks=fallbacks)

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
