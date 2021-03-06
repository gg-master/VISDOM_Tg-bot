import datetime as dt
import logging
import re
from threading import Thread
from typing import Dict, Tuple

import pytz
from telegram import Update, error
from telegram.ext import CallbackContext

from data import db_session
from db_api import (add_patient, add_doctor, add_record, change_accept_time,
                    change_patients_time_zone,
                    get_last_record_by_accept_time, get_patient_by_chat_id,
                    get_all_records_by_accept_time,
                    get_doctor_by_code,
                    get_region_by_code, get_all_patients_by_user_code,
                    add_region, get_all_doctors_by_user_code, add_university)
from modules.location import Location
from modules.notification_dailogs import DataCollectionDialog, PillTakingDialog
from modules.users_list import users_list
from modules.timer import (create_daily_notification, remove_job_if_exists,
                           restore_repeating_task)
from tools.exceptions import DoctorNotFound, UserExists, RegionNotFound
from tools.tools import convert_tz

db_session.global_init()
db_sess = db_session.create_session()

# Форматы паттернов
# Паттерн региона
region_code = r'\d{2,3}'

# Паттерн врача
doctor_name = r'[a-zA-Zа-яА-ЯёЁ]{3}'
doctor_num = r'\d?'
doctor_code = f'{doctor_name}{doctor_num}'

# Паттерн пациента
pat_name = r'[a-zA-Zа-яА-ЯёЁ]{3}'
pat_num = r'\d{,10}'
pat_code = f'{pat_name}{pat_num}'


class BasicUser:
    USER_EXCLUDED = 0
    USER_IS_PATIENT = 1
    USER_IS_DOCTOR = 2
    USER_IS_REGION = 3
    USER_IS_UNI = 4
    USER_IS_NOT_REGISTERED = -1

    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.code = ''
        self.is_registered = False

    def registered(self) -> bool:
        return self.is_registered

    def register(self, *args) -> None:
        self.is_registered = True

    def check_user_reg(self) -> int:
        """Определение к кому принадлежит пользователь"""
        # Ищем в бд
        patient = get_patient_by_chat_id(self.chat_id)
        if patient:
            # Если пациент не участвует в исследовании
            if not patient.member:
                return self.USER_EXCLUDED
            return self.USER_IS_PATIENT
        # Пользователь не зарегистрирован
        return self.USER_IS_NOT_REGISTERED


class PatientTimes:
    # Границы времени уведомлений
    time_limiters = {
        'MOR': [dt.datetime(1212, 12, 12, 6, 00, 0),
                dt.datetime(1212, 12, 12, 12, 00, 0)],
        'EVE': [dt.datetime(1212, 12, 12, 17, 00, 0),
                dt.datetime(1212, 12, 12, 21, 00, 0)]
    }
    # Значения времени по умолчанию
    default_times = {
        'MOR': dt.datetime(1212, 12, 12, 8, 00, 0),
        'EVE': dt.datetime(1212, 12, 12, 20, 00, 0)
    }

    def __init__(self, times=None):
        if times:
            self.times = {k: self.default_times[k].replace(
                hour=times[k].hour, minute=times[k].minute) for k in
                times.keys()}
            self.orig_t = self.times.copy()
        else:
            self.times = self.default_times.copy()
            self.orig_t = None

    def s_times(self):
        return dict(map(lambda x: (x, self.times[x].strftime("%H:%M")),
                        self.times.keys()))

    def add_minutes(self, time, minutes) -> bool:
        # Добавление минут
        delta = dt.timedelta(minutes=int(minutes))
        self.times[time] += delta

        # Ограничение времени
        if not (self.default_times[time].replace(
                hour=self.default_times[time].hour - 1) <= self.times[time] <=
                self.default_times[time].replace(
                    hour=self.default_times[time].hour + 1)):
            self.times[time] -= delta
            return False
        return True

    def drop_times(self):
        """Сброс времени уведомлений до дефолтных"""
        if self.times == self.default_times:
            return False
        self.times = self.default_times.copy()
        return True

    def items(self):
        return self.times.items()

    def cancel_updating(self):
        """Возвращает время к изначальным значениям"""
        self.times = self.orig_t.copy()

    def save_updating(self) -> bool:
        """Сохраняем новое время уведомлений"""
        if self.times != self.orig_t:
            self.orig_t = self.times.copy()
            return True
        return False

    def is_updating(self) -> bool:
        return self.times != self.orig_t

    def __getitem__(self, item) -> dt.datetime:
        return self.times[item]


