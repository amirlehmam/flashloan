import asyncio
import logging
from datetime import datetime
import statistics
import time
import numpy as np
import joblib

try:
    import pandas as pd
except ImportError:
    pd = None

from utils.alerts import send_email_alert, send_slack_alert

# Attempt to load the pre-trained ML model (if available)
try:
    ml_model = joblib.load("models/arbitrage_model.pkl")
    logging.info("ML model loaded successfully.")
except Exception as e:
    ml_model = None
    logging.warning(f"ML model not loaded: {e}")

def calculate_latency(ingestion_timestamp):
    current_time = time.time()
    return current_time - ingestion_timestamp

def compute_sma(price_history, window=10):
    if pd is not None:
        series = pd.Series(price_history)
        sma = series.rolling(window=window).mean().iloc[-1]
        return sma
    else:
        # Fallback: simple average
        if len(price_history) < window:
            return sum(price_history) / len(price_history)
        else:
            window_values = price_history[-window:]
            return sum(window_values) / len(window_values)

def predict_signal(features: dict) -> bool:
    if ml_model is None:
        # If no model is loaded, default to confirming the signal
        return True
    try:
        input_array = np.array([
            features['spread_percentage'], 
            features['volatility'], 
            features['volume'], 
            features['latency']
        ]).reshape(1, -1)
        probability = ml_model.predict_proba(input_array)[0][1]
        logging.info(f"ML model signal probability: {probability:.2f}")
        return probability > 0.7
    except Exception as e:
        logging.error(f"Error during ML prediction: {e}")
        return False

class ArbitrageDetector:
    def __init__(self, spread_threshold=1.0, update_interval=1.0, min_volume=50,
                 volatility_factor=1.5, history_window=10, latency_threshold=1.0):
        """
        Parameters:
          - spread_threshold: Minimum percentage spread required.
          - update_interval: Time (seconds) between detection scans.
          - min_volume: Minimum trading volume required.
          - volatility_factor: Signal triggered if spread exceeds (volatility_factor * volatility).
          - history_window: Number of data points for volatility calculation.
          - latency_threshold: Maximum acceptable latency in seconds.
        """
        self.spread_threshold = spread_threshold
        self.update_interval = update_interval
        self.min_volume = min_volume
        self.volatility_factor = volatility_factor
        self.history_window = history_window
        self.latency_threshold = latency_threshold

        self.latest_prices = {}  # { asset: { exchange: { 'price', 'volume', 'timestamp' } } }
        self.price_history = {}  # { asset: [prices...] }

    async def update_data(self, normalized_data: dict):
        asset = normalized_data.get('asset')
        exchange = normalized_data.get('exchange')
        price = normalized_data.get('price')
        volume = normalized_data.get('volume')
        ingestion_ts = normalized_data.get('timestamp')

        if asset is None or exchange is None or price is None or volume is None or ingestion_ts is None:
            logging.warning("Incomplete data received, skipping update.")
            return

        latency = calculate_latency(ingestion_ts)
        if latency > self.latency_threshold:
            logging.warning(f"High latency for {asset} from {exchange}: {latency:.3f} s")

        # Update the latest price data
        if asset not in self.latest_prices:
            self.latest_prices[asset] = {}
        self.latest_prices[asset][exchange] = {
            'price': price,
            'volume': volume,
            'timestamp': ingestion_ts
        }

        # Update price history for volatility analysis
        if asset not in self.price_history:
            self.price_history[asset] = []
        self.price_history[asset].append(price)
        if len(self.price_history[asset]) > self.history_window:
            self.price_history[asset].pop(0)

        sma = compute_sma(self.price_history[asset], window=self.history_window)
        logging.debug(f"{asset} SMA (last {self.history_window} points): {sma:.2f}")

    async def run_detection(self):
        while True:
            for asset, data_by_exchange in self.latest_prices.items():
                if len(data_by_exchange) < 2:
                    continue

                valid_data = {ex: info for ex, info in data_by_exchange.items() if info['volume'] >= self.min_volume}
                if len(valid_data) < 2:
                    continue

                prices = [(ex, info['price']) for ex, info in valid_data.items()]
                lowest_exchange, lowest_price = min(prices, key=lambda x: x[1])
                highest_exchange, highest_price = max(prices, key=lambda x: x[1])
                if lowest_price == 0:
                    continue

                spread_percentage = ((highest_price - lowest_price) / lowest_price) * 100

                volatility = None
                if asset in self.price_history and len(self.price_history[asset]) >= 2:
                    try:
                        avg_price = sum(self.price_history[asset]) / len(self.price_history[asset])
                        stdev_price = statistics.stdev(self.price_history[asset])
                        volatility = (stdev_price / avg_price) * 100
                    except Exception as e:
                        logging.error(f"Error calculating volatility for {asset}: {e}")

                criteria_met = spread_percentage >= self.spread_threshold
                if volatility is not None:
                    criteria_met = criteria_met and (spread_percentage >= self.volatility_factor * volatility)

                # Calculate average latency among valid data points
                latencies = [calculate_latency(info['timestamp']) for info in valid_data.values()]
                avg_latency = sum(latencies) / len(latencies) if latencies else 0

                features = {
                    'spread_percentage': spread_percentage,
                    'volatility': volatility if volatility is not None else 0,
                    'volume': min(info['volume'] for info in valid_data.values()),
                    'latency': avg_latency
                }

                ml_confirm = predict_signal(features)

                if criteria_met and ml_confirm:
                    timestamp = datetime.now().isoformat()
                    signal = {
                        'asset': asset,
                        'buy_exchange': lowest_exchange,
                        'sell_exchange': highest_exchange,
                        'buy_price': lowest_price,
                        'sell_price': highest_price,
                        'spread_percentage': round(spread_percentage, 2),
                        'volatility': round(volatility, 2) if volatility is not None else None,
                        'latency': round(avg_latency, 3),
                        'timestamp': timestamp
                    }
                    logging.info(f"Arbitrage Signal Detected: {signal}")
                    alert_message = f"Arbitrage Signal Detected:\n{signal}"
                    # Send email alert
                    send_email_alert("Arbitrage Opportunity Detected", alert_message, "recipient@example.com")
                    # Send Slack alert (update the webhook URL)
                    slack_webhook_url = "https://hooks.slack.com/services/your/webhook/url"
                    send_slack_alert(alert_message, slack_webhook_url)
            await asyncio.sleep(self.update_interval)
