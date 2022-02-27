import datetime as dt

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, error
from telegram.ext import (CallbackContext, CallbackQueryHandler,
                          CommandHandler, Filters, MessageHandler)

from modules.dialogs_shortcuts.notification_shortcuts import *
from modules.dialogs_shortcuts.start_shortcuts import START_OVER
from modules.timer import deleting_pre_start_msg_task, remove_job_if_exists
from tools.decorators import registered_patient


class Notification:
    @staticmethod
    def is_msg_updated(user):
        return user.active_dialog_msg and \
               user.msg_to_del != user.active_dialog_msg

    @staticmethod
    def start(update: Update, context: CallbackContext, **kwargs):
        user = context.user_data['user']
        text, keyboard = kwargs['text'], kwargs['keyboard']

        if not context.user_data.get(START_OVER):
            try:
                update.callback_query.answer()
                msg = update.callback_query.edit_message_text(
                    text=text, reply_markup=keyboard)
            except error.TelegramError:
                context.user_data[START_OVER] = False
                return END
        else:
            context.user_data[START_OVER] = False
            # Если сообщения отличаются
            # (т.е. сообщение обновилось, то завершаем диалог)
            if Notification.is_msg_updated(user):
                user.active_dialog_msg = None
                return END

            # Удаляем pre-start сообщение перед началом диалога
            if not user.active_dialog_msg:
                context.bot.delete_message(user.chat_id,
                                           user.msg_to_del.message_id)
            try:
                # Отправляем новое сообщение
                msg = context.bot.send_message(
                    user.chat_id, text=text, reply_markup=keyboard)
            except error.Unauthorized:
                return END

        user.msg_to_del = user.active_dialog_msg = msg


