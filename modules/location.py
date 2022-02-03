import requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, \
    ReplyKeyboardRemove
from telegram.ext import CallbackContext, ConversationHandler, \
    CommandHandler, MessageHandler, Filters, CallbackQueryHandler

from tools.prepared_answers import BAD_GEOCODER_RESP
from tools.tools import get_from_env
from modules.settings_dialogs import SETTINGS_ACTION
from modules.dialogs_shortcuts.start_shortcuts import (
    PATIENT_REGISTRATION_ACTION,
    CONF_TZ_OVER,
    CONF_LOCATION,
    REGISTRATION_OVER,
    LOCATION_OVER,
    STOPPING,
    END,
)


class Location:
    def __init__(self, tz=None, location: dict = None):
        self._time_zone = self.validate_tz(tz) if tz else tz
        self._location = location  # {'address': [lat, lon]}

    def time_zone(self):
        return self._time_zone

    @staticmethod
    def validate_tz(tz):
        if type(tz) is str and (tz[0] not in ('+', '-') or not tz[1:].isdigit()
                                or not (-10 <= int(tz[1:]) <= 10)):
            raise ValueError(f'Not correct tz: {tz}')
        return tz

    def location(self):
        return self._location

    def get_coords(self):
        if self._location:
            return list(self._location.values())[0]
        return None

    def __str__(self):
        if self._location and not self._time_zone:
            address = list(self._location.keys())[0]
            return f'{address} - ({self._location[address][0]}, ' \
                   f'{self._location[address][1]})'
        elif self._time_zone and not self._location:
            return f'{self._time_zone}'


class FindLocationDialog(ConversationHandler):
    def __init__(self, *args, **kwargs):
        from modules.start_dialogs import StartDialog
        super().__init__(
            name=self.__class__.__name__,
            entry_points=[CallbackQueryHandler(
                self.start, pattern=f'^{CONF_LOCATION}$')]
            if not kwargs else kwargs.get('e_points'),

            states={
                1: [MessageHandler(Filters.regex('^Найти адрес$'),
                                   self.input_address),
                    MessageHandler(Filters.location, self.location_response,
                                   run_async=False),
                    MessageHandler(Filters.regex('^Назад$'),
                                   self.back_to_prev_level)],
                2: [MessageHandler(Filters.text & ~Filters.command,
                                   self.find_response)],
                3: [MessageHandler(Filters.regex('^Да, верно$|^Нет, неверно$'),
                                   self.location_response, run_async=False)],
            },
            fallbacks=[CommandHandler('stop', StartDialog.stop_nested,
                                      run_async=False)],
            map_to_parent={
                PATIENT_REGISTRATION_ACTION: END,
                STOPPING: STOPPING,
            }
        )

    @staticmethod
    def start(update: Update, context: CallbackContext):

        kboard = ReplyKeyboardMarkup(
            [
                [KeyboardButton(text="Отправить геолокацию",
                                request_location=True)],
                # ['Найти адрес'],
                ['Назад']
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
        static_api_request = FindLocationDialog.find_location(update, context)

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
    def location_response(update: Update, context: CallbackContext, self=None):
        """
        Проверка результата поиска через апи.
        Сохранение позиции, полученной через геометку ТГ.
        """
        from modules.start_dialogs import PatientRegistrationDialog

        response = update.message.text
        location = update.message.location

        if response and 'Нет, неверно' in response:
            context.user_data[LOCATION_OVER] = True
            return FindLocationDialog.start(update, context)

        elif (response and 'Да, верно' in response) or location:
            # Returning to second level patient registration conv.
            context.user_data[REGISTRATION_OVER] = True

            if location:
                context.user_data['user'].location = Location(
                    location={'Нет адреса': [location.longitude,
                                             location.latitude]})
        if self:
            return self.start(update, context)
        return PatientRegistrationDialog.start(update, context)

    @staticmethod
    def back_to_prev_level(update: Update, context: CallbackContext):
        # Переход на предыдущий уровень в диалоге
        if not context.user_data['user'].registered():
            from modules.start_dialogs import ConfigureTZDialog
            context.user_data[CONF_TZ_OVER] = True
            ConfigureTZDialog.start(update, context)
        return END

    @staticmethod
    def find_location(update: Update, context: CallbackContext):
        """
        Поиск локации в яндексе
        :param update:
        :param context:
        :return: yandex static api request
        """

        # Получние ответа от геокодера о поиске адреса
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

        # На основе ответа геокодера получаем координаты объекта
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

        # Ищем объект на карте, чтобы определить что правильно нашли место
        static_api_request = \
            f"http://static-maps.yandex.ru/1.x/?ll={ll}" \
            f"&spn={spn}&l=map&" \
            f"pt={','.join([toponym_longitude, toponym_lattitude])},vkbkm"

        # Запоминаем положение
        context.user_data['user'].location = \
            Location(location={update.message.text: [toponym_longitude,
                                                     toponym_lattitude]})

        return static_api_request


class ChangeLocationDialog(FindLocationDialog):
    def __init__(self):
        super().__init__()
        self.map_to_parent.update({
            SETTINGS_ACTION: END
        })

    @staticmethod
    def location_response(update: Update, context: CallbackContext, *args):
        from modules.settings_dialogs import SettingsDialog
        return FindLocationDialog.location_response(
            update, context, SettingsDialog)
