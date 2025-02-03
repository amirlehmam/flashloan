# utils/normalization.py

# Map exchange-specific symbols to a common symbol.
ASSET_MAP = {
    "ETHBTC": "ETH",
    "ETH-USD": "ETH",
    # Add additional mappings as needed.
}

def normalize_data(source: str, data) -> dict:
    normalized = {"exchange": source}
    try:
        if source == "binance":
            # Binance sends an array of tickers; we take the first ticker for demonstration.
            ticker = data[0]
            asset = ticker.get("s", "UNKNOWN")
            asset = ASSET_MAP.get(asset, asset)
            normalized["asset"] = asset
            normalized["price"] = float(ticker.get("c", 0))
            normalized["volume"] = float(ticker.get("v", 0))
            # Binance timestamps are in milliseconds.
            normalized["timestamp"] = ticker.get("E", 0) / 1000
        elif source == "coinbase":
            asset = data.get("product_id", "UNKNOWN")
            asset = ASSET_MAP.get(asset, asset)
            normalized["asset"] = asset
            normalized["price"] = float(data.get("price", 0))
            normalized["volume"] = float(data.get("volume_24h", 0))
            normalized["timestamp"] = data.get("time", "")
        elif source == "kraken":
            # Kraken ticker messages typically come as:
            # [channelID, { "a": [ask_price, ...], "b": [bid_price, ...], "c": [last_trade_price, volume], ... }, "pair" ]
            ticker = data[1]
            asset = data[-1]
            asset = ASSET_MAP.get(asset, asset)
            normalized["asset"] = asset
            normalized["price"] = float(ticker.get("c", [0])[0])
            normalized["volume"] = float(ticker.get("v", [0])[0]) if "v" in ticker else 0
            normalized["timestamp"] = None  # Kraken may not include a timestamp
        elif source == "chainlink":
            # Chainlink data comes in nearly normalized.
            asset = data.get("asset", "UNKNOWN")
            asset = ASSET_MAP.get(asset, asset)
            normalized = data
            normalized["exchange"] = "chainlink"
            normalized["asset"] = asset
        else:
            normalized["error"] = "Unknown source"
    except Exception as e:
        normalized["error"] = f"Normalization error: {e}"
    return normalized
