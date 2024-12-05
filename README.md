# TGBOT
> [!NOTE]  
> Данный репозиторий - **некоммерческая** сборка а всего лишь моя производственная практика.
>
> Всем добра и позитива

<h3>Привязка к яндекс диску</h1>
Для получения API Яндекса необходимо зайти на сайт документации - https://yandex.ru/dev/disk/doc/ru/concepts/quickstart#quickstart__oauth

Пройти по заголовку - Авторизация приложения с помощью OAuth-токена
![{2251128F-CD76-440D-9D91-8E02B9E1D71C}](https://github.com/user-attachments/assets/2afbeb0c-3672-4425-9333-e61adc718b54)


В случае успеха вы получите API ключ в виде такой странницы 
![{7F1D4A36-2B75-4CF3-8A42-98BB0B2CBD75}](https://github.com/user-attachments/assets/d99bb2c5-b75d-4d8c-82f9-8a29ea2b25e9)


Перед этим не забываем на страннице https://oauth.yandex.ru/ создать проект и в нём добавить права на: yadisk:disk, cloud_api:disk.app_folder, cloud_api:disk.read, cloud_api:disk.write, cloud_api:disk.info.

<h3>Настройка хоста</h2>

С хостом всё проще, я взял хост Amvera - https://amvera.ru/
Он позволяет используя существующий репозиторий гитхаба на своей базе собрать ваш проект.
Используя команду - **`git remote add amvera https://git.amvera.ru/nickname/projectname`** 

Он начнёт сборку 
![{1D481AA8-906A-472C-8336-A84C8BF515DD}](https://github.com/user-attachments/assets/001ea85c-a68d-420a-b001-1c7aaf9b261a)

Перед этим необходимо авторизироваться и создать файл .yml

Так как в моём коде добавлена настройка DEBUG, в логах сервера я могу видеть любые действия в боте, и в случае каких либо ошибок, их можно будет отследить.

![{FDA0677D-8649-4745-89D9-CF34C45974DD}](https://github.com/user-attachments/assets/4594c054-6dc2-4ecc-b588-98cd22a85c91)


Так же при обновлении проекта, необходимо просто написать в терминал команду **`git push amvera master`**
После чего хост начнёт сборку последней версии вашего кода

> [!CAUTION]
> 
> Я не утверждаю, что моя сборка безупречна, это лишь мой первый крупный проект.
>
> 