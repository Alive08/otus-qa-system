# /usr/bin/env python3

import itertools
import json
import re
from argparse import ArgumentParser
from pathlib import Path
from time import time

'''
Формат записи в файле лога (combined):
%h %l %u %t "%r" %>s %b "%{Referer}i" "%{User-Agent}i" %D
%h - имя удаленного хоста
%l - длинное имя удаленного хоста
%u - имя аутентифицированного пользователя
%t - время получения запроса
%r - тип запроса, его содержимое и версия
%s - код состояния HTTP
%b - количество отданных сервером байт
%{Referer} - URL-источник запроса
%{User-Agent} - HTTP-заголовок, содержащий информацию о запросе
%D - длительность запроса в миллисекундах
'''
# ip: (\d{1,3}\.){3}\d{1,3}), но в этом поле встречаются и доменные имена
PATTERN = r'(?P<host>\S+)\s+(?P<l>\S+)\s+(?P<user>\S+)\s+\[(?P<time>.+)\]\s+\"(?P<method>GET|POST|HEAD|OPTIONS|PUT|TRACE|TRACK|DELETE|FLURP)\s+(?P<url>\S+)\s+(\S+)\"\s+(?P<status>\d{3})\s+(?P<bytes>\S+)\s+\"(?P<referer>.*)\"\s+\"(?P<ua>.*)\"\s+(?P<duration>\S+)'

parser = ArgumentParser()
group = parser.add_mutually_exclusive_group()
group.add_argument('--file', nargs='?', const='access.log', default=None)
group.add_argument('--dir', nargs='?', const='./', default=None)
parser.add_argument('--to-file', nargs='?',
                    const='access_stats.json', default=None)
parser.add_argument('--pattern', default='access*.log*')
parser.add_argument('--top', type=int, default=3)
args = parser.parse_args()

TOP = args.top


def benchmark(func):

    def wrapper(*args, **kwargs):
        start = time()
        result = func(*args, **kwargs)
        print('Elapsed time:', time() - start)
        return result

    return wrapper


def get_files():
    """Parse arguments"""

    file = args.file
    dir = args.dir
    pat = args.pattern
    if dir:
        files = Path(dir).glob(pat)
    elif file:
        files = [Path(file)]
    else:
        print("No file or directory was given")
        exit(1)

    return files


def gen_data(files):
    """Load data from given files"""

    for file in files:
        try:
            with open(file, 'r') as f:
                for line in f:
                    line = line.strip(' \n\r')
                    if line:
                        yield parse_line(line)
        except Exception as e:
            print(e)
            exit(1)


def parse_line(line):
    raw = re.match(PATTERN, line)
    if raw:
        return raw.groupdict()
    else:
        print('NO_MATCH ', line)


def prepare_report(data):
    '''Prepare report for console output'''

    rep = {"method": {},
           "host": {},
           "request": []
           }

    for row in data:

        if not row or not len(row):
            continue

        for key in ('l', 'user', 'bytes', 'referer', 'ua'):
            row.pop(key)

        for k, v in row.items():

            if k in ('host', 'method'):
                if not rep[k].get(v):
                    rep[k].update({v: 0})
                rep[k].update({v: rep[k][v] + 1})

            if k == 'duration':
                rep['request'].append(row)
                rep['request'] = sorted(
                    rep['request'], key=lambda x: int(x['duration']))
                if len(rep['request']) > TOP:
                    rep['request'].pop(0)

    rep['method'] = dict(
        reversed(sorted(rep['method'].items(), key=lambda x: x[1])))
    rep['method'].update({'TOTAL': sum(rep['method'].values())})
    rep['host'] = dict(itertools.islice(
        reversed(sorted(rep['host'].items(), key=lambda x: x[1])), TOP))
    rep['request'].reverse()

    return rep


def out_to_console(rep):
    """Output report to console"""

    print(f"Access log(s) analysis summary:\n")
    print("HTTP methods statistics:\n")
    for k, v in rep['method'].items():
        print(f'\t{k}: {v}')
    print()
    print(f"Top {TOP} hosts by requests:\n")
    for k, v in rep['host'].items():
        print(f'\t{k}: {v}')
    print()
    print(f"Top {TOP} longest requests:\n")
    for r in rep['request']:
        print(
            f"\t{r['host']} {r['time']} {r['method']} {r['url']} {r['duration']} ms \n")


def out_to_file(rep, file):
    """Output json report to file"""

    try:
        with open(file, 'w') as f:
            json.dump(rep, f, indent=4)
    except Exception as e:
        print(e)
        exit(1)


@benchmark
def main():

    rep = prepare_report(gen_data(get_files()))

    out_to_console(rep)

    if args.to_file:
        out_to_file(rep, args.to_file)


if __name__ == '__main__':

    main()
