# otus-qa-system

Python system programming examples

Homework #8

Скрипт parseps.py выводит отчет об активности пользователей в Linux системе, используя результаты работы системной утилиты ps. 

Homework #9

Web-server access log parser

Представлено два варианта реализации скрипта - с использованием модуля re (регулярные выражения)
и модуля pandas (аналитика). Оба скрипта принимают одинаковые аргументы и выдают однотипные результаты:

--file [путь к файлу], по умолчанию - ./access.log
--dir [путь к каталогу], по умолчанию - ./
--pattern [паттерн] - паттерн имени логов, по умолчанию - access*.log*
--to-file [путь к файлу] - сохранить обработанную статистику в указанный файл в формате json.
  Если имя не указано, сохраняет в ./access_stats.json
--top [N] - число "лидеров", выводимых в статистике, по умолчанию - 3

примеры использования:

1) анализ одиночного файла из текущего каталога:

    logparse_re.py --file - будет искать access.log в текущем каталоге
    
    logparse_re.py --file ../non-default-name.log - указан путь к файлу в качестве параметра

2) анализ нескольких файлов

    logparse_re.py --dir - будет искать файлы по паттерну access*.log* в текущем каталоге
    
    logparse_re.py --dir ./logs - будет искать файлы по паттерну access*.log* в указанном каталоге

3) запись статистики в файл:

    logparse_re.py --top 5 --dir ./logs --to-file ./logs/stats.json - будет искать файлы по паттерну access*.log* в указанном каталоге, результаты запишет в ./logs/stats.json

Для сравнения и развлечения в скриптах подсчитывается и выводится в консоль время, затраченное на работу.
Эксперимент показал, что небольших файлах (~1000 записей), быстрее работает вариант с регулярными выражениями,
но при обработке больших файлов (> 1 млн. записей) время выполнения сравнивается, либо становится меньше у
скрипта на pandas. На предоставленном файле (> 3 млн. записей) вариант на pandas выигрывает около 5 с.


Homework #10

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
