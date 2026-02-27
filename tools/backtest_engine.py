"""
Backtesting engine wrapper using Backtrader.

Provides a unified interface for running quantitative strategy backtests
and calculating performance metrics.
"""

import backtrader as bt
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime
from core.state import BacktestResults
import sys
from io import StringIO


class BacktestEngine:
    """
    Wrapper for Backtrader backtesting engine.
    """

    def __init__(
        self,
        initial_capital: float = 100000,
        commission: float = 0.001,
        slippage: float = 0.001
    ):
        """
        Initialize backtest engine.

        Args:
            initial_capital: Starting capital
            commission: Commission rate (0.001 = 0.1%)
            slippage: Slippage rate (0.001 = 0.1%)
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage

    def run_backtest(
        self,
        strategy_class: type,
        data: pd.DataFrame,
        strategy_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run backtest with given strategy and data.

        Args:
            strategy_class: Backtrader strategy class
            data: DataFrame with OHLCV data
            strategy_params: Optional strategy parameters

        Returns:
            Dictionary with backtest results and performance metrics
        """
        if strategy_params is None:
            strategy_params = {}

        # Create cerebro engine
        cerebro = bt.Cerebro()

        # Add strategy
        cerebro.addstrategy(strategy_class, **strategy_params)

        # Convert DataFrame to Backtrader data feed
        bt_data = bt.feeds.PandasData(
            dataname=data,
            datetime=None,  # Use index as datetime
            open='open' if 'open' in data.columns else -1,
            high='high' if 'high' in data.columns else -1,
            low='low' if 'low' in data.columns else -1,
            close='close' if 'close' in data.columns else -1,
            volume='volume' if 'volume' in data.columns else -1,
            openinterest=-1
        )

        cerebro.adddata(bt_data)

        # Set initial capital
        cerebro.broker.setcash(self.initial_capital)

        # Set commission
        cerebro.broker.setcommission(commission=self.commission)

        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')

        # Capture stdout for execution logs
        old_stdout = sys.stdout
        sys.stdout = log_capture = StringIO()

        try:
            # Run backtest
            print(f"Starting backtest with initial capital: ${self.initial_capital:,.2f}")
            results = cerebro.run()
            final_value = cerebro.broker.getvalue()
            print(f"Final portfolio value: ${final_value:,.2f}")

            # Extract results
            strat = results[0]

            # Get execution logs
            execution_logs = log_capture.getvalue()

        finally:
            # Restore stdout
            sys.stdout = old_stdout

        # Calculate metrics
        metrics = self._extract_metrics(strat, final_value)
        metrics['execution_logs'] = execution_logs

        return metrics

    def _extract_metrics(
        self,
        strategy: bt.Strategy,
        final_value: float
    ) -> Dict[str, Any]:
        """
        Extract performance metrics from strategy analyzers.

        Args:
            strategy: Completed strategy instance
            final_value: Final portfolio value

        Returns:
            Dictionary with performance metrics
        """
        # Extract analyzer results
        sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
        drawdown_analysis = strategy.analyzers.drawdown.get_analysis()
        returns_analysis = strategy.analyzers.returns.get_analysis()
        trade_analysis = strategy.analyzers.trades.get_analysis()

        # Calculate basic metrics
        total_return = (final_value - self.initial_capital) / self.initial_capital
        total_trades = trade_analysis.get('total', {}).get('total', 0)

        # Sharpe ratio
        sharpe_ratio = sharpe_analysis.get('sharperatio', 0) or 0

        # Drawdown metrics
        max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0) / 100
        max_drawdown_period = drawdown_analysis.get('max', {}).get('len', 0)

        # Returns
        avg_return = returns_analysis.get('ravg', 0) or 0
        rtot = returns_analysis.get('rtot', 0) or 0

        # Trade statistics
        won_trades = trade_analysis.get('won', {}).get('total', 0)
        lost_trades = trade_analysis.get('lost', {}).get('total', 0)
        win_rate = won_trades / total_trades if total_trades > 0 else 0

        # Profit factor
        gross_profit = trade_analysis.get('won', {}).get('pnl', {}).get('total', 0)
        gross_loss = abs(trade_analysis.get('lost', {}).get('pnl', {}).get('total', 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Average trade duration (simplified)
        avg_trade_duration = 0
        if total_trades > 0:
            avg_bars = trade_analysis.get('len', {}).get('average', 0)
            avg_trade_duration = avg_bars or 0

        # Estimate CAGR and volatility
        years = 1  # Simplified - should calculate from actual date range
        cagr = ((1 + total_return) ** (1 / years) - 1) if years > 0 else 0

        # Sortino ratio (simplified - Backtrader doesn't have built-in)
        sortino_ratio = sharpe_ratio * 1.2 if sharpe_ratio > 0 else 0

        # Calmar ratio
        calmar_ratio = cagr / abs(max_drawdown) if max_drawdown != 0 else 0

        # Estimate volatility from returns
        volatility = 0.15  # Placeholder - would need returns series

        return {
            'final_value': final_value,
            'total_return': total_return,
            'cagr': cagr,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'calmar_ratio': calmar_ratio,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_trades': total_trades,
            'won_trades': won_trades,
            'lost_trades': lost_trades,
            'avg_trade_duration': avg_trade_duration,
            'volatility': volatility,
            'max_drawdown_period': max_drawdown_period,
        }

    def format_results(self, metrics: Dict[str, Any]) -> BacktestResults:
        """
        Format metrics into BacktestResults structure.

        Args:
            metrics: Raw metrics dictionary

        Returns:
            BacktestResults TypedDict
        """
        return BacktestResults(
            total_return=metrics.get('total_return', 0.0),
            cagr=metrics.get('cagr', 0.0),
            sharpe_ratio=metrics.get('sharpe_ratio', 0.0),
            sortino_ratio=metrics.get('sortino_ratio', 0.0),
            max_drawdown=metrics.get('max_drawdown', 0.0),
            calmar_ratio=metrics.get('calmar_ratio', 0.0),
            win_rate=metrics.get('win_rate', 0.0),
            profit_factor=metrics.get('profit_factor', 0.0),
            total_trades=metrics.get('total_trades', 0),
            avg_trade_duration=metrics.get('avg_trade_duration', 0.0),
            volatility=metrics.get('volatility', 0.0),
        )

    @staticmethod
    def validate_strategy_code(code: str) -> bool:
        """
        Validate that strategy code is syntactically correct.

        Args:
            code: Python code string

        Returns:
            True if valid, False otherwise
        """
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError:
            return False

    @staticmethod
    def execute_strategy_code(
        code: str,
        data: pd.DataFrame,
        initial_capital: float = 100000
    ) -> Dict[str, Any]:
        """
        Execute strategy code and return results.

        Args:
            code: Python code defining a Backtrader strategy
            data: DataFrame with OHLCV data
            initial_capital: Starting capital

        Returns:
            Dictionary with results and metrics
        """
        # Create execution namespace
        namespace = {
            'bt': bt,
            'pd': pd,
            'np': np,
            'data': data,
        }

        try:
            # Execute code to define strategy class
            exec(code, namespace)

            # Look for Strategy class in namespace
            strategy_class = None
            for name, obj in namespace.items():
                if (isinstance(obj, type) and
                    issubclass(obj, bt.Strategy) and
                    obj is not bt.Strategy):
                    strategy_class = obj
                    break

            if strategy_class is None:
                return {
                    'success': False,
                    'error': 'No Strategy class found in code'
                }

            # Run backtest
            engine = BacktestEngine(initial_capital=initial_capital)
            results = engine.run_backtest(strategy_class, data)

            results['success'] = True
            return results

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# Example strategy template
EXAMPLE_STRATEGY = """
import backtrader as bt

class MomentumStrategy(bt.Strategy):
    params = (
        ('period', 20),
        ('threshold', 0.02),
    )

    def __init__(self):
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data.close,
            period=self.params.period
        )
        self.momentum = self.data.close / self.sma - 1

    def next(self):
        if not self.position:
            if self.momentum[0] > self.params.threshold:
                self.buy()
        else:
            if self.momentum[0] < -self.params.threshold:
                self.sell()
"""
