from random import randint


def generate_mac():
    r255 = lambda: randint(16, 255)
    return f'52:54:00:{r255():x}:{r255():x}:{r255():x}'
