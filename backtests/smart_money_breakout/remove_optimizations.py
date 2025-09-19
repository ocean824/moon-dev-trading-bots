#!/usr/bin/env python3
"""
Remove optimization code from Smart Money strategies
"""

import os
import re

# Files that need optimization removed
files_to_fix = [
    'smart_money_kalman.py',
    'smart_money_adx.py',
    'smart_money_mfi.py'
]

for filename in files_to_fix:
    filepath = f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/smart_money_breakout/{filename}'

    if os.path.exists(filepath):
        print(f"Fixing {filename}...")

        with open(filepath, 'r') as f:
            content = f.read()

        # Find and remove optimization block
        # Look for pattern starting with "print.*Optimizing" and ending at the next print statement
        pattern = r'# Optimization.*?print\("\n🚀 Optimizing.*?\n.*?optimization_results = bt\.optimize\([\s\S]*?\)[\s\S]*?print\(.*?optimization_results.*?\)'
        content = re.sub(pattern, '# Optimization removed - running with default parameters only', content)

        # Also remove any standalone bt.optimize calls
        pattern2 = r'optimization_results = bt\.optimize\([\s\S]*?\)[\s\S]*?print\(.*?optimization_results.*?\)'
        content = re.sub(pattern2, '# Optimization removed', content)

        # Write back
        with open(filepath, 'w') as f:
            f.write(content)

        print(f"✅ Fixed {filename}")
    else:
        print(f"❌ File not found: {filename}")

print("\n✅ All optimizations removed!")