class PatientLocation:
    def __init__(self, tz=None):
        self.tz = tz
        self.location = self.orig_loc = Location(tz=-int(re.search(
            pattern=r'[+-]?\d+', string=self.tz.zone).group(0))
            if tz else None) if tz else None

    def cancel_updating(self) -> None:
        """Возвращает местоположение в оригинальное"""
        self.location = self.orig_loc

    def save_updating(self) -> bool:
        """Сохранение нового местоположения"""
        if self.location != self.orig_loc:
            self.tz = pytz.timezone(convert_tz(self.location.get_coords(),
                                               self.location.time_zone()))
            self.orig_loc = self.location = Location(tz=-int(re.search(
                pattern=r'[+-]?\d+', string=self.tz.zone).group(0)))
            return True
        return False

    def is_updating(self) -> bool:
        """Возвращает результат сравнения местоположений"""
        return self.location != self.orig_loc


class PatientUser(BasicUser):
    # Последовательность сообщений в уведомлении
    notification_states = {
        'MOR': [PillTakingDialog, DataCollectionDialog],
        'EVE': [DataCollectionDialog]
    }
    # Паттыерн для вроверки формата кода
    code_pat = f'^{region_code}{doctor_code}{pat_code}$'
    # Паттерн для отделения цифр у пользователя из кода (при наличии)
    univ_code_pat = f'^{region_code}({doctor_code}{pat_name}){pat_num}$'
    # Паттерн для получения только цифр пользователя из кода
    usr_code_num_pat = f'^{region_code}{doctor_code}{pat_name}({pat_num})$'

    # Паттерны для получения каждой из частей кода (региона, врача, пациента)
    user_pat = f'^{region_code}{doctor_code}({pat_code})$'
    doctor_pat = f'^{region_code}({doctor_code}){pat_code}$'
    region_pat = f'^({region_code}){doctor_code}{pat_code}$'

    def __init__(self, chat_id: int):
        super().__init__(chat_id)
        self.member = True

        self.accept_times = self.doctor_id = None

        self.p_loc = PatientLocation()
        self.times = PatientTimes()

        # Сообщения, которые отправляются пользователю при получении
        # уведомлений. Сохраняем их для функции удаления старых сообщений
        # при обновлении уведомления.
        self.msg_to_del = self.active_dialog_msg = None

        self.alarmed = {'MOR': False, 'EVE': False}

        # Текущее состояние диалога
        self.curr_state = []  # [name, index]

        # Ответы от пользователя на уведомления
        self.pill_response = None
        self.data_response = {'sys': None, 'dias': None, 'heart': None}

    def set_code(self, code):
        """Проверка пользовательского кода на соответствие формату при вводе"""

        # Код не подходит по патерну, то вызываем ошибку
        if not re.match(self.code_pat, code):
            raise ValueError()
        self.code = code

    def validate_code(self):
        """Проверка пользовательского кода перед регистрацией"""

        # Разделяем введенный код на части
        r_code = re.findall(self.region_pat, self.code)[0].rjust(3, '0')
        d_code = re.findall(self.doctor_pat, self.code)[0]
        u_code = re.findall(self.user_pat, self.code)[0]

        # Получаем код пациента без цифр в конце
        univ_code = r_code + re.findall(self.univ_code_pat, self.code)[0]

        # Получаем всех пациентов, у которых одинаково ФИО
        patients = get_all_patients_by_user_code(univ_code)

        if patients and any(map(lambda x: x.user_code == r_code + d_code +
                                u_code, patients)):
            # Добавляем цифры к коду, если совпали
            advise_code = univ_code + str(int('0' + re.findall(
                self.usr_code_num_pat, patients[-1].user_code)[0]) + 1)
            raise UserExists(
                f'Ваш код совпал с кем-то. Измените Ваш код.\n'
                f'Рекомендуем использовать код: {advise_code}',
                advise_code
            )
        if not get_region_by_code(r_code):
            raise RegionNotFound('Ваш регион не найден. Проверьте Ваш код.')

        doc = get_doctor_by_code(r_code + d_code)
        if not doc:
            raise DoctorNotFound(f'Ваш доктор не найден. Проверьте Ваш код.')

        self.doctor_id = doc.id
        self.code = r_code + d_code + u_code

    def change_membership(self, context: CallbackContext):
        """Для исключения пациента из исследования"""
        self.member = False

        for task in (f'{self.chat_id}-MOR', f'{self.chat_id}-EVE',
                     f'{self.chat_id}-rep_task'):
            remove_job_if_exists(task, context)

    def create_notification(self, context: CallbackContext, **kwargs):
        """Создание уведомлений при регистрации или
        после изменения времени в настройках"""
        for name, notification_time in list(self.times.items())[:]:
            time = self.p_loc.tz.localize(notification_time)

            now = dt.datetime.now(tz=self.p_loc.tz)
            next_r_time = None

            # Зарегистрирован ли пациент впервые
            if self.check_last_record_by_name(name)[0] or \
                    (name == 'MOR' and (
                    kwargs.get('register') or (
                    not get_all_records_by_accept_time(
                        self.accept_times['EVE']) and
                    not get_all_records_by_accept_time(
                        self.accept_times['MOR'])))) or \
                    context.job_queue.get_jobs_by_name(
                        f'{self.chat_id}-rep_task'):
                # Утреннее уведомление переносим на день вперед
                next_r_time = now.replace(
                    hour=time.hour, minute=time.minute, second=0,
                    microsecond=0) + dt.timedelta(days=1)

            create_daily_notification(
                context=context,
                time=time,
                next_run_time=next_r_time,
                name=name,
                user=self,
                task_data={
                    'interval': dt.timedelta(hours=1) if name == 'MOR'
                    else dt.timedelta(minutes=30),
                    'last': self.p_loc.tz.localize(
                        self.times.time_limiters[name][1]).astimezone(
                        pytz.utc).time()},
            )

    def recreate_notification(self, context: CallbackContext, **kwargs):
        """Восстановление ежедневных тасков"""
        self.create_notification(context, **kwargs)

    def restore_repeating_task(self, context: CallbackContext, **kwargs):
        """Восстановление повторяющихся тасков"""
        restore_repeating_task(self, context, **kwargs)

    def _thr_restore_notifications(self, context, **kwargs):
        self.recreate_notification(context, register=kwargs['register'])
        self.restore_repeating_task(context, register=kwargs['register'])
        # print(context.job_queue.get_jobs_by_name(
        #     f'{context.user_data["user"].chat_id}-MOR')[0].next_t)
        # print(context.job_queue.get_jobs_by_name(
        #     f'{context.user_data["user"].chat_id}-EVE')[0].next_t)
        # job1 = context.job_queue.get_jobs_by_name(
        #     f'{context.user_data["user"].chat_id}-rep_task')
        # if job1:
        #     print(job1[0].next_t)

    def state(self):
        """Возвращает имя временного таймера и состояние
        (т.е. в каком диалоге находится пользователь)"""
        return self.curr_state

    def set_curr_state(self, name: str):
        """Устанавливает новое состояние"""
        self.curr_state = [name, 0]

    def _set_curr_state_by_time(self):
        # Устанавливаем состояние диалога исходя из текущего времени
        if self.p_loc.tz.localize(self.times['MOR']).time() < \
                dt.datetime.now(tz=self.p_loc.tz).time() < \
                self.p_loc.tz.localize(self.times['EVE']).time():
            self.set_curr_state('MOR')
        else:
            self.set_curr_state('EVE')

    def next_curr_state_index(self):
        """Переключает индекс текущего состояния"""
        self.curr_state[1] = min(1, self.curr_state[1] + 1)

    def clear_responses(self):
        self.pill_response = None
        self.data_response = {'sys': None, 'dias': None, 'heart': None}

    def cancel_updating(self):
        """Возвращение значений времени и ЧП к начальным значениям"""
        self.times.cancel_updating()
        self.p_loc.cancel_updating()

    def save_updating(self, context: CallbackContext, check_user=True):
        """Сохранение изменение настроект ЧП и времени уведомлений"""
        # Проверка существует ли пользователь в бд
        if check_user and (not get_patient_by_chat_id(self.chat_id)
                           or not self.accept_times):
            raise ValueError()
        if self.times.is_updating() or self.p_loc.is_updating():
            ch_tz = self.p_loc.save_updating()
            ch_times = self.times.save_updating()

            self._set_curr_state_by_time()

            if check_user:
                Thread(target=self._threading_save_sett,
                       args=(ch_times, ch_tz)).start()

            # Восстанавливливаем уведомления
            Thread(target=self._thr_restore_notifications, args=(context,),
                   kwargs={'register': not check_user}).start()

            # Проверка ответов пользователя. Т.с. защита от махинаций
            self.check_user_records(context)

    def _threading_save_sett(self, ch_times, ch_tz):
        """Сохранение новых настроек в бд"""
        if ch_times:
            change_accept_time(self.accept_times['MOR'],
                               self.times['MOR'].time())
            change_accept_time(self.accept_times['EVE'],
                               self.times['EVE'].time())
        if ch_tz:
            change_patients_time_zone(self.chat_id, self.p_loc.tz.zone)

    def restore(self, code: str, times: Dict[str, dt.time], tz_str: str,
                accept_times):
        """Восстановление пользователя после перезапуска бота"""
        super().register()
        users_list[self.chat_id] = self

        self.code = code

        self.p_loc = PatientLocation(tz=pytz.timezone(tz_str))
        self.times = PatientTimes(times)

        self.accept_times = accept_times

        self._set_curr_state_by_time()

    def enable_user(self, context: CallbackContext):
        """Восстановление пользователя, после разблокировки им бота"""
        Thread(target=self._threading_enable, args=(context,)).start()

    def _threading_enable(self, context: CallbackContext):
        """Восстанавливаем пользователя, если он отключал бота"""
        if not context.job_queue.get_jobs_by_name(f'{self.chat_id}-MOR'):
            self.recreate_notification(context)
        if not context.job_queue.get_jobs_by_name(f'{self.chat_id}-rep_task'):
            if self.state() and get_all_records_by_accept_time(
                    self.accept_times[self.state()[0]]):
                self.restore_repeating_task(context)

    def register(self, update: Update, context: CallbackContext):
        """Регистрация пациента"""
        super().register()
        logging.info(f'REGISTER NEW USER: '
                     f'{update.effective_user.id} - {self.code}')
        Thread(target=self._threading_reg, args=(update, context)).start()

    def _threading_reg(self, update: Update, context: CallbackContext):
        # Добавляем пациента в список пациентов
        users_list[self.chat_id] = self

        self.p_loc.save_updating()

        # Добавляем пациента в бд
        self.accept_times = add_patient(
            time_morn=self.times['MOR'].time(),
            time_even=self.times['EVE'].time(),
            name=update.effective_user.full_name,
            user_code=self.code,
            time_zone=self.p_loc.tz.zone,
            chat_id=self.chat_id,
            doctor_id=self.doctor_id
        )
        self.save_updating(context, check_user=False)

    def save_patient_record(self):
        """Сохранение результатов ответа на уведомления"""
        self.alarmed[self.state()[0]] = False
        Thread(target=self._threading_save_record).start()

    def _threading_save_record(self):
        add_record(
            time_zone=self.p_loc.tz.zone,
            time=self.times[self.state()[0]].time(),
            response_time=dt.datetime.now(self.p_loc.tz),
            accept_time_id=self.accept_times[self.state()[0]],
            sys_press=self.data_response['sys'],
            dias_press=self.data_response['dias'],
            heart_rate=self.data_response['heart'],
            comment=self.pill_response[self.pill_response.find(':') + 2:]
            if self.pill_response and ':' in self.pill_response
            else self.pill_response
        )

    def check_user_records(self, context: CallbackContext):
        # Если аларм у пользователя уже сработал, то заново не активируем
        if any(self.alarmed.values()) or not self.accept_times:
            return None
        Thread(target=self._thread_check_user_records, args=(context,)).start()

    def _thread_check_user_records(self, context: CallbackContext):
        mor_record = self.check_last_record_by_name('MOR')
        eve_record = self.check_last_record_by_name('EVE')

        # Если есть какие-либо записи и время ответа >= 25 часов
        if (not mor_record[0] and mor_record[1] >= 25) or \
                (not eve_record[0] and eve_record[1] >= 25):
            self.alarmed['MOR' if mor_record[1] >= 25 else "EVE"] = True

            # Количество дней без ответа от пациента
            days = int(mor_record[1] / 24) if self.alarmed['MOR'] \
                else int(eve_record[1] / 24)

            # Получаем ФИО врача и номер региона, чтобы взять врача из бд
            doc = re.findall(self.doctor_pat, self.code)[0]
            region = re.findall(self.region_pat, self.code)[0]

            # Ежедневное уведомление для доктора
            DoctorUser.send_alarm(
                context=context,
                user=self,
                doctor_code=region + doc,
                days=days
            )

            # Еженедельное уведомление для региона
            if not days % 7:
                RegionUser.send_alarm(
                    context=context,
                    user=self,
                    region_code=region,
                    days=days
                )

    def check_last_record_by_name(self, name) -> Tuple[bool, int]:
        """
        Получение из бд времени последнего ответа по названию типа уведомления
        :param name:
        :return: True if all right and last record time less than 24 hour
        :return: False if last record time more then 24 hour
        """
        recs = get_last_record_by_accept_time(self.accept_times[name])
        hours = 24
        if recs:
            rec_t: dt.datetime = recs[-1].response_time.astimezone(
                self.p_loc.tz)
            now = dt.datetime.now(tz=self.p_loc.tz)
            hours = abs(now - rec_t).total_seconds() // 3600
            return now.date() == rec_t.date(), hours
        return False, hours


