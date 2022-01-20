from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    CallbackContext, ConversationHandler, CommandHandler, MessageHandler,
    Filters, CallbackQueryHandler,
)

from modules.prepared_answers import START_MSG
from tools.decorators import not_registered_users

(
    # State definitions for top level conversation
    START_SELECTORS,
    SIGN_UP_AS_PATIENT,
    SIGN_UP_AS_CC1,

    # State definitions for second level conversation (PATIENT)
    PATIENT_REGISTRATION_ACTION,
    CC1_REGISTRATION_ACTION,
    ADDING_CODE,
    EDITING_CODE,
    ADDING_LOCATION,
    EDITING_LOCATION,

    # State definitions for second level conversation (CC1)
    # ADDING_PERSONAL_CODE
    # ...
    START_OVER,
    LOCATION_OVER,
    REGISTRATION_OVER,

    TYPING_CODE,
    END_REGISTRATION,
    STOPPING,

) = map(chr, range(15))
# Different states
RETURN = 'RETURN'
# Shortcut for ConversationHandler.END
END = ConversationHandler.END


class StartDialog(ConversationHandler):
    def __init__(self):
        e_points = [CommandHandler('start', self.start)]
        st = {
            START_SELECTORS: [PatientRegistrationDialog(),
                              CC1RegistrationDialog()],
        }
        fallbacks = [CommandHandler('stop', self.stop)]
        super().__init__(entry_points=e_points, states=st, fallbacks=fallbacks)

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


class PatientRegistrationDialog(ConversationHandler):
    def __init__(self):
        from modules.location import FindLocationDialog, ChangeLocationDialog
        e_points = [CallbackQueryHandler(self.patient_registration,
                                         pattern=f'^{SIGN_UP_AS_PATIENT}$')]
        st = {
            PATIENT_REGISTRATION_ACTION: [
                CallbackQueryHandler(
                    self.add_code, pattern=f'^{ADDING_CODE}$|^{EDITING_CODE}$'),
                FindLocationDialog(),
                ChangeLocationDialog(),
                CallbackQueryHandler(self.end_reg,
                                     pattern=f'^{END_REGISTRATION}$')
            ],
            TYPING_CODE: [
                MessageHandler(Filters.text & ~Filters.command, self.save_code)
            ]
        }
        fallbacks = [
            CommandHandler('stop', StartDialog.stop),
            CallbackQueryHandler(self.return_to_start, pattern=f'^{RETURN}$')
        ]
        super().__init__(entry_points=e_points, states=st, fallbacks=fallbacks)

    # @not_registered_users

    @staticmethod
    def patient_registration(update: Update, context: CallbackContext):
        if not context.user_data.get(REGISTRATION_OVER):
            context.user_data['get_address'] = False
            context.user_data['get_code'] = False

        buttons = [
            [InlineKeyboardButton(text="Завершить регистрацию",
                                  callback_data=f'{END_REGISTRATION}')]
            if context.user_data['get_address'] and
               context.user_data['get_code'] else '',
            [InlineKeyboardButton(text='Добавить код',
                                  callback_data=f'{ADDING_CODE}') if
             not context.user_data['get_code'] else
             InlineKeyboardButton(text='Изменить код',
                                  callback_data=f'{EDITING_CODE}'),

             InlineKeyboardButton(text='Добавить местоположение',
                                  callback_data=f'{ADDING_LOCATION}') if
             not context.user_data['get_address'] else
             InlineKeyboardButton(text='Изменить местоположение',
                                  callback_data=f'{EDITING_LOCATION}')],
            [InlineKeyboardButton(text='Назад',
                                  callback_data=f'{RETURN}')]
        ]
        keyboard = InlineKeyboardMarkup(buttons)
        if context.user_data['get_address'] and context.user_data['get_code']:
            location = context.user_data.get('location')
            text = f'Нажмите "Завершить регистрацию", ' \
                   f'чтобы завершить регистрацию.\n' \
                   f'Ваш код: {context.user_data["get_code"]}\n' \
                   f'Ваше местоположение: ' \
                   f'{location if location else "Нет адреса"} ' \
                   f'- ({context.user_data["longitude"]}, ' \
                   f'{context.user_data["latitude"]})'
        elif context.user_data['get_address'] and \
                not context.user_data['get_code']:
            location = context.user_data.get('location')
            text = f'Чтобы закончить регистрацию добавьте Ваш ' \
                   f'персональный код.\nВаше местоположение: ' \
                   f'{location if location else "Нет адреса"} ' \
                   f'- ({context.user_data["longitude"]}, ' \
                   f'{context.user_data["latitude"]})'
        elif not context.user_data['get_address'] \
                and context.user_data['get_code']:
            text = f'Чтобы закончить регистрацию добавьте Вашe ' \
                   f'местоположение.\nВаш код: {context.user_data["get_code"]}'
        else:
            text = 'Чтобы закончить регистрацию добавьте Ваш ' \
                   'персональный код и местоположение.'

        if not context.user_data.get(REGISTRATION_OVER):
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text,
                                                    reply_markup=keyboard)
        else:
            update.message.reply_text(text=text, reply_markup=keyboard)

        context.user_data[REGISTRATION_OVER] = False
        return PATIENT_REGISTRATION_ACTION

    @staticmethod
    def add_code(update: Update, context: CallbackContext):
        update.callback_query.answer()

        text = 'Введите Ваш персональный код'
        update.callback_query.edit_message_text(text=text)
        return TYPING_CODE

    @staticmethod
    def save_code(update: Update, context: CallbackContext):
        context.user_data['get_code'] = update.message.text
        context.user_data[REGISTRATION_OVER] = True
        return PatientRegistrationDialog.patient_registration(update, context)

    @staticmethod
    def end_reg(update: Update, context: CallbackContext):
        context.user_data['is_registered'] = True
        update.callback_query.answer()

        text = 'Вы успешно вошли в аккаунт!'
        update.callback_query.delete_message()

        # TODO добавить кнопки для обычного общения с системой
        keyboard = ReplyKeyboardMarkup(
            [['/help', '/settings']],
            row_width=1, resize_keyboard=True)

        context.bot.send_message(
            update.effective_chat.id, text=text, reply_markup=keyboard)
        return END

    @staticmethod
    def return_to_start(update: Update, context: CallbackContext):
        context.user_data[START_OVER] = True
        StartDialog.start(update, context)
        return END


class CC1RegistrationDialog(ConversationHandler):
    def __init__(self):
        e_points = [CallbackQueryHandler(self.cc1_registration,
                                         pattern=f'^{SIGN_UP_AS_CC1}$')]
        st = {
            CC1_REGISTRATION_ACTION: [

            ],
        }
        fallbacks = [
            CommandHandler('stop', StartDialog.stop),
            CallbackQueryHandler(PatientRegistrationDialog.return_to_start,
                                 pattern=f'^{RETURN}$')
        ]
        super().__init__(entry_points=e_points, states=st, fallbacks=fallbacks)

    @staticmethod
    def cc1_registration(update: Update, context: CallbackContext):
        return CC1_REGISTRATION_ACTION
