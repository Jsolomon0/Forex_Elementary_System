# performance.py
import pandas as pd
import numpy as np

class PerformanceAnalyzer:
    def __init__(self, trades_list, initial_balance, start_date, end_date):
        self.df = pd.DataFrame(trades_list)
        self.initial_balance = initial_balance
        # Calculate days for annualized return
        delta = end_date - start_date
        self.days = max(delta.days, 1) # Prevent division by zero
        
    def generate_report(self):
        if self.df.empty: 
            return "No trades were executed during this period. Check your strategy logic or data warmup."

         # --- CALCULATIONS ---
        total_trades = len(self.df)
        final_equity = self.df['balance'].iloc[-1]
        

        # 1. Profit & Return
        final_equity = self.df['balance'].iloc[-1]
        net_profit = final_equity - self.initial_balance
        total_return = (net_profit / self.initial_balance) * 100
        annualized_return = ((1 + (net_profit/self.initial_balance)) ** (365/self.days) - 1) * 100

        # 2. Drawdowns
        self.df['equity_peak'] = self.df['balance'].cummax()
        self.df['drawdown_pct'] = (self.df['balance'] - self.df['equity_peak']) / self.df['equity_peak']
        max_drawdown = self.df['drawdown_pct'].min() * 100
        
        # Time under Water (TuW)
        is_underwater = self.df['drawdown_pct'] < 0
        tuw_durations = []
        count = 0
        for val in is_underwater:
            if val: count += 1
            else:
                if count > 0: tuw_durations.append(count)
                count = 0
        max_tuw = max(tuw_durations) if tuw_durations else 0

        # 3. Risk & Volatility
        daily_returns = self.df['return_pct']
        sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() != 0 else 0

        # 4. Trade Statistics
        win_rate = (len(self.df[self.df['result'] == 'WIN']) / len(self.df)) * 100
        wins = self.df[self.df['pnl'] > 0]['pnl']
        losses = self.df[self.df['pnl'] < 0]['pnl']
        
        avg_win = wins.mean() if not wins.empty else 0
        avg_loss = losses.mean() if not losses.empty else 0
        profit_factor = wins.sum() / abs(losses.sum()) if not losses.empty else 0

        print_report_dict = {
            
            "--- OVERALL SUMMARY ---": "",
            "Total Trades Executed": total_trades,
            "Final Account Balance": f"${final_equity:.2f}",

            "--- RETURNS ---": "",
            "Net Profit": f"${net_profit:.2f}",
            "Total Return": f"{total_return:.2f}%",
            "Annualized Return": f"{annualized_return:.2f}%",
            
            "--- RISK & DRAWDOWN ---": "",
            "Max Drawdown": f"{max_drawdown:.2f}%",
            "Sharpe Ratio": round(sharpe_ratio, 2),
            "Time under Water": f"{max_tuw} trades",
            
            "--- TRADE STATS ---": "",
            "Win Rate": f"{win_rate:.2f}%",
            "Profit Factor": round(profit_factor, 2),
            "Avg Win": f"${avg_win:.2f}",
            "Avg Loss": f"${avg_loss:.2f}",
            "Win/Loss Ratio": round(avg_win / abs(avg_loss), 2) if avg_loss != 0 else "N/A"
        }

        report_dict = {


            "total_trades": total_trades,
            "acct_balance": final_equity,


            "net_profit": net_profit,
            "total_return": total_return,
            "ann_return": annualized_return,
            

            "mdd": max_drawdown,
            "sharpe_ratio": round(sharpe_ratio, 2),
            "tuw": max_tuw,
            

            "win_rate": win_rate,
            "profit_factor": round(profit_factor, 2),
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "wl_ratio": round(avg_win / abs(avg_loss), 2) if avg_loss != 0 else "N/A",
            "print_report": print_report_dict,
        }
        return report_dict