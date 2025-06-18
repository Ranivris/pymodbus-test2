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


# Custom Modbus Data Block for logging HR setpoint writes
class SetpointLoggingHoldingRegisterDataBlock(ModbusSequentialDataBlock):
    def __init__(self, unit_id, *args, **kwargs):
        self.unit_id = unit_id
        super().__init__(*args, **kwargs)

    def setValues(self, address, values):
        # For logging consistency, and to match super.setValues expectation if it's a single value.
        log_values = values if isinstance(values, list) else [values]
        
        # Log only if the write is to a setpoint register address (HR 6-15)
        if 5 <= address <= 14: 
            logging.info(f"ModbusServer HR Write: unit={self.unit_id}, addr={address}, values={log_values}")
        
        # Call the original setValues. As per prompt, using listified log_values.
        # The base ModbusSequentialDataBlock.setValues can handle a list for single/multiple writes.
        super().setValues(address, log_values)


# ---------- 데이터 블록 ----------
def init_hr():
    temps = [random.randint(220, 260) for _ in range(5)]   # 22.0‑26.0℃
    return [0] + temps + [210, 230, 250, 290, 400] + [190, 190, 200, 200, 250] + [0]           # 17

def init_bits():
    return [False] + [False]*5 + [False]                   # 7

slaves = {}
"""
# This is logging every changes. 
for unit in (1, 2):
    slaves[unit] = ModbusSlaveContext(
        hr=LoggingModbusSequentialDataBlock(unit, 0, init_hr()),  # Use logging version, pass unit ID
        co=LoggingModbusSequentialDataBlock(unit, 0, init_bits()), # Use logging version, pass unit ID
        di=ModbusSequentialDataBlock(0, init_bits()), # di remains unchanged as per subtask
    )

"""
for unit in (1, 2):
    slaves[unit] = ModbusSlaveContext(
        hr=SetpointLoggingHoldingRegisterDataBlock(unit, 0, init_hr()),
        co=ModbusSequentialDataBlock(0, init_bits()),
        di=ModbusSequentialDataBlock(0, init_bits()),
    )


CTX = ModbusServerContext(slaves=slaves, single=False)

# ---------- 제어 루프 ----------
SCALE      = 0.1
COOL_RATE  = [8, 7, 6, 9, 2]   # −0.8…‑0.6℃ / 주기
WARM_RATE  = [4, 5, 3, 6, 1]   # +0.4…+0.6℃ / 주기

# Initialize last_setpoints based on init_hr()
# High setpoints are at init_hr()[6:11], Low setpoints at init_hr()[11:16]
# These are initialized to 280 and 205 respectively.
initial_high_sp = [280] * 5
initial_low_sp = [205] * 5
last_setpoints = {
    1: {'high': list(initial_high_sp), 'low': list(initial_low_sp)},
    2: {'high': list(initial_high_sp), 'low': list(initial_low_sp)}
}

def control_loop(dt=2):
    while True:
        for unit, ctx in slaves.items(): # unit is 1 or 2
            hr = ctx.getValues(3, 0, count=16) # Reads 16 registers from address 0 for the current unit
            co = ctx.getValues(1, 0, count=7)  # Reads 7 coils from address 0 for the current unit

            # Actual setpoints are at hr[5:10] for high, hr[10:15] for low
            current_high_sps = hr[5:10]
            current_low_sps = hr[10:15]

            for i in range(5): # Index for setpoint (0-4)
                # Check High Setpoints
                old_high_sp = last_setpoints[unit]['high'][i]
                new_high_sp_val = current_high_sps[i] # Renamed for clarity from subtask's new_val
                if old_high_sp != new_high_sp_val:
                    # Log with actual register address (6+i for High SPs) and raw integer values
                    logging.info(f"Server detected setpoint change: unit={unit}, addr=HR{5+i}, old_val={old_high_sp}, new_val={new_high_sp_val}")
                    last_setpoints[unit]['high'][i] = new_high_sp_val

                # Check Low Setpoints
                old_low_sp = last_setpoints[unit]['low'][i]
                new_low_sp_val = current_low_sps[i] # Renamed for clarity
                if old_low_sp != new_low_sp_val:
                    # Log with actual register address (11+i for Low SPs) and raw integer values
                    logging.info(f"Server detected setpoint change: unit={unit}, addr=HR{10+i}, old_val={old_low_sp}, new_val={new_low_sp_val}")
                    last_setpoints[unit]['low'][i] = new_low_sp_val

            # Control logic (uses potentially different indices for setpoints: h_idx=5+i, l_idx=10+i)
            for i in range(5):
                # t_idx for temp is hr[0]..hr[4]
                # h_idx for high SP is hr[5]..hr[9]
                # l_idx for low SP is hr[10]..hr[14]
                t_idx, h_idx, l_idx = i, 5+i, 10+i
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

