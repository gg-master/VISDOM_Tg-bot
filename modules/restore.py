import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, error
from telegram.ext import CallbackContext

from db_api import (get_accept_times_by_patient_id, get_all_patients,
                    get_all_doctors, get_all_regions, get_all_uni)
from modules.users_classes import DoctorUser, RegionUser, UniUser
from modules.users_list import users_list
from modules.timer import remove_job_if_exists
from tools.decorators import not_registered_users, unavailable_for_user


class Restore:
    def __init__(self, dispatcher):
        self.context = CallbackContext(dispatcher)

        # Восстановление всех пациентов, которые зарегистрированны и участвуют
        self.restore_all_patients()
        # Восстановление врачей
        self.restore_all_doctors(self.context)
        # Восстановление регионов
        self.restore_all_regions(self.context)
        # Восстановление университета
        self.restore_all_uni(self.context)

    def restore_all_patients(self):
        for patient in filter(lambda x: x.member, get_all_patients()):
            accept_times = get_accept_times_by_patient_id(patient.id)
            self.restore_patient(patient, accept_times)

    def restore_patient(self, patient, accept_times):
        from modules.users_classes import PatientUser

        p = PatientUser(patient.chat_id)
        p.restore(
            code=patient.user_code,
            tz_str=patient.time_zone,
            times={'MOR': accept_times[0].time, 'EVE': accept_times[1].time},
            accept_times={'MOR': accept_times[0].id, 'EVE': accept_times[1].id}
        )
        # Проверяем пациента на время последней записи
        p.check_user_records(self.context)

        # Если удалось отправить сообщение пациенту
        if Restore.restore_patient_msg(self.context, chat_id=patient.chat_id):
            # Восстановление обычных Daily тасков
            p.recreate_notification(self.context)

            # Восстановление цикличных тасков. Если для них соответствует время
            p.restore_repeating_task(self.context)

        logging.info(f'SENT PATIENT RESTORE_MSG: {p.chat_id}')

    @staticmethod
    def restore_all_doctors(context):
        for doctor in get_all_doctors():
            user = DoctorUser(doctor.chat_id)
            user.restore(doctor.doctor_code)

            Restore.restore_doctor_msg(context, chat_id=user.chat_id)

    @staticmethod
    def restore_all_regions(context):
        for region in get_all_regions():
            user = RegionUser(region.chat_id)
            user.restore(region.region_code)

            Restore.restore_region_msg(context, chat_id=user.chat_id)

    @staticmethod
    def restore_all_uni(context):
        for uni in get_all_uni():
            user = UniUser(uni.chat_id)
            user.restore()

            Restore.restore_uni_msg(context, chat_id=user.chat_id)

    @staticmethod
    def restore_patient_msg(context, **kwargs):
        text = 'Уважаемый пользователь, чат-бот был перезапущен.\n' \
               'Приносим свои извенения за доставленные неудобства.\n' \
               'Уведомления были востановлены.\n' \
               'Чтобы получить доступ к основным функциям нажмите ' \
               '"Восстановить доступ"'
        buttons = [[InlineKeyboardButton(text='Восстановить доступ',
                                         callback_data=f'RESTORE_PATIENT')]]
        kb = InlineKeyboardMarkup(buttons)
        try:
            context.bot.send_message(kwargs['chat_id'], text=text,
                                     reply_markup=kb)
            return True
        except (error.Unauthorized, error.BadRequest):
            for task in (f'{kwargs["chat_id"]}-MOR',
                         f'{kwargs["chat_id"]}-EVE',
                         f'{kwargs["chat_id"]}-rep_task'):
                remove_job_if_exists(task, context)
            return False

    @staticmethod
    def restore_doctor_msg(context, **kwargs):
        text = 'Уважаемый пользователь, чат-бот был перезапущен.\n' \
               'Приносим свои извенения за доставленные неудобства.\n' \
               'Чтобы получить доступ к основным функциям нажмите ' \
               '"Восстановить доступ"'
        buttons = [
            [InlineKeyboardButton(text='Восстановить доступ',
                                  callback_data=f'RESTORE_DOCTOR')],
        ]
        keyboard = InlineKeyboardMarkup(buttons)
        try:
            context.bot.send_message(
                kwargs['chat_id'], text=text, reply_markup=keyboard)
        except error.Unauthorized:
            pass
        except Exception as e:
            logging.warning(f'CANT SEND RESTORE_MSG TO '
                            f'DOCTOR-{kwargs["chat_id"]}. '
                            f'CHAT NOT FOUND. \nMORE: {e}')

    @staticmethod
    def restore_region_msg(context, **kwargs):
        text = 'Уважаемый пользователь, чат-бот был перезапущен.\n' \
               'Приносим свои извенения за доставленные неудобства.\n' \
               'Чтобы получить доступ к основным функциям нажмите ' \
               '"Восстановить доступ"'
        buttons = [
            [InlineKeyboardButton(text='Восстановить доступ',
                                  callback_data=f'RESTORE_REGION')],
        ]
        keyboard = InlineKeyboardMarkup(buttons)
        try:
            context.bot.send_message(
                kwargs['chat_id'], text=text, reply_markup=keyboard)
        except error.Unauthorized:
            pass
        except Exception as e:
            logging.warning(f'CANT SEND RESTORE_MSG TO '
                            f'REGION-{kwargs["chat_id"]}. '
                            f'CHAT NOT FOUND. \nMORE: {e}')

    @staticmethod
    def restore_uni_msg(context, **kwargs):
        text = 'Уважаемый пользователь, чат-бот был перезапущен.\n' \
               'Приносим свои извенения за доставленные неудобства.\n' \
               'Чтобы получить доступ к основным функциям нажмите ' \
               '"Восстановить доступ"'
        buttons = [
            [InlineKeyboardButton(text='Восстановить доступ',
                                  callback_data=f'RESTORE_UNI')],
        ]
        keyboard = InlineKeyboardMarkup(buttons)
        try:
            context.bot.send_message(
                kwargs['chat_id'], text=text, reply_markup=keyboard)
        except error.Unauthorized:
            pass
        except Exception as e:
            logging.warning(f'CANT SEND RESTORE_MSG TO '
                            f'UNI-{kwargs["chat_id"]}. '
                            f'CHAT NOT FOUND. \nMORE: {e}')