class DoctorUser(BasicUser):
    # Паттыерн для вроверки формата кода
    code_pat = f'^{region_code}{doctor_code}$'
    # Паттерн для отделения цифр у врача из кода (при наличии)
    univ_code_pat = f'^{region_code}({doctor_name}){doctor_num}$'
    # Паттерн для получения только цифр врача из кода
    doc_code_num_pat = f'^{region_code}{doctor_name}({doctor_num})$'

    # Паттерны для получения каждой из частей кода (региона, врача)
    doctor_pat = f'^{region_code}({doctor_code})$'
    region_pat = f'^({region_code}){doctor_code}$'

    def __init__(self, chat_id):
        super().__init__(chat_id)
        self.region_id = None

    def set_code(self, code):
        # Код не подходит по патерну, то вызываем ошибку
        if not re.match(self.code_pat, code):
            raise ValueError('Код введен в неправильном формате.')
        self.code = code

    def validate_code(self):
        # Код региона
        r_code = re.findall(self.region_pat, self.code)[0].rjust(3, '0')
        d_code = re.findall(self.doctor_pat, self.code)[0]

        # Получаем код врача без цифр в конце
        univ_code = r_code + re.findall(self.univ_code_pat, self.code)[0]
        # Получаем всех врачей, у которых одинаково ФИО
        doctors = get_all_doctors_by_user_code(univ_code)

        if doctors and any(map(lambda x: x.doctor_code == r_code + d_code,
                               doctors)):
            # Добавляем цифры к коду, если совпали
            advise_code = univ_code + str(int('0' + re.findall(
               self.doc_code_num_pat, doctors[-1].doctor_code)[0]) + 1)
            raise UserExists(
                f'Ваш код совпал с кем-то. Измените Ваш код.\n'
                f'Рекомендуем использовать код: {advise_code}',
                advise_code
            )
        region = get_region_by_code(r_code)
        if not region:
            raise RegionNotFound('Ваш регион не найден. Проверьте Ваш код.')

        self.region_id = region.id
        self.code = r_code + d_code

    def register(self, update: Update, context: CallbackContext):
        super().register()
        logging.info(f'REGISTER NEW DOCTOR: {update.effective_user.id}')
        Thread(target=self._threading_reg).start()

    def restore(self, code):
        super().register()
        users_list[self.chat_id] = self
        self.code = code

    def _threading_reg(self):
        users_list[self.chat_id] = self

        add_doctor(
            chat_id=self.chat_id,
            doctor_code=self.code,
            region_id=self.region_id
        )

    @staticmethod
    def send_alarm(context, **kwargs):
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        user = kwargs['user']
        doctor = get_doctor_by_code(kwargs['doctor_code'])
        if doctor:
            text = f'❗️ Внимание ❗️\n' \
                   f'В течении суток пациент {user.code} не принял ' \
                   f'лекарство/не отправил данные давления и ЧСС.\n' \
                   f'Дней без ответа: {kwargs["days"]}'

            kb = InlineKeyboardMarkup(
                [[InlineKeyboardButton(
                    'Получить данные о пациенте',
                    callback_data=f'A_PATIENT_DATA&{user.code}')]],
                one_time_keyboard=True)
            try:
                context.bot.send_message(doctor.chat_id, text,
                                         reply_markup=kb)
            except error.Unauthorized:
                pass
            except Exception as e:
                logging.warning(f'CANT SEND ALARM TO '
                                f'DOCTOR-{kwargs["doctor_code"]}. '
                                f'CHAT NOT FOUND. \nMORE: {e}')


