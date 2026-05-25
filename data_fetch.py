# data_fetch.py

import requests
import pandas as pd
from config import TWELVE_DATA_API_KEY

def get_price(symbol: str) -> float:
    url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE_DATA_API_KEY}"
    res = requests.get(url).json()
    return float(res['price'])

def get_ohlc_data(symbol: str = "CHF/JPY", interval: str = '1min', outputsize: int = 50):
    url = (
        f"https://api.twelvedata.com/time_series"
        f"?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={TWELVE_DATA_API_KEY}"
    )
    res = requests.get(url).json()
    values = res.get('values', [])
    if not values:
        return None
    df = pd.DataFrame(values)
    df = df.rename(columns={'datetime': 'timestamp'})
    df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)
    df = df.sort_values(by='timestamp').reset_index(drop=True)
    return df

# Legacy helpers kept for backwards compat
def get_chfjpy_price():
    return get_price("CHF/JPY")

def get_ohlc_data_legacy():
    return get_ohlc_data("CHF/JPY")
