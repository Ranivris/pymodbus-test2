from pymodbus.client import ModbusTcpClient
import time

MB_HOST, MB_PORT = "127.0.0.1", 5020
UNITS = (1, 2)
SCALE = 0.1                  # 0.1 ℃

def read_hr(client, unit):
    r = client.read_holding_registers(address=0, count=16, slave=unit)
    return None if r.isError() else r.registers[0:]      # Dummy(0) 제거 → 1‑15

def read_bits(client, unit, fn):
    call = client.read_coils if fn == "co" else client.read_discrete_inputs
    r = call(address=0, count=6, slave=unit)             # 0‑5 (앞 Dummy 포함)
    return None if r.isError() else r.bits[1:6]          # Dummy(0) 제거 X

def show(unit, t, h, l, co):
    print(f"\n─── Slave {unit} ──────────────────────────────")
    print (t)
    print (h)
    print (l)
    print (co)        
    for i in range(5):
        temp = t[i] * SCALE
        hi, lo = h[i]*SCALE, l[i]*SCALE
        st = "🟢 ON" if co[i] else "🔴 OFF"
        print(f"AC{ i+1 + (unit-1)*5 :>2} │ {temp:5.1f}°C │ {st} │ H {hi:4.1f} / L {lo:4.1f}")

def main(delay=2):
    c = ModbusTcpClient(MB_HOST, port=MB_PORT)
    if not c.connect():
        print("❌ 서버 연결 실패"); return
    try:
        while True:
            for u in UNITS:
                hr = read_hr(c,u); co = read_bits(c,u,"co")
                if None in (hr,co):
                    print(f"⚠️  슬레이브 {u} 읽기 오류"); continue
                temps, highs, lows = hr[0:5], hr[5:10], hr[10:15]
                show(u, temps, highs, lows, co)
            time.sleep(delay)
    finally:
        c.close()

if __name__ == "__main__":
    main()

