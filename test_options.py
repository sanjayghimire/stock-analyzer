from data_engine import get_all_data
from options_engine import get_most_active_expiry, get_best_option

print("Fetching AAPL data...")
data   = get_all_data("AAPL", "1h")

if data['options']:
    print(f"Options expiries available: {list(data['options'].keys())[:6]}")
    expiry = get_most_active_expiry(data['options'])
    print(f"Selected expiry: {expiry}")

    if expiry:
        calls = data['options'][expiry]['calls']
        puts  = data['options'][expiry]['puts']
        print(f"Calls available: {len(calls)}")
        print(f"Puts available:  {len(puts)}")
        print(f"Sample call strikes: {calls['strike'].tolist()[:5]}")

        best = get_best_option(data['options'], 263.0, "BUY", expiry)
        if best:
            print(f"\n✅ Best option found!")
            print(f"Strike:  ${best['strike']}")
            print(f"Premium: ${best['premium']}")
            print(f"Delta:   {best['delta']}")
            print(f"Theta:   {best['theta']}")
            print(f"IV:      {best['iv']}%")
        else:
            print("❌ get_best_option returned None")
    else:
        print("❌ No expiry selected")
else:
    print("❌ No options data returned at all")