import pandas as pd
import numpy as np

class LiveStats:
    def calculate_live_probability(self, open_price: float, current_price: float, volatility: float, time_elapsed_fraction: float):
        """
        Calculate probability of closing Green based on current progress.
        
        Args:
            open_price: Candle open
            current_price: Current real-time price
            volatility: Average True Range (ATR) or typical candle range
            time_elapsed_fraction: 0.0 to 1.0 (how much of the candle is done)
        """
        delta = current_price - open_price
        
        # If volatility is 0, avoid div by zero
        if volatility == 0:
            return 50.0
            
        # Normalize delta by volatility
        # As time passes, the "uncertainty" decreases.
        # We can model this as a drift diffusion or just a sigmoid of the Z-score.
        
        # Simple heuristic:
        # If we are +0.5 ATR up and 90% time is done, prob is very high.
        # If we are +0.1 ATR up and 10% time is done, prob is slightly > 50%.
        
        # Z-score roughly:
        z_score = (delta / volatility) * (1 + time_elapsed_fraction * 2) 
        
        # Sigmoid function to map to 0-100
        prob_green = 1 / (1 + np.exp(-z_score))
        
        return round(prob_green * 100, 1)
