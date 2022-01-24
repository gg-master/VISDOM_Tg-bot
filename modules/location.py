import requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, \
    ReplyKeyboardRemove
from telegram.ext import CallbackContext, ConversationHandler, CommandHandler, \
    MessageHandler, Filters, CallbackQueryHandler

from modules.prepared_answers import BAD_GEOCODER_RESP
from tools.decorators import not_registered_users, registered_users
from tools.tools import get_from_env

from modules.start_dialogs import (
    CONF_LOCATION,
    CONF_TZ_OVER,
    LOCATION_OVER,
    END, STOPPING,
)


class Location:
    @staticmethod
    def find_location(update: Update, context: CallbackContext):
        # Поиск локации в яндексе.
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
            update.message.reply_text('Мы не смогли найти указанный адрес. '
                                      'Попробуйте снова.')
            return None

        toponym = json_response["response"]["GeoObjectCollection"][
            "featureMember"][0]["GeoObject"]
        toponym_coodrinates = toponym["Point"]["pos"]

        # Долгота и широта
        toponym_longitude, toponym_lattitude = toponym_coodrinates.split(" ")
        delta = "0.3"
        ll = ",".join([toponym_longitude, toponym_lattitude])
        spn = ",".join([delta, delta])

        static_api_request = \
            f"http://static-maps.yandex.ru/1.x/?ll={ll}" \
            f"&spn={spn}&l=map&" \
            f"pt={','.join([toponym_longitude, toponym_lattitude])},vkbkm"

        context.user_data['location'] = \
            {update.message.text: [toponym_longitude, toponym_lattitude]}
        return static_api_request


class FindLocationDialog(ConversationHandler, Location):
    def __init__(self, *args, **kwargs):
        e_points = [CallbackQueryHandler(self.start_find,
                                         pattern=f'^{CONF_LOCATION}$')]
        super(FindLocationDialog, self).__init__(
            entry_points=e_points if not kwargs else kwargs.get('e_points'),

            states={
                1: [MessageHandler(Filters.regex('^Найти адрес$'),
                                   self.input_address),
                    MessageHandler(Filters.location, self.location_response)],
                2: [MessageHandler(Filters.text & ~Filters.command,
                                   self.find_response)],
                3: [MessageHandler(Filters.regex('^Да, верно$|^Нет, неверно$'),
                                   self.location_response)],

            },
            fallbacks=[CommandHandler('stop', self.stop)],
            map_to_parent={
                STOPPING: STOPPING
            }
        )

    @staticmethod
    def start_find(update: Update, context: CallbackContext):
        context.user_data['location'] = None

        kboard = ReplyKeyboardMarkup(
            [
                [KeyboardButton(text="Отправить геолокацию",
                                request_location=True)],
                ['Найти адрес']
            ],
            row_width=1, resize_keyboard=True, one_time_keyboard=True)

        if not context.user_data.get(LOCATION_OVER):
            update.callback_query.answer()
            update.callback_query.delete_message()
        context.bot.send_message(
            update.effective_chat.id,
            text='Выберите способ добавления местоположения',
            reply_markup=kboard)
        context.user_data[LOCATION_OVER] = False
        return 1

    @staticmethod
    def input_address(update: Update, context: CallbackContext):
        context.bot.send_message(update.effective_chat.id,
                                 text='Введите Ваш адрес или '
                                      'ближайший населенный пункт.',
                                 reply_markup=ReplyKeyboardRemove())
        return 2

    @staticmethod
    def find_response(update: Update, context: CallbackContext):
        static_api_request = Location.find_location(update, context)

        if static_api_request is not None:
            keyboard = ReplyKeyboardMarkup(
                [['Да, верно'], ['Нет, неверно']],
                row_width=1, resize_keyboard=True, one_time_keyboard=True)
            context.bot.send_photo(
                update.message.chat_id,
                static_api_request,
                caption="Пожалуйста, убидетесь, что мы правильно "
                        "определили Ваше местоположение.",
                reply_markup=keyboard)
            return 3

        return FindLocationDialog.input_address(update, context)

    @staticmethod
    def location_response(update: Update, context: CallbackContext):
        from modules.start_dialogs import PatientRegistrationDialog
        response = update.message.text
        location = update.message.location

        if response and 'Нет, неверно' in response:
            context.user_data[LOCATION_OVER] = True
            return FindLocationDialog.start_find(update, context)

        elif (response and 'Да, верно' in response) or location:
            context.user_data[CONF_TZ_OVER] = True

            if location:
                context.user_data['location'] = {
                    'Нет адреса': [location.longitude, location.latitude]}

            PatientRegistrationDialog.patient_registration(update, context)
        return END

    @staticmethod
    def stop(update: Update, context: CallbackContext):
        from modules.start_dialogs import StartDialog
        StartDialog.stop(update, context)
        return STOPPING
