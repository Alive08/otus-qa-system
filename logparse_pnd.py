# /usr/bin/env python3.9

import json
from argparse import ArgumentParser
from pathlib import Path
from time import time

import numpy as np
import pandas as pd

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

cols = {'host': str, 'l': str, 'user': str, 'timestamp': str, 'tz': str, 'request': str,
        'status': pd.UInt64Dtype(), 'bytes': pd.UInt64Dtype(), 'referer': str, 'ua': str, 'mils': pd.UInt64Dtype()}

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


def load_data(files):
    """Load data from given files"""

    try:
        df = pd.concat((pd.read_csv(f,
                                    delim_whitespace=True,
                                    quotechar='"',
                                    escapechar='\\',
                                    names=cols.keys(),
                                    dtype=cols,
                                    na_values=["-", ""]) for f in files)).drop(columns='l')
    except Exception as e:
        print(e)
        exit(1)

    df["timestamp"] = df["timestamp"].str.lstrip(
        "[") + " " + df.pop("tz").str.rstrip("]")
    df[['method', 'url']] = df.pop('request').str.split(' ', 1, expand=True)

    return df


def prepare_report(df: pd.DataFrame):
    '''Prepare report for console output'''

    rep = {"methods": None,
           "top_hosts": None,
           "top_requests": None
           }

    reqs = df['method'].value_counts(dropna=True, ascending=False).to_dict()
    rep['methods'] = reqs
    rep['methods']['TOTAL'] = sum(reqs.values())

    rep['top_hosts'] = df['host'].value_counts(
        dropna=True, ascending=False).head(TOP).to_dict()

    long_reqs = df.sort_values(by=['mils'], ascending=False).drop(
        columns=['user', 'status', 'bytes', 'referer', 'ua']).head(TOP)
    rep['top_requests'] = long_reqs.astype(object).replace(
        np.nan, 'Null').to_dict(orient='records')

    return rep


def out_to_console(rep):
    """Output report to console"""

    print(f"Access log(s) analysis summary:\n")
    print("HTTP methods statistics:\n")
    for k, v in rep['methods'].items():
        print(f'\t{k}: {v}')
    print()
    print(f"Top {TOP} hosts by requests:\n")
    for k, v in rep['top_hosts'].items():
        print(f'\t{k}: {v}')
    print()
    print(f"Top {TOP} longest requests:\n")
    for r in rep['top_requests']:
        duration = r.pop('mils')
        print(f'\t{"  ".join([*r.values(), duration])} ms \n')


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

    rep = prepare_report(load_data(get_files()))

    out_to_console(rep)

    if args.to_file:
        out_to_file(rep, args.to_file)


if __name__ == '__main__':

    main()
