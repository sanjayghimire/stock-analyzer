import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import warnings
import time
warnings.filterwarnings('ignore')

# Fix for rate limiting on cloud servers
import requests
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

def get_stock_data(ticker, interval='1h', period='60d'):
    try:
        # Retry up to 3 times with delay
        for attempt in range(3):
            try:
                stock = yf.Ticker(ticker)

                if interval in ['1m', '2m', '5m', '15m', '30m']:
                    period = '7d'
                elif interval in ['1h']:
                    period = '60d'
                else:
                    period = '1y'

                df = stock.history(period=period, interval=interval)

                if df.empty and attempt < 2:
                    time.sleep(2)
                    continue

                if df.empty:
                    return None, None

                df.index = pd.to_datetime(df.index)
                df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
                df.columns = ['open', 'high', 'low', 'close', 'volume']
                df = df.dropna()

                info = stock.info
                return df, info

            except Exception as e:
                if 'Rate' in str(e) or 'Too Many' in str(e):
                    print(f"Rate limited — waiting 3 seconds (attempt {attempt+1})")
                    time.sleep(3)
                    continue
                raise e

        return None, None

    except Exception as e:
        print(f"Error fetching stock data: {e}")
        return None, None
    try:
        stock = yf.Ticker(ticker)
        
        if interval in ['1m', '2m', '5m', '15m', '30m']:
            period = '7d'
        elif interval in ['1h']:
            period = '60d'
        else:
            period = '1y'

        df = stock.history(period=period, interval=interval)
        
        if df.empty:
            return None, None
            
        df.index = pd.to_datetime(df.index)
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        df.columns = ['open', 'high', 'low', 'close', 'volume']
        df = df.dropna()
        
        info = stock.info
        
        return df, info
    except Exception as e:
        print(f"Error fetching stock data: {e}")
        return None, None

def get_premarket_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        pre_market_price = info.get('preMarketPrice', None)
        regular_price = info.get('regularMarketPrice', None)
        previous_close = info.get('previousClose', None)
        
        if pre_market_price and regular_price:
            gap = pre_market_price - previous_close
            gap_pct = (gap / previous_close) * 100
            gap_direction = 'GAP UP' if gap > 0 else 'GAP DOWN'
        else:
            gap = 0
            gap_pct = 0
            gap_direction = 'No gap data'
            
        return {
            'pre_market_price': pre_market_price,
            'regular_price': regular_price,
            'previous_close': previous_close,
            'gap': round(gap, 2),
            'gap_pct': round(gap_pct, 2),
            'gap_direction': gap_direction
        }
    except Exception as e:
        print(f"Error fetching premarket data: {e}")
        return {}

def get_options_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options
        
        if not expirations:
            return None, None
            
        options_data = {}
        for exp in expirations[:6]:
            opt_chain = stock.option_chain(exp)
            options_data[exp] = {
                'calls': opt_chain.calls,
                'puts': opt_chain.puts
            }
            
        return options_data, expirations
    except Exception as e:
        print(f"Error fetching options data: {e}")
        return None, None

def get_analyst_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        return {
            'target_mean': info.get('targetMeanPrice', None),
            'target_high': info.get('targetHighPrice', None),
            'target_low': info.get('targetLowPrice', None),
            'recommendation': info.get('recommendationKey', None),
            'num_analysts': info.get('numberOfAnalystOpinions', None)
        }
    except Exception as e:
        print(f"Error fetching analyst data: {e}")
        return {}

def get_earnings_date(ticker):
    try:
        stock = yf.Ticker(ticker)
        calendar = stock.calendar
        
        if calendar is not None and not calendar.empty:
            earnings_date = calendar.iloc[0].get('Earnings Date', None)
            if earnings_date:
                days_until = (pd.Timestamp(earnings_date) - pd.Timestamp.now()).days
                return {
                    'earnings_date': str(earnings_date),
                    'days_until': days_until,
                    'warning': days_until <= 14
                }
        return {'earnings_date': 'Unknown', 'days_until': 999, 'warning': False}
    except Exception as e:
        return {'earnings_date': 'Unknown', 'days_until': 999, 'warning': False}

def get_all_data(ticker, interval='1h'):
    print(f"Fetching data for {ticker}...")
    
    df, info = get_stock_data(ticker, interval)
    premarket = get_premarket_data(ticker)
    options, expirations = get_options_data(ticker)
    analyst = get_analyst_data(ticker)
    earnings = get_earnings_date(ticker)
    
    return {
        'df': df,
        'info': info,
        'premarket': premarket,
        'options': options,
        'expirations': expirations,
        'analyst': analyst,
        'earnings': earnings,
        'ticker': ticker,
        'interval': interval
    }

if __name__ == "__main__":
    data = get_all_data("AAPL", "1h")
    
    if data['df'] is not None:
        print(f"\n✅ Stock data fetched successfully!")
        print(f"Rows of data: {len(data['df'])}")
        print(f"Latest price: ${data['df']['close'].iloc[-1]:.2f}")
        print(f"Pre-market: {data['premarket']}")
        print(f"Analyst target: ${data['analyst'].get('target_mean', 'N/A')}")
        print(f"Earnings: {data['earnings']}")
    else:
        print("❌ Failed to fetch data")