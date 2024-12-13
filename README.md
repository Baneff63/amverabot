# [![Typing SVG](https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=900&size=22&pause=1000&width=435&lines=%D0%A2%D0%B5%D0%BB%D0%B5%D0%B3%D1%80%D0%B0%D0%BC%D0%BC+%D0%B1%D0%BE%D1%82+%D0%B4%D0%BB%D1%8F+%D0%B7%D0%B0%D0%B3%D1%80%D1%83%D0%B7%D0%BA%D0%B8+%D0%BE%D1%82%D1%87%D1%91%D1%82%D0%BE%D0%B2)](https://git.io/typing-svg)
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
Используя команду -

**`git remote add amvera https://git.amvera.ru/nickname/projectname`** 

Он начнёт сборку 
![{1D481AA8-906A-472C-8336-A84C8BF515DD}](https://github.com/user-attachments/assets/001ea85c-a68d-420a-b001-1c7aaf9b261a)

Перед этим необходимо авторизироваться и создать файл .yml

Так как в моём коде добавлена настройка DEBUG, в логах сервера я могу видеть любые действия в боте, и в случае каких либо ошибок, их можно будет отследить.

![{FDA0677D-8649-4745-89D9-CF34C45974DD}](https://github.com/user-attachments/assets/4594c054-6dc2-4ecc-b588-98cd22a85c91)


Так же при обновлении проекта, необходимо просто написать в терминал команду **`git push amvera master`**
После чего хост начнёт сборку последней версии вашего кода

<h1>UPDATE 1.0</h1>
- Список изменений:

1. Добавлена система профиля пользователя.
   
![{C1D12E90-8A56-4F56-8F26-8DD85A4134AE}](https://github.com/user-attachments/assets/fd2e822f-fc72-44b3-80e4-c0af5882a38c)

2. История выполненных заказов.

![{AB356877-B706-4297-839E-6D3000C9C4F0}](https://github.com/user-attachments/assets/f48752db-cac0-4753-8475-f27c84f745ea)

3. Обработка ботом геолокации.

![{9036CE47-CDAA-41BD-877D-ACB994F56847}](https://github.com/user-attachments/assets/ed27fe4c-ac29-4ad5-8036-cb6646e64b1b)

4. Обновлён отчёт, теперь в отчёт попадает медиафайл, загруженный пользователем.

![{2FE30BD5-C90C-4EB4-A051-152EBE7488A9}](https://github.com/user-attachments/assets/33c202c9-d955-45f2-bbfe-ee5cabc3b1b1)

Обработка геолокации была реализована с помощью API ключа Яндекс Карт.
Необходимо зайти на сайт Яндекс.Кабинет разработчика — https://developer.tech.yandex.ru/services.

Далее зарегистрировать новый API ключ. 

![{FB7AFC8B-F5AC-4872-819C-4AC8185D5D17}](https://github.com/user-attachments/assets/4a5d9b4b-a25c-4b78-94b1-f916170f7045)
И выбрать подходящий тариф.

После чего нам доступен API ключ Яндекс Карт, с помощью которого мы можем реализовывать Яндекс Карты под наши задачи.

![{BCF866D1-956C-4054-8B12-22497EF4330B}](https://github.com/user-attachments/assets/8e96b75a-93a4-44a9-abf4-e0ff2c546759)





> [!CAUTION]
> 
> Не исключены баги при работе кода
>
> 
