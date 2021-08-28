import matplotlib.pyplot as plt
import datetime as DT
import telebot
import config
import requests
from time import time
import io
import os
import pprint


bot = telebot.TeleBot(os.environ["TOKEN"])

storage = {}
last_invocated = {}

today = DT.date.today()
access_key = config.access_key
url_list = 'https://fixer-fixer-currency-v1.p.rapidapi.com/latest'
x_rapidapi_key = os.environ["x_rapidapi_key"]
x_rapidapi_host = "fixer-fixer-currency-v1.p.rapidapi.com"
headers = {
    'x-rapidapi-host': x_rapidapi_host,
    'x-rapidapi-key': x_rapidapi_key
}


def cached(ttl_s: int):
    """
    Декоратор для кэширования
    """

    def cached_decorator(function):
        def cached_function(*args, **kwargs):
            key = f"{function.__name__}|{str(args)}|{str(kwargs)}"

            now = int(time())
            if key not in storage or last_invocated.get(key, 0) + ttl_s <= now:
                if key not in last_invocated:
                    last_invocated[key] = now
                result = function(*args, **kwargs)
                storage[key] = result
            else:
                result = storage[key]
                last_invocated[key] = now

            return result

        return cached_function

    return cached_decorator


@bot.message_handler(commands=['help'])
def help_list(message):
    """
    Команда /help для боллее детальной информации о командах
    """
    bot.send_message(
        message.chat.id,
        f"/list - Выводит список курса валют USD \n/exchange - /exchange 10 USD to RUB "
        f"(конвертация валюты из евро в российский рубль по курсу) "
        f"\n/history - /history USD/RUB n days (График курса за последние n дней до 100 дней)"
    )


@bot.message_handler(commands=['list'])
def list_message(message):
    """
    Команда /list для списка курса валют USD
    """
    querystring = {"base": "USD"}
    response = cached(ttl_s=600)(requests.get)(url_list, headers=headers, params=querystring).json()["rates"]
    text = "\n".join(f"{currency}: {amount:.2f}" for currency, amount in response.items())
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['exchange'], content_types=["text"])
def exchange_message(message):
    amount = sum([int(s) for s in message.text.split() if s.isdigit()])
    currency = message.text[-3:]
    querystring = {"amount": amount, "to": currency, "from": "USD"}
    response = cached(ttl_s=600)(requests.get)(url_list, headers=headers, params=querystring).json()["rates"]
    text = f"{response[currency] * amount:.2f} {currency}"
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=["history"], content_types=["text"])
def list_exchange(message):
    """
    Команда /history (/history EUR/RUB n days) для показа графика курса за последние n дней
    """
    if message.text[19:] == 'days':
        days = int(message.text[-6:-5])
        currency = message.text[-10:-7]
    else:
        days = int(message.text[-7:-5])
        currency = message.text[-11:-8]
    dates = []
    i = 0
    while i <= days:
        days_ago = today - DT.timedelta(days=i)
        dates.append(days_ago)
        i += 1
    historical_data = {}
    for date in dates:
        url_historical = f'https://fixer-fixer-currency-v1.p.rapidapi.com/{date}'
        querystring = {"symbols": currency, "base": "USD"}
        response = cached(ttl_s=600)(requests.get)(url_historical, headers=headers, params=querystring).json()["rates"]
        historical_data[date] = {currency: response[currency]}
    coords = {date.day: exchange_rate for date, rate in historical_data.items() for exchange_rate in rate.values()}
    print(list(coords.keys()))
    fig = plt.figure()
    plt.plot(list(coords.keys()), list(coords.values()))
    plt.xlabel("День в текущем месяце")
    plt.ylabel(f"Курс {currency}")
    plt.title(f"Курс USD/{currency}")
    fig.savefig(file := io.BytesIO())
    file.seek(0)
    bot.send_photo(message.chat.id, file)


bot.polling()