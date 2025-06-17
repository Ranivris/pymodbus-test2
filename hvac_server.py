"""
Modbus‑TCP HVAC 서버
  • 2 개의 슬레이브(Unit 1, 2)
  • HR 17 개  (0 Dummy, 1‑5 Temp, 6‑10 High, 11‑15 Low, 16 Dummy)
  • CO/DI 7개 (0 Dummy, 1‑5 ON/OFF, 6 Dummy)
pymodbus 3.9.x
"""
import random, threading, time, logging
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.server   import StartTcpServer
from pymodbus.device   import ModbusDeviceIdentification

logging.basicConfig(level=logging.INFO)

# ---------- 데이터 블록 ----------
def init_hr():
    temps = [random.randint(220, 260) for _ in range(5)]   # 22.0‑26.0℃
    return [0] + temps + [280]*5 + [205]*5 + [0]           # 17

def init_bits():
    return [False] + [False]*5 + [False]                   # 7

slaves = {}
for unit in (1, 2):
    slaves[unit] = ModbusSlaveContext(
        hr=ModbusSequentialDataBlock(0, init_hr()),
        co=ModbusSequentialDataBlock(0, init_bits()),
        di=ModbusSequentialDataBlock(0, init_bits()),
    )

CTX = ModbusServerContext(slaves=slaves, single=False)

# ---------- 제어 루프 ----------
SCALE      = 0.1
COOL_RATE  = [8, 7, 6, 9, 7]   # −0.8…‑0.6℃ / 주기
WARM_RATE  = [4, 5, 3, 6, 4]   # +0.4…+0.6℃ / 주기

def control_loop(dt=2):
    while True:
        for unit, ctx in slaves.items():
            hr = ctx.getValues(3, 0, 16)         # 3 = FC03 (Holding)
            co = ctx.getValues(1, 0, 7)          # 1 = FC01 (Coils)

            for i in range(5):
                t_idx, h_idx, l_idx =i,5 +i, 10+i
                temp, hi, lo = hr[t_idx], hr[h_idx], hr[l_idx]

                # ON/OFF 결정
                if temp >= hi:
                    co[1+i] = True
                elif temp <= lo:
                    co[1+i] = False

                # 온도 시뮬레이션
                if co[1+i]:
                    hr[t_idx] = max(lo, temp - COOL_RATE[i])
                else:
                    hr[t_idx] = min(hi, temp + WARM_RATE[i])

            # 값 반영
            ctx.setValues(3, 0, hr)              # HR
            ctx.setValues(1, 0, co)              # CO
            ctx.setValues(2, 0, co)              # DI (2 = FC02)

        time.sleep(dt)

# ---------- 서버 실행 ----------
def run():
    threading.Thread(target=control_loop, daemon=True).start()

    ident = ModbusDeviceIdentification()
    ident.VendorName  = "CIP Demo"
    ident.ProductName = "Dummy‑Wrapped 17HR/7Bit Server"

    logging.info("Modbus‑TCP server listening on :5020")
    StartTcpServer(context=CTX, identity=ident, address=("0.0.0.0", 5020))

if __name__ == "__main__":
    run()
