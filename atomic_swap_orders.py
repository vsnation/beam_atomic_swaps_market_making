import json
import random
import time
import traceback

import requests
from lib.swap_api import AtomicSwapAPI
from lib.wallet_api import WalletAPI
from telegram import Bot
from pymongo import MongoClient
import logging


logging.basicConfig(filename='debug.log', level=logging.DEBUG)

with open('config.json') as conf_file:
    conf = json.load(conf_file)
    connectionString = conf['mongo']['connectionString']
    bot_token = conf['telegram_bot']['bot_token']
    httpprovider = conf['httpprovider']
    logs_tg_channel_id = conf['tg_channel_id']


atomic_swap_api = AtomicSwapAPI(httpprovider)
wallet_api = WalletAPI(httpprovider)

FEES = {
    "btc": 110000,
    "beam": 200,
    "ltc": 110000
}

_offers_count = {
    "BEAMBTC": {
        "count": 0,
        "from_curr": "BEAM",
        "to_curr": "BTC",
    },
    "BTCBEAM": {
        "count": 0,
        "from_curr": "BTC",
        "to_curr": "BEAM",
    },
    "BEAMLTC": {
        "count": 0,
        "from_curr": "BEAM",
        "to_curr": "LTC",
    },
    "LTCBEAM": {
        "count": 0,
        "from_curr": "LTC",
        "to_curr": "BEAM",
    }
}

OFFERS_LIMIT = 4
DIFF_PERCENT = 3

db_client = MongoClient(connectionString)
db = db_client.get_default_database()
col_balances = db['balances']
col_offers = db['offers']

GROTH_IN_BEAM = 100000000
BTC_MIN = 0.0015
BTC_MAX = 0.01
LTC_MIN = 0.31
LTC_MAX = 4

OFFER_EXPIRES = 720
bot = Bot(bot_token)


"""
   Check BEAM utxos to define how many inputs exists in the wallet now 
"""
def check_beam_utxos_on_available():
    try:
        free_utxos = [{"amount": _x['amount'], "id": _x['id']} for _x in wallet_api.get_utxo(count=10000)['result'] if _x['status'] == 1]
        print("FREE UTXO: %s" % len(free_utxos))
        free_utxos_count = 40
        if len(free_utxos) < free_utxos_count:
            wallet_status = wallet_api.wallet_status()
            available = wallet_status['result']['available']
            if int(available / GROTH_IN_BEAM) > 1:
                coins_amount = available / (free_utxos_count + 1)
                coins = [int(coins_amount) for _ in range(free_utxos_count)]
                result = wallet_api.split_coins(coins=coins, fee=10000)
                print(f"Splited and added {len(coins)} utxos", result)

    except Exception as exc:
        print(exc)
        traceback.print_exc()
        send_message_to_monitor(traceback.format_exc())


def send_message_to_monitor(text):
    try:
        bot.send_message(
            logs_tg_channel_id,
            text=text,
            parse_mode='HTML'
        )
    except Exception as exc:
        print(exc)
        traceback.print_exc()


def get_beam_depth(pair="BEAMBTC"):
    try:
        response = requests.get(f"https://www.binance.com/api/v3/ticker/24hr?symbol={pair}").json()
        print(response)
        return response
    except Exception:
        traceback.print_exc()
        send_message_to_monitor(traceback.format_exc())
        raise Exception


def create_offer(price: float, from_curr, to_curr, offer_expires=OFFER_EXPIRES):
    try:
        # create offer
        responses = {}
        if from_curr == "beam" and to_curr == "btc":
            to_amount = float("{0:.8f}".format(random.uniform(BTC_MIN, BTC_MAX)))
            from_amount = float("{0:.8f}".format(to_amount / price))

        elif from_curr == "btc" and to_curr == "beam":
            to_amount = float("{0:.8f}".format(random.uniform(int(BTC_MIN / price), int(BTC_MAX / price))))
            from_amount = float("{0:.8f}".format(to_amount * price))

        elif from_curr == "beam" and to_curr == "ltc":
            to_amount = float("{0:.8f}".format(random.uniform(LTC_MIN, LTC_MAX)))
            from_amount = float("{0:.8f}".format(to_amount / price))

        elif from_curr == "ltc" and to_curr == "beam":
            to_amount = float("{0:.8f}".format(random.uniform(int(LTC_MIN / price), int(LTC_MAX / price))))
            from_amount = float("{0:.8f}".format(to_amount * price))


        response = atomic_swap_api.swap_create_offer(
            from_amount=int(from_amount * GROTH_IN_BEAM),
            from_curr=from_curr,
            to_curr=to_curr,
            to_amount=int(to_amount * GROTH_IN_BEAM),
            from_curr_fee=FEES['beam'],
            to_curr_fee=FEES['btc'],
            offer_expires=offer_expires,
            comment=""
        )
        responses.update({"create_offer": response})
        response = atomic_swap_api.swap_publish_offer(response['result']['token'])
        responses.update({"publish_offer": response})
        text = f"<b>Created new offer</b>\n[{from_amount}]{from_curr.upper()} => [{to_amount}]{to_curr.upper()} with price {'{0:.8f}'.format(price)}\n" \
               f"<b>TxId</b>: #{response['result']['txId']}"
        send_message_to_monitor(text)

        return responses

    except Exception:
        traceback.print_exc()
        print(responses)
        if "error" in response.keys():
            return
        send_message_to_monitor(response)
        print(responses)