class PillTakingDialog(ConversationHandler):
    def __init__(self):
        super().__init__(
            name=self.__class__.__name__,
            conversation_timeout=dt.timedelta(hours=1, minutes=30),
            entry_points=[CallbackQueryHandler(self.start,
                                               pattern=f'^{PILL_TAKING}$')],
            states={
                PILL_TAKING_ACTION: [
                    CallbackQueryHandler(self.confirm,
                                         pattern=f'^{CONFIRM_PILL_TAKING}$'),
                    CallbackQueryHandler(self.reason,
                                         pattern=f'^{CANT_PILL_TAKING}$'),
                    CallbackQueryHandler(self.end, pattern='END_PILL_TAKING')
                ],
                TYPING: [
                    MessageHandler(Filters.text & ~Filters.command,
                                   self.save_reason)
                ]
            },
            fallbacks=[CommandHandler('stop', self.stop),
                       CallbackQueryHandler(self.start,
                                            pattern=f'^{PILL_TAKING}$')]
        )

    @staticmethod
    def pre_start(context: CallbackContext, data, text=None, buttons=None):
        # Получаем пользователя из задачи
        user = data['user']

        text = 'Доброе утро! Примите, пожалуйста, лекарство!\n' \
               'Нажмите "Добавить ответ", чтобы мы могли зафиксировать ваши '\
               'действия.' if not text else text

        buttons = [[InlineKeyboardButton(
            text='Добавить ответ', callback_data=f'{PILL_TAKING}')]] \
            if not buttons else buttons

        keyboard = InlineKeyboardMarkup(buttons)

        try:
            msg = context.bot.send_message(user.chat_id, text=text,
                                           reply_markup=keyboard)
            user.msg_to_del = msg
        except error.Unauthorized:
            pass
        # Таск на "само-удаление" сообщения
        remove_job_if_exists(f'{user.chat_id}-pre_start_msg', context)
        context.job_queue.run_once(
            callback=deleting_pre_start_msg_task,
            when=dt.timedelta(hours=1, minutes=30),
            context={'user': user},
            name=f'{user.chat_id}-pre_start_msg'
        )

    @staticmethod
    @registered_patient
    def start(update: Update, context: CallbackContext):
        response = context.user_data['user'].pill_response

        if not response:
            text = 'Доброе утро! Примите, пожалуйста, лекарство!\n\n' \
                   'Если вы приняли лекарство, нажмите "Я принял лекарство".'\
                   '\n\nЕсли у Вас нет возможности принять лекарство, ' \
                   'нажмите "Я не могу принять" и опишите свою причину.'
        else:
            text = f'Нажмите "Подтвердить", чтобы сохранить ваш ответ.\n' \
                   f'При необходимости Вы можете изменить ваш ответ.' \
                   f'\n\nВаш ответ: {response}'

        buttons = [
            [InlineKeyboardButton(text='Подтвердить',
                                  callback_data='END_PILL_TAKING')]
            if response else '',
            [InlineKeyboardButton(text='Я принял лекарство',
                                  callback_data=f'{CONFIRM_PILL_TAKING}')]
            if not response or 'Я принял' not in response else '',
            [InlineKeyboardButton(text='Я не могу принять',
                                  callback_data=f'{CANT_PILL_TAKING}')]
            if not response or 'Я не могу' not in response else '',
        ]
        keyboard = InlineKeyboardMarkup(buttons)
        Notification.start(update, context, text=text, keyboard=keyboard)
        return PILL_TAKING_ACTION

    @staticmethod
    def confirm(update: Update, context: CallbackContext):
        """Подтверждение принятия лекарства"""
        context.user_data['user'].pill_response = 'Я принял лекарство.'
        return PillTakingDialog.start(update, context)

    @staticmethod
    def reason(update: Update, context: CallbackContext):
        """Запрашивает у пользователя причину"""
        text = 'Опишите вашу причину'
        if not context.user_data.get(START_OVER):
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text)
        else:
            try:
                update.effective_chat.send_message(text=text)
            except error.Unauthorized:
                return END
            finally:
                context.user_data[START_OVER] = False
        return TYPING

    @staticmethod
    def save_reason(update: Update, context: CallbackContext):
        """Сохранение пользовательского ответа"""
        resp = update.message.text

        context.user_data[START_OVER] = True
        if len(resp) <= 100:
            context.user_data['user'].pill_response = \
                f'Я не могу принять лекарство. Причина: {update.message.text}'
            return PillTakingDialog.start(update, context)
        text = 'Ваш ответ слишком длинный.' \
               '\nВозможное количество символов: 100'
        try:
            update.message.reply_text(text=text)
        except error.Unauthorized:
            return END
        return PillTakingDialog.reason(update, context)

    @staticmethod
    def end(update: Update, context: CallbackContext):
        """Завершение первого утреннего диалога"""
        text = 'Мы сохранили Ваш ответ. Спасибо!'

        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text)

        # Переключаем индекс диалога у пользователя из задачи.
        user = context.user_data['user']
        user.next_curr_state_index()

        # Запускаем второй диалог
        DataCollectionDialog.pre_start(context, data={'user': user})

        return END

    @staticmethod
    def stop(update: Update, context: CallbackContext):
        user = context.user_data['user']
        # Если сообщение еще не обновилось
        if not Notification.is_msg_updated(user):
            # Если пользователь ввел команду /stop, диалог останавливается.
            context.bot.delete_message(update.effective_chat.id,
                                       user.msg_to_del.message_id)
            PillTakingDialog.pre_start(context, data={'user': user})
        return END


