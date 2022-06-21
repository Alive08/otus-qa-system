import threading
import time


counter = 10000000


def f1(num):
    global counter
    while counter:
        time.sleep(num)
        counter -= 1
        print(counter)

def f2(num):
    global counter
    while counter:
        time.sleep(num)
        counter -= 1
        print(counter)

thr1 = threading.Thread(target=f1, name='thr1', args=(0.0,))
thr2 = threading.Thread(target=f2, name='thr2', args=(0.0,))

thr1.start()
thr2.start()

while counter:
    time.sleep(0)
    counter -= 1
    print(counter)



