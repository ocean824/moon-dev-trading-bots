#!/usr/bin/env python3
"""
Update all ATAI strategies to use multi_data_tester
"""

import os

# The new main section to add
new_main_section = '''if __name__ == "__main__":
    # Use multi_data_tester to test on all 25 data sources
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    print("\\n🎯 Testing {} Strategy")
    print("=" * 80)

    # Test on all available data sources
    results = test_on_all_data(
        {},
        '{}',
        cash=10000,
        commission=0.002,
        verbose=True
    )

    if results is not None:
        print("\\n📊 Strategy Summary:")
        print(f"✅ Tested on {{len(results)}} data sources")
        print(f"📈 Average Return: {{results['Return_%'].mean():.2f}}%")
        print(f"📊 Average Sharpe Ratio: {{results['Sharpe'].mean():.3f}}")
        print(f"📉 Average Max Drawdown: {{results['Max_DD_%'].mean():.2f}}%")
        print(f"🎯 Average Win Rate: {{results['Win_Rate_%'].mean():.2f}}%")

    print("\\n🌙 {} Strategy Testing Complete! 🚀")
'''

def update_strategy(filepath, class_name, display_name):
    """Update a strategy file to use multi_data_tester"""

    with open(filepath, 'r') as f:
        lines = f.readlines()

    # Find where the main section starts
    main_start = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('if __name__ == "__main__":'):
            main_start = i
            break

    if main_start == -1:
        print(f"Could not find main section in {filepath}")
        return

    # Replace everything from main_start to end
    new_lines = lines[:main_start]
    new_lines.append(new_main_section.format(display_name, class_name, class_name, display_name))

    with open(filepath, 'w') as f:
        f.writelines(new_lines)

    print(f"Updated {filepath}")

# Update all strategies
strategies = [
    ('atai_volume_pressure_base.py', 'ATAIVolumePressureBase', 'ATAI Volume Pressure Base'),
    ('atai_volume_pressure_mfi.py', 'ATAIVolumePressureMFI', 'ATAI Volume Pressure MFI'),
    ('atai_volume_pressure_adx.py', 'ATAIVolumePressureADX', 'ATAI Volume Pressure ADX'),
    ('atai_volume_pressure_kalman.py', 'ATAIVolumePressureKalman', 'ATAI Volume Pressure Kalman')
]

for filename, class_name, display_name in strategies:
    if os.path.exists(filename):
        update_strategy(filename, class_name, display_name)

print("\n✅ All strategies updated to use multi_data_tester!")