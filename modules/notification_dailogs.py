from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CallbackQueryHandler, \
    CallbackContext, CommandHandler, MessageHandler, Filters

from modules.timer import remove_job_if_exists

from modules.dialogs_shortcuts.notification_shortcuts import *


class PillTakingDialog(ConversationHandler):
    def __init__(self):
        super().__init__(
            name=self.__class__.__name__,
            entry_points=[CallbackQueryHandler(self.start,
                                               pattern=f'^{PILL_TAKING}$')],
            states={
                PILL_TAKING_ACTION: [
                    CallbackQueryHandler(self.confirm,
                                         pattern=f'^{CONFIRM_PILL_TAKING}$'),
                    CallbackQueryHandler(self.reason,
                                         pattern=f'^{CANT_PILL_TAKING}$'),
                    CallbackQueryHandler(self.end, pattern=f'^{END}$')
                ],
                TYPING: [
                    MessageHandler(Filters.text & ~Filters.command,
                                   self.save_reason)
                ]
            },
            fallbacks=[CommandHandler('stop', self.stop),
                       CallbackQueryHandler(self.stop,
                                            pattern=f'^{PILL_TAKING}$')
                       ]
        )

    @staticmethod
    def pre_start(context: CallbackContext, data, text=None, buttons=None):
        text = 'Доброе утро! Примите, пожалуйста, лекарство!\n' \
               'Нажмите "Добавить ответ", чтобы мы могли зафиксировать ваши ' \
               'действия.' if not text else text

        buttons = [[InlineKeyboardButton(
            text="Добавить ответ", callback_data=f'{PILL_TAKING}')]] \
            if not buttons else buttons

        keyboard = InlineKeyboardMarkup(buttons)

        msg = context.bot.send_message(data['user'].chat_id,
                                       text=text,
                                       reply_markup=keyboard)
        if context.job:
            context.job.context['user'].msg = msg
        elif context.user_data:
            context.user_data['user'].msg = msg

    @staticmethod
    def start(update: Update, context: CallbackContext):
        response = context.user_data.get('pill_response')

        if not response:
            text = 'Доброе утро! Примите, пожалуйста, лекарство!\n\n' \
                   'Если вы приняли лекарство, нажмите "Я принял лекарство".' \
                   '\n\nЕсли у Вас нет возможности принять лекарство, нажмите ' \
                   '"Я не могу принять" и опишите свою причину.'
        else:
            text = f'Нажмите "Подтвердить", чтобы сохранить ваш ответ.\n' \
                   f'При необходимости Вы можете изменить ваш ответ.' \
                   f'\n\nВаш ответ: {response}'

        buttons = [
            [InlineKeyboardButton(text='Подтвердить', callback_data=f'{END}')]
            if response else '',
            [InlineKeyboardButton(text='Я принял лекарство',
                                  callback_data=f'{CONFIRM_PILL_TAKING}')]
            if not response or 'Я принял' not in response else '',
            [InlineKeyboardButton(text='Я не могу принять',
                                  callback_data=f'{CANT_PILL_TAKING}')]
            if not response or 'Я не могу' not in response else '',
        ]
        keyboard = InlineKeyboardMarkup(buttons)
        if not context.user_data.get(PILL_TAKING_OVER):
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text,
                                                    reply_markup=keyboard)
        else:
            msg = update.message.reply_text(text=text, reply_markup=keyboard)
            context.user_data['user'].msg = msg

        context.user_data[PILL_TAKING_OVER] = False

        return PILL_TAKING_ACTION

    @staticmethod
    def confirm(update: Update, context: CallbackContext):
        context.user_data['pill_response'] = 'Я принял лекарство.'
        return PillTakingDialog.start(update, context)

    @staticmethod
    def reason(update: Update, context: CallbackContext):
        text = "Опишите вашу причину"
        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text)
        return TYPING

    @staticmethod
    def save_reason(update: Update, context: CallbackContext):
        context.user_data['pill_response'] = f'Я не могу принять лекарство. ' \
                                             f'Причина: {update.message.text}'
        context.user_data[PILL_TAKING_OVER] = True
        return PillTakingDialog.start(update, context)

    @staticmethod
    def end(update: Update, context: CallbackContext):
        print(context.user_data['pill_response'])
        # TODO запрос в бд для сохранения данных
        text = "Мы сохранили Ваш ответ. Спасибо!"

        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text)

        context.user_data['user'].next_curr_state_index()

        DataCollectionDialog.pre_start(
            context, data={'user': context.user_data['user']})

        return END

    @staticmethod
    def stop(update: Update, context: CallbackContext):
        if update.callback_query.data == f'{PILL_TAKING}':
            return PillTakingDialog.start(update, context)

        context.bot.delete_message(update.effective_chat.id,
                                   context.user_data['user'].msg.message_id)
        PillTakingDialog.pre_start(
            context, data={'user': context.user_data['user']})
        return END


