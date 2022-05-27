from telegram.ext import CallbackContext

from modules.users_classes import PatientUser
from modules.users_list import users_list


def clear_all_notification(context: CallbackContext):
    for user in users_list.values():
        try:
            if type(user) is PatientUser and user.msg_to_del:
                context.bot.delete_message(user.chat_id,
                                           user.msg_to_del.message_id)
        except Exception as e:
            print(e)
    print('ALL MSG-NOTIFICATION DELETED')
