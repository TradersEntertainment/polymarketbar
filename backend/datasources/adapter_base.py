from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import pandas as pd

class DataAdapter(ABC):
    @abstractmethod
    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 1000) -> pd.DataFrame:
        """
        Fetch OHLCV data and return as a pandas DataFrame.
        DataFrame columns should be: ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        Timestamp should be in datetime objects (UTC).
        """
        pass

    @abstractmethod
    async def fetch_current_price(self, symbol: str) -> float:
        """
        Fetch the current real-time price.
        """
        pass
