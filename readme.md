[comment]: <> (После получения Токена от BotFather Вы должны запустить tools/tools.py c параметром "-T TOKEN&#40;Ваш токен&#41;".)

[comment]: <> (После Вы должны создать .env файл в корне проекта и вставить туда полученный TOKEN.)

[comment]: <> (Выглядеть .env файл должен так:<br>)

[comment]: <> (`TOKEN = 'YOURTOKEN from tools/tools.py'`)


Перед запоковыванием проекта в контейнер нужно изменить ссылки на базу данных и токен бота.
Заходим в файл .env и меняем TOKEN на токен бота в телеграме, DB_ADDRESS на адресс базы данных,
PATRONAGE_TOKEN на токен патронажа(любое значение, которое придется ввести патронажу для аутентификации).\
Все данные в этом файле записываются в кодировке base64.
В файле alembic.ini значение параметра sqlalchemy.url устанавливаем как адресс базы данных (без кодировки).