def check_offers(pair='btc'):
    try:
        ask_step = 1
        bid_step = 1
        if pair == 'btc':
            depth = get_beam_depth("BEAMBTC")
        elif pair == 'ltc':
            beam_depth = get_beam_depth("BEAMBTC")
            ltc_depth = get_beam_depth("LTCBTC")

            # do calculation between both
            depth = {
                "askPrice": "{0:.8f}".format(float(beam_depth['askPrice']) / float(ltc_depth['askPrice'])),
                "bidPrice": "{0:.8f}".format(float(beam_depth['bidPrice']) / float(ltc_depth['bidPrice']))
            }


        # get own orders
        own_offers = atomic_swap_api.swap_offers_list(filter={"status": 0})

        for _offer in sorted(own_offers['result'], key=lambda x: int(x['receive_amount'])):

            _offers_count[f'{_offer["send_currency"]}{_offer["receive_currency"]}']['count'] += 1

            if 'is_public' in _offer.keys() and not _offer['is_public']:
                response = atomic_swap_api.swap_publish_offer(_offer['token'])
                print(response)

            if _offer['receive_currency'] == "BEAM":
                _offer_rate = float("{0:.8f}".format((int(_offer['send_amount']) / GROTH_IN_BEAM) / (int(_offer['receive_amount']) / GROTH_IN_BEAM)))
                _rates_diff = abs(100 - (_offer_rate / float(depth['askPrice'])) * 100)
                _current_rate = float(depth['askPrice']) * ((100 + DIFF_PERCENT * ask_step) / 100)
                print()
                ask_step += 1

            elif _offer['send_currency'] == "BEAM":
                _offer_rate = float("{0:.8f}".format((int(_offer['receive_amount']) / GROTH_IN_BEAM) / (int(_offer['send_amount']) / GROTH_IN_BEAM)))
                _rates_diff = abs(100 - (_offer_rate / float(depth['bidPrice'])) * 100)
                _current_rate = float(depth['bidPrice']) * ((100 - DIFF_PERCENT * bid_step) / 100)
                print()
                bid_step += 1
            else:
                _rates_diff = 0
                _current_rate = 0

            if float(_rates_diff) < DIFF_PERCENT - 0.5 and _offer['status'] == 0:
                atomic_swap_api.swap_cancel_offer(_offer['txId'])
                print(create_offer(_current_rate, _offer['receive_currency'].lower(), _offer['send_currency'].lower(), offer_expires=OFFER_EXPIRES))
                print("CANCELLED AND CREATED NEW ORDER")
                text = f"<b>Cancelled offer</b> with rate {_offer_rate} {_offer['send_currency']} => [{_offer['receive_currency']}]\n" \
                       f"<b>TxId</b>: #{_offer['txId']}"
                send_message_to_monitor(text)

        if _offers_count[f"BEAM{pair.upper()}"]['count'] < OFFERS_LIMIT:
            for _x in range(OFFERS_LIMIT - _offers_count[f"BEAM{pair.upper()}"]['count']):
                _current_rate = float(depth['bidPrice']) * abs((100 - (DIFF_PERCENT + _x * 2)) / 100)
                print(
                    create_offer(
                        _current_rate,
                        pair.lower(),
                        'beam',
                        offer_expires=OFFER_EXPIRES)
                )
                time.sleep(1)

        if _offers_count[f"{pair.upper()}BEAM"]['count'] < OFFERS_LIMIT:
            for _x in range(OFFERS_LIMIT - _offers_count[f"{pair.upper()}BEAM"]['count']):
                _current_rate = float(depth['askPrice']) * abs((100 + DIFF_PERCENT + _x * 2) / 100)
                print(create_offer(
                    _current_rate,
                    'beam',
                    pair.lower(),
                    offer_expires=OFFER_EXPIRES)
                )
                time.sleep(1)


    except Exception:
        traceback.print_exc()
        send_message_to_monitor(traceback.format_exc())


def get_balances():
    try:
        beam_balance = wallet_api.wallet_status()['result']
        btc_balance = atomic_swap_api.swap_get_balance(currency='btc')['result']['available']
        ltc_balance = atomic_swap_api.swap_get_balance(currency='ltc')['result']['available']
        beam_available = '{0:.2f}'.format(beam_balance['available'] / GROTH_IN_BEAM)
        beam_locked = '{0:.2f}'.format((beam_balance['receiving'] + beam_balance['sending']) / GROTH_IN_BEAM)
        text = f"<b>Current Balance</b>:\n" \
        f"<b>BTC</b>: { '{0:.8f}'.format(float(btc_balance) / GROTH_IN_BEAM) }\n" \
        f"<b>LTC</b>: { '{0:.8f}'.format(float(ltc_balance) / GROTH_IN_BEAM) }\n" \
        f"<b>BEAM</b>: Available: { beam_available } | " \
        f"Locked: { beam_locked }"
        print(text)
        send_message_to_monitor(text)

    except Exception:
        traceback.print_exc()
        send_message_to_monitor(traceback.format_exc())

def monitor_offers_status():
    try:
        own_offers = atomic_swap_api.swap_offers_list()
        for _offer in own_offers['result']:
            rq_offer = col_offers.find_one({"_id": _offer['txId']})
            _is_offer_exists = rq_offer is not None
            if not _is_offer_exists:
                col_offers.insert_one(
                    {
                        "_id": _offer['txId'],
                        **_offer
                    }
                )
                continue

            elif _is_offer_exists and _offer['status'] != rq_offer['status']:
                if _offer['status_string'] == "completed":
                    get_balances()
                col_offers.update_one(
                    {
                        "_id": _offer['txId'],
                    },
                    {
                        "$set": _offer
                    }
                )
                text = f"<b>Status</b> of #{_offer['txId']} <b>changed</b> from {rq_offer['status_string']} to {_offer['status_string']}"
                send_message_to_monitor(text)
                continue

    except Exception:
        traceback.print_exc()
        send_message_to_monitor(traceback.format_exc())

check_beam_utxos_on_available()
check_offers('btc')
check_offers('ltc')
monitor_offers_status()
