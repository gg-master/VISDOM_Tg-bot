import logging
from os import remove

from telegram import ReplyKeyboardMarkup, Update, error
from telegram.ext import (CallbackContext, CallbackQueryHandler,
                          CommandHandler, ConversationHandler, Filters,
                          MessageHandler)

from db_api import (change_patients_membership, get_patient_by_user_code,
                    make_file_by_patient_user_code, make_file_patients,
                    make_patient_list, patient_exists_by_user_code)
from modules.dialogs_shortcuts.start_shortcuts import (END, EXCLUDE_PATIENT,
                                                       SEND_USER_DATA_PAT)
from modules.users_list import users_list
from tools.decorators import registered_doctors


class RegionJon():
    pass