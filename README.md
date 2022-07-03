# otus-qa-system
Basic Python system programming

homework #9

HTTP Echo сервер

Реализован примитивный HTTP echo-сервер, поддерживающий только методы GET и
POST, на остальные запросы отдает 501 Not Implemented. Реализован событийный
цикл с использованием модуля selectors стандартной библиотеки. Сервер одновременно
обслуживает несколько клиентских подключений в асинхронном режиме.

Сервер ищет в запросе параметр 'status' и если он валиден с точки зрения HTTP,
возвращает ответ с данным статусом, если статус невалиден, то сервер выставляет
в ответе статус 200 OK. В тело ответа включаются заголовки, пришедшие в запросе.
Сервер понимает заголовок Connection - поддерживает соединение открытым, если
клиент прислал заголовок Connection: keep-alive и закрывает, если пришел заголовок
Connection: close. Особым образом обрабатываtтся ситуация, когда клиент прислал
запрос с неподдерживаемым методом - в ответ на такой запрос отправляется 501
Not Implemented, а в теле ответа приходит только статус ответа и соединение
принудительно разрывается. При отправке клиентом стартовой строки, содержащей
невалидный ввод, соединение также разрывается со статусом 400 Bad Request.

В качестве аргументов командной строки принимает

    --host [default '0.0.0.0']
    --port [default 9000]

Сервер не демонизируется, работает только в консольном режиме.
Сервер можно запускать в докер-контейнере, для этого сначала нужно построить образ:
    
    docker build --tag echo-http .

а затем запустить контейнер с сервером:

    docker run --rm -d --name echo -p 9000:9000 echo-http

для просмотра лога запущенного в докер-контейнере сервера используется команда

    docker logs -f echo
