import logging

from telegram import Update
from telegram.ext import CallbackContext

from db_api import (get_accept_times_by_patient_id, get_all_patients,
                    get_all_doctors, get_all_regions, get_all_uni,
                    get_patient_by_chat_id)
from modules.users_classes import DoctorUser, RegionUser, UniUser
from modules.users_list import users_list


class Restore:
    def __init__(self, dispatcher):
        self.context = CallbackContext(dispatcher)

        # Восстановление всех пациентов, которые зарегистрированны и участвуют
        self.restore_all_patients()
        # Восстановление врачей
        self.restore_all_doctors()
        # Восстановление регионов
        self.restore_all_regions()
        # Восстановление университета
        self.restore_all_uni()

    def restore_all_patients(self):
        for patient in filter(lambda x: x.member, get_all_patients()):
            accept_times = get_accept_times_by_patient_id(patient.id)
            self.restore_patient(self.context, patient, accept_times)

    @staticmethod
    def restore_patient(context, patient, accept_times):
        from modules.users_classes import PatientUser

        p = PatientUser(patient.chat_id)
        p.restore(
            code=patient.user_code,
            tz_str=patient.time_zone,
            times={'MOR': accept_times[0].time, 'EVE': accept_times[1].time},
            accept_times={'MOR': accept_times[0].id, 'EVE': accept_times[1].id}
        )
        # Проверяем пациента на время последней записи
        p.check_user_records(context)

        # Восстановление обычных Daily тасков
        p.recreate_notification(context)
        # Восстановление цикличных тасков. Если для них соответствует время
        p.restore_repeating_task(context)

        logging.info(f'--- PATIENT {p.chat_id} RESTORED ---')

    @staticmethod
    def restore_patient_by_chat_id(update: Update, context: CallbackContext):
        patient = get_patient_by_chat_id(update.effective_chat.id)
        accept_times = get_accept_times_by_patient_id(patient.id)
        Restore.restore_patient(context, patient, accept_times)

        context.user_data['user'] = users_list[update.effective_user.id]

    @staticmethod
    def restore_all_doctors():
        for doctor in get_all_doctors():
            DoctorUser(doctor.chat_id).restore(doctor.doctor_code)
            logging.info(f'--- DOCTOR {doctor.chat_id} RESTORED ---')

    @staticmethod
    def restore_all_regions():
        for region in get_all_regions():
            RegionUser(region.chat_id).restore(region.region_code)
            logging.info(f'--- REGION {region.chat_id} RESTORED ---')

    @staticmethod
    def restore_all_uni():
        for uni in get_all_uni():
            UniUser(uni.chat_id).restore()
            logging.info(f'--- UNI {uni.chat_id} RESTORED ---')