class RegionUser(BasicUser):
    # Паттыерн для вроверки формата кода
    code_pat = f'^{region_code}$'

    def set_code(self, code):
        # Код не подходит по патерну, то вызываем ошибку
        if not re.match(self.code_pat, code):
            raise ValueError('Код введен в неправильном формате.')
        self.code = code

    def validate_code(self):
        # Проверяем, имеется ли регион уже в БД
        self.code = self.code.rjust(3, '0')
        regions = get_region_by_code(self.code)

        if regions:
            raise UserExists(f'Ваш код совпал с кем-то. Измените Ваш код.')

    def register(self, update: Update, context: CallbackContext):
        super().register()
        logging.info(f'REGISTER NEW REGION: {update.effective_user.id}')
        Thread(target=self._threading_reg).start()

    def restore(self, code):
        super().register()
        users_list[self.chat_id] = self
        self.code = code

    def _threading_reg(self):
        users_list[self.chat_id] = self

        add_region(chat_id=self.chat_id, region_code=self.code)

    @classmethod
    def send_alarm(cls, context, **kwargs):
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        user = kwargs['user']
        region = get_region_by_code(kwargs['region_code'])
        if region:
            text = f'❗️ Внимание ❗️\n' \
                   f'В течении суток пациент {user.code} не принял ' \
                   f'лекарство/не отправил данные давления и ЧСС.\n' \
                   f'Дней без ответа: {kwargs["days"]}'

            kb = InlineKeyboardMarkup(
                [[InlineKeyboardButton(
                    'Получить данные о пациенте',
                    callback_data=f'A_PATIENT_DATA&{user.code}')]],
                one_time_keyboard=True)
            try:
                context.bot.send_message(region.chat_id, text,
                                         reply_markup=kb)
            except error.Unauthorized:
                pass
            except Exception as e:
                logging.warning(f'CANT SEND ALARM TO '
                                f'REGION-{kwargs["region_code"]}. '
                                f'CHAT NOT FOUND. \nMORE: {e}')


class UniUser(BasicUser):
    def register(self, update: Update, context: CallbackContext):
        super().register()
        logging.info(f'REGISTER NEW UNI: {update.effective_user.id}')
        Thread(target=self._threading_reg).start()

    def restore(self):
        super().register()
        users_list[self.chat_id] = self

    def _threading_reg(self):
        users_list[self.chat_id] = self

        add_university(
            chat_id=self.chat_id,
        )
