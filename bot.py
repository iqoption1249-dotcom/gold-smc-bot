import os
import time
import requests
import pandas as pd

# --- CONFIGURATION (Secure Cloud Setup) ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
DATA_API_KEY = os.getenv("DATA_API_KEY")

last_signal_time = 0 
last_signal_type = None

def fetch_live_xauusd(interval="15min", limit=50):
    url = f"https://financialmodelingprep.com{interval}/FOREX:XAUUSD?apikey={DATA_API_KEY}"
    try:
        response = requests.get(url).json()
        if not response or "Error Message" in response: return pd.DataFrame()
        df = pd.DataFrame(response[:limit]).iloc[::-1].reset_index(drop=True)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns: df[col] = df[col].astype(float)
        return df
    except:
        return pd.DataFrame()

def is_market_manipulated(df):
    if df.empty or 'volume' not in df.columns: return False
    avg_volume = df['volume'].tail(20).mean()
    if df['volume'].iloc[-1] > (avg_volume * 4.0): return True
    return False

def analyze_pure_smc():
    df = fetch_live_xauusd(interval="15min", limit=40)
    if df.empty or len(df) < 15 or is_market_manipulated(df): return None

    c1_close = df['close'].iloc[-1]
    c2_open, c2_close = df['open'].iloc[-2], df['close'].iloc[-2]
    c2_high, c2_low = df['high'].iloc[-2], df['low'].iloc[-2]
    c3_high, c3_low = df['high'].iloc[-3], df['low'].iloc[-3]
    c3_open, c3_close = df['open'].iloc[-3], df['close'].iloc[-3]
    c4_high, c4_low = df['high'].iloc[-4], df['low'].iloc[-4]
    
    pure_volatility = (df['high'].tail(14) - df['low'].tail(14)).mean()
    local_high = df['high'].iloc[-15:-2].max()
    local_low = df['low'].iloc[-15:-2].min()

    if c1_close > local_high and c2_low > c4_high and c2_close > c3_high and c3_close < c3_open:
        live_entry = c1_close + 0.20 
        sl_level = c3_low - (pure_volatility * 0.4)
        return {"type": "BUY", "entry": live_entry, "sl": sl_level, "tp": live_entry + ((live_entry - sl_level) * 2.0)}

    if c1_close < local_low and c2_high < c4_low and c2_close < c3_low and c3_close > c3_open:
        live_entry = c1_close - 0.20
        sl_level = c3_high + (pure_volatility * 0.4)
        return {"type": "SELL", "entry": live_entry, "sl": sl_level, "tp": live_entry - ((sl_level - live_entry) * 2.0)}
    return None

def send_telegram_alert(signal):
    url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
    emoji = "🟢 NOW BUY MARKET" if signal["type"] == "BUY" else "🔴 NOW SELL MARKET"
    msg = f"🛡️ *MANIPULATION-FILTERED GOLD ALERT*\n\n📊 *ACTION:* {emoji}\n🎯 *ENTRY:* {signal['entry']:.2f}\n🛑 *SL:* {signal['sl']:.2f}\n🎁 *TP:* {signal['tp']:.2f}"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    while True:
        current_time = time.time()
        signal = analyze_pure_smc()
        if signal:
            if (current_time - last_signal_time) > 18000 or signal["type"] != last_signal_type:
                fresh_df = fetch_live_xauusd(interval="15min", limit=2)
                if not fresh_df.empty: signal['entry'] = fresh_df['close'].iloc[-1]
                send_telegram_alert(signal)
                last_signal_time, last_signal_type = current_time, signal["type"]
        time.sleep(300)
