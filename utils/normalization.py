def normalize_data(source: str, data: dict) -> dict:
    """
    Normalize incoming data from various sources to a common format:
    
    {
        "exchange": source,
        "asset": <symbol>,
        "price": <price>,
        "volume": <volume>,
        "timestamp": <timestamp in seconds or ISO format>
    }
    
    Parameters:
    - source: Identifier for the data source (e.g., 'binance', 'coinbase', 'kraken', 'chainlink')
    - data: Raw data from the source (could be a dict or list)
    """
    normalized = {"exchange": source}
    
    try:
        if source == "binance":
            # Binance sends an array of tickers; we take the first ticker for demonstration.
            ticker = data[0]
            normalized["asset"] = ticker.get("s", "UNKNOWN")
            normalized["price"] = float(ticker.get("c", 0))
            normalized["volume"] = float(ticker.get("v", 0))
            # Binance timestamp is in milliseconds
            normalized["timestamp"] = ticker.get("E", 0) / 1000  
        elif source == "coinbase":
            # Coinbase ticker message sample fields: product_id, price, volume_24h, time
            normalized["asset"] = data.get("product_id", "UNKNOWN")
            normalized["price"] = float(data.get("price", 0))
            normalized["volume"] = float(data.get("volume_24h", 0))
            normalized["timestamp"] = data.get("time", "")
        elif source == "kraken":
            # Kraken ticker messages typically come as a list:
            # [channelID, { "a": [ask_price, ...], "b": [bid_price, ...], "c": [last_trade_price, volume], ... }, "pair" ]
            ticker = data[1]
            normalized["asset"] = data[-1]  # The pair info is typically the last element
            normalized["price"] = float(ticker.get("c", [0])[0])
            # Some Kraken messages include volume info; otherwise, set to 0
            normalized["volume"] = float(ticker.get("v", [0])[0]) if "v" in ticker else 0
            normalized["timestamp"] = None  # Kraken does not always include timestamp data in this feed
        elif source == "chainlink":
            # Our simulated on-chain data is already near the desired format.
            normalized = data
            normalized["exchange"] = "chainlink"
        else:
            normalized["error"] = "Unknown source"
    except Exception as e:
        normalized["error"] = f"Normalization error: {e}"
    
    return normalized
