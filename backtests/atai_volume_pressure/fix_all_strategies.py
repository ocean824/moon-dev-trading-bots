#!/usr/bin/env python3
"""
Fix stop-loss and take-profit issues in all ATAI strategies
"""

import os
import re

def fix_strategy_file(filepath):
    """Fix SL/TP issues in a strategy file"""

    with open(filepath, 'r') as f:
        content = f.read()

    # Add percentage parameters if not present
    if 'stop_loss_pct' not in content:
        # Find the parameters section and add the new parameters
        content = content.replace(
            'sl_multiplier = 2\n    tp_multiplier = 3',
            'sl_multiplier = 2\n    tp_multiplier = 3\n    stop_loss_pct = 0.03  # 3% stop loss\n    take_profit_pct = 0.06  # 6% take profit'
        )

    # Fix all buy orders - find all variations
    buy_patterns = [
        (r'(\s+)sl_price = self\.data\.Close\[-1\] - \(current_atr \* .*?\)\n(\s+)tp_price = self\.data\.Close\[-1\] \+ \(current_atr \* .*?\)\n(\s+)self\.buy\(sl=sl_price, tp=tp_price\)',
         r'\1current_price = self.data.Close[-1]\n\1sl_price = current_price * (1 - self.stop_loss_pct)\n\1tp_price = current_price * (1 + self.take_profit_pct)\n\1self.buy(sl=sl_price, tp=tp_price)'),
    ]

    # Fix all sell orders - find all variations
    sell_patterns = [
        (r'(\s+)sl_price = self\.data\.Close\[-1\] \+ \(current_atr \* .*?\)\n(\s+)tp_price = self\.data\.Close\[-1\] - \(current_atr \* .*?\)\n(\s+)self\.sell\(sl=sl_price, tp=tp_price\)',
         r'\1current_price = self.data.Close[-1]\n\1sl_price = current_price * (1 + self.stop_loss_pct)\n\1tp_price = current_price * (1 - self.take_profit_pct)\n\1self.sell(sl=sl_price, tp=tp_price)'),
    ]

    # Apply buy fixes
    for pattern, replacement in buy_patterns:
        content = re.sub(pattern, replacement, content)

    # Apply sell fixes
    for pattern, replacement in sell_patterns:
        content = re.sub(pattern, replacement, content)

    # Save the fixed file
    with open(filepath, 'w') as f:
        f.write(content)

    print(f"Fixed: {os.path.basename(filepath)}")

# Fix all strategy files
strategy_files = [
    'atai_volume_pressure_base.py',
    'atai_volume_pressure_mfi.py',
    'atai_volume_pressure_adx.py',
    'atai_volume_pressure_kalman.py'
]

for file in strategy_files:
    if os.path.exists(file):
        fix_strategy_file(file)

print("\n✅ All strategies fixed!")