@not_registered_users
def patient_restore_handler(update: Update, context: CallbackContext):
    from modules.start_dialogs import PatientRegistrationDialog

    # Устанавливаем в контекст ранее созданный объект пациента
    user = context.user_data['user'] = users_list[update.effective_chat.id]

    if not user or not user.member:
        unavailable_for_user(update)
        return

    logging.info(f'RESTORED PATIENT: {user.chat_id}')

    # Если уже пришло уведомление, то переотправляем его после восстановления
    if user.msg_to_del:
        # Получаем id сообщения иp пользователя
        try:
            context.bot.delete_message(user.chat_id,
                                       user.msg_to_del.message_id)
        except error.TelegramError:
            pass

    # Удаляем сообщени с кнопкой восстановления
    update.callback_query.delete_message()
    try:
        update.effective_chat.send_message(
            'Доступ восстановлен. Теперь Вы можете добавить ответ на '
            'уведомления, к которым не было доступа.')
        PatientRegistrationDialog.restore_main_msg(update, context)
        # print(context.job_queue.get_jobs_by_name(
        #     f'{context.user_data["user"].chat_id}-EVE')[0].next_t)
        # print(context.job_queue.get_jobs_by_name(
        #     f'{context.user_data["user"].chat_id}-rep_task')[0].next_t)
        # Если уже пришло уведомление, то переотправляем его
        if user.msg_to_del:
            try:
                context.bot.delete_message(user.chat_id,
                                           user.msg_to_del.message_id)
            except error.TelegramError:
                pass
            # Снова отображаем удаленное уведомление
            user.notification_states[user.state()[0]][
                user.state()[1]].pre_start(
                context, data={'user': user})
    except error.Unauthorized:
        pass


@not_registered_users
def doctor_restore_handler(update: Update, context: CallbackContext):
    from modules.patronage_dialogs import DoctorJob

    doc = context.user_data['user'] = users_list[update.effective_chat.id]
    if not doc:
        return
    logging.info(f'RESTORED DOCTOR: {doc.chat_id}')
    try:
        update.callback_query.delete_message()
        update.effective_chat.send_message('Доступ восстановлен.')
        DoctorJob.default_job(update, context)
    except error.Unauthorized:
        pass
    except Exception as e:
        logging.warning(f"CANT SEND RESTORE_MSG TO DOCTOR. CHAT NOT FOUND."
                        f"\nMORE: {e}")


@not_registered_users
def region_restore_handler(update: Update, context: CallbackContext):
    from modules.patronage_dialogs import RegionJob

    reg = context.user_data['user'] = users_list[update.effective_chat.id]

    if not reg:
        return

    logging.info(f'RESTORED REGION: {reg.chat_id}')
    try:
        update.callback_query.delete_message()
        update.effective_chat.send_message('Доступ восстановлен.')
        RegionJob.default_job(update, context)
    except error.Unauthorized:
        pass
    except Exception as e:
        logging.warning(f"CANT SEND RESTORE_MSG TO REGION. CHAT NOT FOUND."
                        f"\nMORE: {e}")


@not_registered_users
def uni_restore_handler(update: Update, context: CallbackContext):
    from modules.patronage_dialogs import UniJob

    uni = context.user_data['user'] = users_list[update.effective_chat.id]

    if not uni:
        return

    logging.info(f'RESTORED UNI: {uni.chat_id}')
    try:
        update.callback_query.delete_message()
        update.effective_chat.send_message('Доступ восстановлен.')
        UniJob.default_job(update, context)
    except error.Unauthorized:
        pass
    except Exception as e:
        logging.warning(f"CANT SEND RESTORE_MSG TO UNI. CHAT NOT FOUND."
                        f"\nMORE: {e}")
