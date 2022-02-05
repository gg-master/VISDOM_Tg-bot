from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CallbackQueryHandler, \
    CallbackContext, CommandHandler, MessageHandler, Filters, \
    DispatcherHandlerStop

from modules.timer import remove_job_if_exists
from tools.decorators import registered_patient
from modules.dialogs_shortcuts.notification_shortcuts import *
from db_api import add_record


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
                    CallbackQueryHandler(self.end, pattern='END_PILL_TAKING')
                ],
                TYPING: [
                    MessageHandler(Filters.text & ~Filters.command,
                                   self.save_reason)
                ]
            },
            fallbacks=[CommandHandler('stop', self.stop),
                       CallbackQueryHandler(self.start,
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
        print(context.user_data)
        user = context.job.context['user'] if context.job \
            else context.user_data['user']
        user.msg_to_del = msg

    @staticmethod
    @registered_patient
    def start(update: Update, context: CallbackContext):
        user = context.user_data['user']
        response = user.pill_response

        if not response:
            text = 'Доброе утро! Примите, пожалуйста, лекарство!\n\n' \
                   'Если вы приняли лекарство, нажмите "Я принял лекарство".' \
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

        if not context.user_data.get(PILL_TAKING_OVER):
            update.callback_query.answer()
            msg = update.callback_query.edit_message_text(
                text=text, reply_markup=keyboard)
        else:
            # Если сообщения отличаются
            # (т.е. сообщение обновилось, то завершаем диалог)
            if user.is_msg_updated():
                user.active_dialog_msg = None
                return END

            # Удаляем pre-start сообщение перед началом диалога
            if not user.active_dialog_msg:
                context.bot.delete_message(user.chat_id,
                                           user.msg_to_del.message_id)

            # Отправляем новое сообщение
            msg = context.bot.send_message(
                user.chat_id, text=text, reply_markup=keyboard)

        user.msg_to_del = user.active_dialog_msg = msg

        context.user_data[PILL_TAKING_OVER] = False
        return PILL_TAKING_ACTION

    @staticmethod
    def confirm(update: Update, context: CallbackContext):
        """Подтверждение принятия лекарства"""
        context.user_data['user'].pill_response = 'Я принял лекарство.'
        return PillTakingDialog.start(update, context)

    @staticmethod
    def reason(update: Update, context: CallbackContext):
        """Запрашивает у пользователя причину"""
        text = "Опишите вашу причину"
        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text)
        return TYPING

    @staticmethod
    def save_reason(update: Update, context: CallbackContext):
        """Сохранение пользовательского ответа"""
        context.user_data['user'].pill_response = \
            f'Я не могу принять лекарство. Причина: {update.message.text}'
        context.user_data[PILL_TAKING_OVER] = True
        return PillTakingDialog.start(update, context)

    @staticmethod
    def end(update: Update, context: CallbackContext):
        """Завершение первого утреннего диалога"""
        text = "Мы сохранили Ваш ответ. Спасибо!"

        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text)

        # Переключаем индекс диалога у пользователя.
        context.user_data['user'].next_curr_state_index()

        # Запускаем второй диалог
        DataCollectionDialog.pre_start(
            context, data={'user': context.user_data['user']})

        return END

    @staticmethod
    def stop(update: Update, context: CallbackContext):
        user = context.user_data['user']
        # Если сообщение еще не обновилось
        if not user.is_msg_updated():
            # Если пользователь ввел команду /stop, диалог останавливается.
            context.bot.delete_message(update.effective_chat.id,
                                       user.msg_to_del.message_id)
            PillTakingDialog.pre_start(context, data={'user': user})
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

        buttons = [[InlineKeyboardButton(text="Добавить ответ",
                                         callback_data=f'{DATA_COLLECT}')]]
        PillTakingDialog.pre_start(context, data, text=text, buttons=buttons)

    @staticmethod
    @registered_patient
    def start(update: Update, context: CallbackContext):
        user = context.user_data['user']
        response = user.data_response

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
            text += f'\nВаши данные:' \
                    f'\n{("САД: " + str(sys)) if sys else ""}' \
                    f'\n{("ДАД: " + str(dias)) if dias else ""}' \
                    f'\n{("ЧСС: " + str(heart)) if heart else ""}'

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
        if not context.user_data.get(DATA_COLLECT_OVER):
            update.callback_query.answer()
            msg = update.callback_query.edit_message_text(
                text=text, reply_markup=keyboard)
        else:
            # Если сообщения отличаются
            # (т.е. сообщение обновилось, то завершаем диалог)
            if user.is_msg_updated():
                user.active_dialog_msg = None
                return END
            # Удаляем pre-start сообщение перед началом диалога
            if not user.active_dialog_msg:
                context.bot.delete_message(user.chat_id,
                                           user.msg_to_del.message_id)
            # Отправляем новое сообщение
            msg = context.bot.send_message(
                user.chat_id, text=text, reply_markup=keyboard)

        user.msg_to_del = user.active_dialog_msg = msg

        context.user_data[DATA_COLLECT_OVER] = False
        return DATA_COLLECT_ACTION

    @staticmethod
    def input_req(update: Update, context: CallbackContext):
        """Запрос у пользователя ввода данных"""
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
        """Сохранение пользовательских данных"""
        context.user_data['user'].data_response[
            context.user_data['val'].lower()] = update.message.text

        context.user_data[DATA_COLLECT_OVER] = True
        return DataCollectionDialog.start(update, context)

    @staticmethod
    def end(update: Update, context: CallbackContext):
        from modules.users_classes import PatientUser
        print(context.user_data['user'].data_response)
        user: PatientUser = context.user_data['user']

        # TODO запрос в бд для сохранения данных
        # add_record(
        #     time=user.times[user.state()[0]].time(),
        #     sys_press=user.data_response['sys'],
        #     dias_press=user.data_response['dias'],
        #     heart_rate=user.data_response['heart'],
        #     time_zone=user.tz.zone,
        #     accept_time_id=user.accept_times[user.state()[0]]
        # )
        user.clear_responses()

        text = "Мы сохранили Ваш ответ. Спасибо!"

        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text)

        remove_job_if_exists(context.user_data['user'].rep_task_name, context)
        context.user_data['user'].msg_to_del = None
        return END

    @staticmethod
    def stop(update: Update, context: CallbackContext):
        user = context.user_data['user']
        # Если сообщение еще не обновилось
        if not user.is_msg_updated():
            context.bot.delete_message(update.effective_chat.id,
                                       user.msg_to_del.message_id)

            DataCollectionDialog.pre_start(
                context, data={'user': context.user_data['user']})
        return END