class DataCollectionDialog(ConversationHandler):
    def __init__(self):
        super().__init__(
            name=self.__class__.__name__,
            conversation_timeout=dt.timedelta(hours=1, minutes=30),
            entry_points=[CallbackQueryHandler(self.start,
                                               pattern=f'^{DATA_COLLECT}$')],
            states={
                DATA_COLLECT_ACTION: [
                    CallbackQueryHandler(self.input_req,
                                         pattern=f'^SYS$|^DIAS$|^HEART$'),
                    CallbackQueryHandler(self.end, pattern=f'END_DATA_COLLECT')
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
        """Предстартовое сообщение с кнопкой для запуска диалога"""
        state_name = data['user'].state()[0]
        text = 'Добрый вечер! ' if not state_name == 'MOR' else 'Доброе утро! '

        text += 'Сообщите, пожалуйста, ' \
                'ваше артериальное давление!\n' \
                'Нажмите "Добавить ответ", чтобы мы могли зафиксировать ' \
                'ваши действия.'

        buttons = [[InlineKeyboardButton(text='Добавить ответ',
                                         callback_data=f'{DATA_COLLECT}')]]
        PillTakingDialog.pre_start(context, data, text=text, buttons=buttons)

    @staticmethod
    @registered_patient
    def start(update: Update, context: CallbackContext):
        # Получаем пользователя из задачи
        user = context.user_data['user']

        # Получаем ответ пользователя из контекста
        response = context.user_data['user'].data_response

        state_name = user.state()[0]
        text = 'Добрый вечер!' if not state_name == 'MOR' else 'Доброе утро!'

        if not all(response.values()):
            text += ' Сообщите, пожалуйста, ваше артериальное давление!\n' \
                    'Введите значения систолического давления (САД), ' \
                    'диастолического АД (ДАД) и ЧСС\n'
        else:
            text = f'Нажмите "Подтвердить", чтобы сохранить ваш ответ.\n' \
                   f'При необходимости вы можете изменить ваш ответ.\n'

        sys, dias, heart = response.values()
        if any(response.values()):
            text += f'\nВаши данные:'
            text += ('\nСАД: ' + str(sys)) if sys else ''
            text += ('\nДАД: ' + str(dias)) if dias else ''
            text += ('\nЧСС: ' + str(heart)) if heart else ''

        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(text='Подтвердить',
                                      callback_data=f'END_DATA_COLLECT')]
                if all(response.values()) else '',
                [InlineKeyboardButton(text='Ввести САД'
                 if not sys else 'Изменить САД', callback_data=f'SYS'),
                 InlineKeyboardButton(text='Ввести ДАД'
                 if not dias else 'Изменить ДАД', callback_data=f'DIAS'),
                 InlineKeyboardButton(text='Ввести ЧСС'
                 if not heart else 'Изменить ЧСС', callback_data=f'HEART')],
            ]
        )
        Notification.start(update, context, text=text, keyboard=keyboard)
        return DATA_COLLECT_ACTION

    @staticmethod
    def input_req(update: Update, context: CallbackContext):
        """Запрос у пользователя ввода данных"""
        val = update.callback_query.data \
            if update.callback_query else context.user_data['val']
        context.user_data['val'] = val

        if val == 'SYS':
            text = 'Введите значение систолического давления (САД)'
        elif val == 'DIAS':
            text = 'Введите значение диастолического АД (ДАД)'
        else:
            text = 'Введите значение частоты сердечных сокращений (ЧСС)'
        if not context.user_data.get(START_OVER):
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text)
        else:
            try:
                update.effective_chat.send_message(text=text)
            except error.Unauthorized:
                return END
        context.user_data[START_OVER] = False
        return TYPING

    @staticmethod
    def save_input(update: Update, context: CallbackContext):
        """Сохранение пользовательских данных"""
        inp = update.message.text
        if inp.isdigit():
            context.user_data['user'].data_response[
                context.user_data['val'].lower()] = inp

            context.user_data[START_OVER] = True
            return DataCollectionDialog.start(update, context)
        text = 'Данные были введены в неправильном формате.\nПопробуйте снова.'
        update.message.reply_text(text=text)
        context.user_data[START_OVER] = True
        return DataCollectionDialog.input_req(update, context)

    @staticmethod
    def end(update: Update, context: CallbackContext):
        # Получаем пользователя из контекста
        user = context.user_data['user']

        # Сохраняем данные в бд
        user.save_patient_record()

        # Очищаем ответы для новых записей
        user.clear_responses()

        text = 'Мы сохранили Ваш ответ. Спасибо!'

        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text)

        # Удаляем повторяющийся таск
        remove_job_if_exists(f'{user.chat_id}-rep_task', context)

        # Удаляем таск удаления pre-start сообщения
        remove_job_if_exists(f'{user.chat_id}-pre_start_msg', context)
        return END

    @staticmethod
    def stop(update: Update, context: CallbackContext):
        user = context.user_data['user']
        # Если сообщение еще не обновилось
        if not Notification.is_msg_updated(user):
            context.bot.delete_message(update.effective_chat.id,
                                       user.msg_to_del.message_id)

            DataCollectionDialog.pre_start(context, data={'user': user})
        return END
