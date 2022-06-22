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

TOP = 3

PATTERN = r'(?P<host>(\d{1,3}\.){3}\d{1,3})(\.*\S*)\s(?P<l>\S+)\s(?P<user>\S+)\s\[(?P<time>.+)\]\s\"(?P<method>GET|POST|HEAD|OPTIONS|PUT|TRACE|TRACK|DELETE|FLURP)\s(?P<url>\S+)\s(\S+)\"\s(?P<status>\d{3})\s(?P<bytes>\S+)\s\"(?P<referer>\S*)\"\s\"(?P<ua>.*)\"\s\"(?P<duration>\S+)\"'

parser = ArgumentParser()
group = parser.add_mutually_exclusive_group()
group.add_argument('--file', nargs='?', const='access.log', default=None)
group.add_argument('--dir', nargs='?', const='./', default=None)
parser.add_argument('--to-file', nargs='?',
                    const='access_stats.json', default=None)
parser.add_argument('--pattern', default='access*.log*')
args = parser.parse_args()


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


def prepare_report(data):
    '''Prepare report for console output'''

    rep = {}

    for raw in data:

        if not raw or not len(raw):
            continue

        for k, v in raw.items():

            if k in ('host', 'method'):
                if not rep.get(k):
                    rep.update({k: {}})
                if not rep[k].get(raw[k]):
                    rep[k].update({raw[k]: 0})
                rep[k].update({raw[k]: rep[k][raw[k]] + 1})

            if 'duration' == k:
                if not rep.get('duration'):
                    rep['duration'] = []
                rep['duration'].append(raw)
                rep['duration'] = sorted(
                    rep['duration'], key=lambda x: x['duration'])
                # only TOP durations
                if len(rep['duration']) > TOP:
                    rep['duration'].pop(0)
    # only TOP hosts
    rep['method'] = dict(
        reversed(sorted(rep['method'].items(), key=lambda x: x[1])))
    rep['host'] = dict(itertools.islice(
        reversed(sorted(rep['host'].items(), key=lambda x: x[1])), TOP))

    return rep


def out_to_console(rep):
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
    for r in rep['duration']:
        duration = r.pop('duration')
        print(f'\t{"  ".join([*r.values(), duration])} ms \n')


def out_to_file(rep, file):
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