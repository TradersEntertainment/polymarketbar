import pandas as pd
import numpy as np

def calculate_streaks(df):
    # Determine candle colors
    df['color'] = np.where(df['close'] >= df['open'], 'green', 'red')
    
    # Calculate streaks
    df['ts'] = df.index
    # Shift logic: True where color changes
    # cumsum() increments group ID every time color changes
    df['streak_group'] = (df['color'] != df['color'].shift()).cumsum()
    
    streaks = df.groupby('streak_group').agg(
        color=('color', 'first'),
        length=('color', 'count'),
        end_time=('ts', 'max')
    )
    
    return df, streaks

def print_result(scenario_name, df):
    print(f"\n--- {scenario_name} ---")
    df_res, streaks = calculate_streaks(df.copy())
    
    print("DataFrame with Streak Info:")
    print(df_res[['open', 'close', 'color', 'streak_group']])
    
    current_streak = streaks.iloc[-1]
    print(f"Current Streak Result: {current_streak['length']} {current_streak['color']}")

# Mock Data Generation
def create_mock_df(prices):
    # prices list of tuples (open, close)
    df = pd.DataFrame(prices, columns=['open', 'close'])
    df.index = pd.date_range(start='2024-01-01', periods=len(df), freq='15min')
    return df

# Scenario 1: 3 Green Closed, 1 Green Open (Partial)
# Expectation: If current included, Streak 4 G.
data1 = [
    (100, 101), # G
    (101, 102), # G
    (102, 103), # G
    (103, 104), # G (Open)
]
df1 = create_mock_df(data1)
print_result("Scenario 1: 4 Greens", df1)

# Scenario 2: 3 Green Closed, 1 Red Open (Partial)
# Expectation: Streak 1 R.
data2 = [
    (100, 101), # G
    (101, 102), # G
    (102, 103), # G
    (103, 102), # R (Open)
]
df2 = create_mock_df(data2)
print_result("Scenario 2: 3 G -> 1 R", df2)

# Scenario 3: 1 Red, 1 Green
data3 = [
    (100, 99),  # R
    (99, 100),  # G
]
df3 = create_mock_df(data3)
print_result("Scenario 3: 1 R -> 1 G", df3)

# Scenario 4: User Report potential - alternating
# G R G R G
data4 = [
    (100, 101), # G
    (101, 100), # R
    (100, 101), # G
    (101, 100), # R
    (100, 101), # G
]
df4 = create_mock_df(data4)
print_result("Scenario 4: Alternating", df4)