class DataCollectionDialog(ConversationHandler):
    def __init__(self):
        super().__init__(
            name=self.__class__.__name__,
            entry_points=[CallbackQueryHandler(self.start,
                                               pattern=f'^{DATA_COLLECT}$')],
            states={
                DATA_COLLECT_ACTION: [
                    CallbackQueryHandler(self.input_req,
                                         pattern=f'^SYS$|^DIAS$|^HEART$'),
                    CallbackQueryHandler(self.end, pattern=f'^{END}$')
                ],
                TYPING: [
                    MessageHandler(Filters.text & ~Filters.command,
                                   self.save_input)
                ]
            },
            fallbacks=[CommandHandler('stop', self.stop),
                       CallbackQueryHandler(self.start,
                                            pattern=f'^{DATA_COLLECT}$')]
        )

    @staticmethod
    def pre_start(context: CallbackContext, data):
        state_name = data['user'].state()[0]
        text = 'Добрый вечер! ' if not state_name == 'MOR' else 'Доброе утро! '

        text += 'Сообщите, пожалуйста, ' \
                'ваше артериальное давление!\n' \
                'Нажмите "Добавить ответ", чтобы мы могли зафиксировать ' \
                'ваши действия.'

        buttons = [[InlineKeyboardButton(text="Добавить ответ",
                                         callback_data=f'{DATA_COLLECT}')]]
        PillTakingDialog.pre_start(context, data, text=text, buttons=buttons)

    @staticmethod
    def start(update: Update, context: CallbackContext):
        response = context.user_data.get('data_response')
        if not response:
            response = context.user_data['data_response'] = \
                {'sys': None, 'dias': None, 'heart': None}

        state_name = context.user_data['user'].state()[0]
        text = 'Добрый вечер! ' if not state_name == 'MOR' else 'Доброе утро! '

        if not all(response.values()):
            text += 'Сообщите, пожалуйста, ' \
                    'ваше артериальное давление!\n' \
                    'Введите значения систолического давления (САД), ' \
                    'диастолического АД (ДАД) и ЧСС\n'
        else:
            text = f'Нажмите "Подтвердить", чтобы сохранить ваш ответ.\n' \
                   f'При необходимости вы можете изменить ваш ответ.' \
                   f'\n\nВаши данные:'

        sys = response.get('sys')
        dias = response.get('dias')
        heart = response.get('heart')

        data_text = '\nВаши данные:'
        data_text += f'\nСАД: {sys}' if sys else ''
        data_text += f'\nДАД: {dias}' if dias else ''
        data_text += f'\nЧСС: {heart}' if heart else ''

        if data_text != '\nВаши данные:':
            text += data_text

        buttons = [
            [InlineKeyboardButton(text='Подтвердить', callback_data=f'{END}')]
            if all(response.values()) else '',
            [InlineKeyboardButton(text='Ввести САД'
             if not sys else 'Изменить САД', callback_data=f'SYS'),
             InlineKeyboardButton(text='Ввести ДАД'
             if not dias else 'Изменить ДАД', callback_data=f'DIAS'),
             InlineKeyboardButton(text='Ввести ЧСС'
             if not heart else 'Изменить ЧСС', callback_data=f'HEART')],
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        if not context.user_data.get(DATA_COLLECT_OVER):
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text,
                                                    reply_markup=keyboard)
        else:
            msg = update.message.reply_text(text=text, reply_markup=keyboard)
            context.user_data['user'].msg = msg

        context.user_data[DATA_COLLECT_OVER] = False

        return DATA_COLLECT_ACTION

    @staticmethod
    def input_req(update: Update, context: CallbackContext):
        val = update.callback_query.data
        context.user_data['val'] = val

        if val == 'SYS':
            text = 'Введите значение систолического давления (САД)'
        elif val == 'DIAS':
            text = 'Введите значение диастолического АД (ДАД)'
        else:
            text = 'Введите значение частоты сердечных сокращений (ЧСС)'

        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text)
        return TYPING

    @staticmethod
    def save_input(update: Update, context: CallbackContext):
        context.user_data['data_response'][
            context.user_data['val'].lower()] = update.message.text

        context.user_data[DATA_COLLECT_OVER] = True
        return DataCollectionDialog.start(update, context)

    @staticmethod
    def end(update: Update, context: CallbackContext):
        print(context.user_data['data_response'])
        # TODO запрос в бд для сохранения данных
        text = "Мы сохранили Ваш ответ. Спасибо!"

        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text)
        remove_job_if_exists(context.user_data['user'].rep_task_name, context)
        return END

    @staticmethod
    def stop(update: Update, context: CallbackContext):
        if update.callback_query.data == f'{DATA_COLLECT}':
            return DataCollectionDialog.start(update, context)
        context.bot.delete_message(update.effective_chat.id,
                                   context.user_data['user'].msg.message_id)
        DataCollectionDialog.pre_start(
            context, data={'user': context.user_data['user']})
        return END
