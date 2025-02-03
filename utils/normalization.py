def normalize_data(source: str, data) -> dict:
    """
    Normalize data from different sources to a common schema:
    {
        "exchange": source,
        "asset": <symbol>,
        "price": <price>,
        "volume": <volume>,
        "timestamp": <timestamp>
    }
    """
    normalized = {"exchange": source}
    
    try:
        if source == "binance":
            # Binance sends an array of tickers; we take the first one for demonstration.
            ticker = data[0]
            normalized["asset"] = ticker.get("s", "UNKNOWN")
            normalized["price"] = float(ticker.get("c", 0))
            normalized["volume"] = float(ticker.get("v", 0))
            # Binance timestamps are in milliseconds
            normalized["timestamp"] = ticker.get("E", 0) / 1000  
        elif source == "coinbase":
            # Coinbase ticker message sample fields: product_id, price, volume_24h, time
            normalized["asset"] = data.get("product_id", "UNKNOWN")
            normalized["price"] = float(data.get("price", 0))
            normalized["volume"] = float(data.get("volume_24h", 0))
            normalized["timestamp"] = data.get("time", "")
        elif source == "kraken":
            # Kraken ticker messages typically come as:
            # [channelID, { "a": [ask_price, ...], "b": [bid_price, ...], "c": [last_trade_price, volume], ... }, "pair" ]
            ticker = data[1]
            normalized["asset"] = data[-1]
            normalized["price"] = float(ticker.get("c", [0])[0])
            normalized["volume"] = float(ticker.get("v", [0])[0]) if "v" in ticker else 0
            normalized["timestamp"] = None  # Kraken often omits a timestamp in this feed
        elif source == "chainlink":
            # Our simulated on-chain data is nearly in the desired format.
            normalized = data
            normalized["exchange"] = "chainlink"
        else:
            normalized["error"] = "Unknown source"
    except Exception as e:
        normalized["error"] = f"Normalization error: {e}"
    
    return normalized
