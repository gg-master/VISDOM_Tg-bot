import requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CallbackContext, ConversationHandler, CommandHandler, \
    MessageHandler, Filters, CallbackQueryHandler

from modules.prepared_answers import BAD_GEOCODER_RESP
from tools.decorators import not_registered_users, registered_users
from tools.tools import get_from_env

from modules.start_dialogs import ADDING_LOCATION, EDITING_LOCATION, END, \
    PATIENT_REGISTRATION_ACTION, REGISTRATION_OVER


class Location:
    @staticmethod
    def find_location(update: Update, context: CallbackContext):
        # Поиск локации в яндексе. Перед добавлением
        context.user_data['location'] = update.message.text

        geocoder_uri = "http://geocode-maps.yandex.ru/1.x/"
        response = requests.get(geocoder_uri, params={
            "apikey": get_from_env('GEOCODER_T'),
            "format": "json",
            "geocode": update.message.text
        })
        if not response:
            update.message.reply_text(
                BAD_GEOCODER_RESP +
                f'Http статус: {response.status_code} ({response.reason})')
            return None

        json_response = response.json()

        if json_response['response']['GeoObjectCollection'][
            'metaDataProperty']['GeocoderResponseMetaData']['found'] == '0':
            update.message.reply_text('Объект не найден! Попробуйте снова.')
            return None

        toponym = json_response["response"]["GeoObjectCollection"][
            "featureMember"][0]["GeoObject"]
        toponym_coodrinates = toponym["Point"]["pos"]
        # Долгота и широта:
        toponym_longitude, toponym_lattitude = toponym_coodrinates.split(" ")
        delta = "0.3"
        ll = ",".join([toponym_longitude, toponym_lattitude])
        spn = ",".join([delta, delta])

        static_api_request = \
            f"http://static-maps.yandex.ru/1.x/?ll={ll}" \
            f"&spn={spn}&l=map&" \
            f"pt={','.join([toponym_longitude, toponym_lattitude])},vkbkm"

        context.user_data['longitude'] = toponym_longitude
        context.user_data['latitude'] = toponym_lattitude
        return static_api_request

    @staticmethod
    def location(update: Update, context: CallbackContext):
        message = update.message
        current_pos = (message.location.latitude, message.location.longitude)
        print(current_pos)


class FindLocationDialog(ConversationHandler, Location):
    def __init__(self, *args, **kwargs):
        # MessageHandler(Filters.regex("^Добавить местоположение$"),
        #                self.start_find
        e_points = [CallbackQueryHandler(self.start_find,
                                         pattern=f'^{ADDING_LOCATION}$')]
        super(FindLocationDialog, self).__init__(
            entry_points=e_points if not kwargs else kwargs.get('e_points'),

            states={
                1: [MessageHandler(Filters.text, self.input_address),
                    MessageHandler(Filters.location, self.location_response)],
                2: [MessageHandler(Filters.text, self.find_response)],
                3: [MessageHandler(
                    Filters.regex('^Да, верно$|^Нет, неверно$'),
                    self.location_response)],

            },
            fallbacks=[CommandHandler('stop', self.stop)],
            map_to_parent={
                END: PATIENT_REGISTRATION_ACTION
            },
        )

    # @not_registered_users
    def start_find(self, update: Update, context: CallbackContext):

        kboard = ReplyKeyboardMarkup(
            [
                [KeyboardButton(text="Отправить геолокацию",
                                request_location=True)],
                ['Найти адрес']
            ],
            row_width=1, resize_keyboard=True, one_time_keyboard=True)

        update.callback_query.answer()
        update.callback_query.delete_message()
        context.bot.send_message(
            update.effective_chat.id,
            text='Выберите способ добавления местоположения',
            reply_markup=kboard)
        return 1

    @staticmethod
    def input_address(update: Update, context: CallbackContext):
        context.bot.send_message(update.effective_chat.id,
                                 text='Введите Ваш адрес или '
                                      'ближайший населенный пункт.')
        return 2

    def find_response(self, update: Update, context: CallbackContext):
        static_api_request = self.find_location(update, context)

        if static_api_request is not None:
            keyboard = ReplyKeyboardMarkup(
                [
                    ['Да, верно'],
                    ['Нет, неверно']
                ],
                row_width=1, resize_keyboard=True, one_time_keyboard=True)
            context.bot.send_photo(
                update.message.chat_id,
                static_api_request,
                caption="Пожалуйста, убидетесь, что мы правильно "
                        "определили Ваше местоположение.",
                reply_markup=keyboard)
            return 3

        context.bot.send_message(update.effective_chat.id,
                                 text='У нас возникли трудности с поиском '
                                      'вашего адреса. Попробуйте снова')
        return self.END

    def location_response(self, update: Update, context: CallbackContext):
        from modules.start_dialogs import RegistrationDialog
        response = update.message.text
        location = update.message.location
        if response and 'Нет, неверно' in response:
            return self.start_find(update, context)
        elif (response and 'Да, верно' in response) or location:
            context.user_data['get_address'] = \
                context.user_data[REGISTRATION_OVER] = True
            if location:
                context.user_data['longitude'] = location.longitude
                context.user_data['latitude'] = location.latitude
            print(context.user_data['longitude'],
                  context.user_data['latitude'])
            RegistrationDialog.patient_registration(update, context)
        return END

    @staticmethod
    def stop(update: Update, context: CallbackContext):
        return END


class ChangeLocationDialog(FindLocationDialog):
    def __init__(self):
        super(ChangeLocationDialog, self).__init__(e_points=[
            CallbackQueryHandler(self.change_location,
                                 pattern=f'^{EDITING_LOCATION}$'),
            MessageHandler(Filters.regex("^Изменить местоположение$"),
                           self.change_location)
        ]
        )

    # @registered_users
    def change_location(self, update: Update, context: CallbackContext):
        context.user_data['location'] = None
        keyboard = ReplyKeyboardMarkup(
            [
                [KeyboardButton(text="Отправить геолокацию",
                                request_location=True)],
                ['Найти адрес']
            ],
            row_width=1, resize_keyboard=True, one_time_keyboard=True)

        context.bot.send_message(
            update.effective_chat.id,
            text='Выберите способ добавления местоположения',
            reply_markup=keyboard)
        return 1
