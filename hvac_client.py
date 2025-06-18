import logging # Added import
from flask import Flask, jsonify, request, render_template
from pymodbus.client import ModbusTcpClient

MB_HOST, MB_PORT = "127.0.0.1", 5020
ROOMS = [
    "창고 101","창고 102","창고 103","창고 104","창고 105",
    "창고 201","창고 202","창고 203","창고 204","창고 205"
]
SCALE = 0.1

# Custom logging filter for /api/data
class APIDataFilter(logging.Filter):
    def __init__(self, name=''):
        super().__init__(name)
        self.count = 0

    def filter(self, record):
        # Check if record.args is a tuple and has enough elements
        if isinstance(record.args, tuple) and len(record.args) >= 2:
            # record.args for Werkzeug often is (request_line, status_code, ...)
            # e.g., ("GET /api/data HTTP/1.1", "200", ...)
            is_api_data_success = (
                record.args[0] == "GET /api/data HTTP/1.1" and
                record.args[1] == "200"
            )

            if is_api_data_success:
                self.count += 1
                # Log 1st, 11th, 21st, etc. (roughly 1 in 10)
                if self.count % 10 == 1:
                    return True
                return False
        # Allow all other log records
        return True

app = Flask(__name__, template_folder="templates")  # templates/dashboard.html
app.logger.setLevel(logging.INFO) # Set app.logger level to INFO

# Apply the filter to Werkzeug logger
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addFilter(APIDataFilter())
werkzeug_logger.setLevel(logging.INFO) # Ensure INFO level is processed

# ---------- Modbus ----------
def read_hr(client, unit):
    r = client.read_holding_registers(0, count=16, slave=unit)
    return None if r.isError() else r.registers          # Dummy 포함

def read_bits(client, unit):
    r = client.read_coils(1, count=5, slave=unit)
    return None if r.isError() else r.bits               # Dummy 포함 X 

def write_reg(client, unit, addr, val):
    w = client.write_register(addr, val, slave=unit)
    return not w.isError()

# ---------- API ----------
@app.route("/api/data")
def api_data():
    with ModbusTcpClient(MB_HOST, port=MB_PORT, timeout=2) as c:
        if not c.connect():
            return jsonify({"error":"server offline"}),500
        out={}
        for u in (1,2):
            hr = read_hr(c,u); co = read_bits(c,u)
            if hr is None or co is None:
                return jsonify({"error":f"read fail {u}"}),500
            out[f"t{u}"]=hr[0:5]; out[f"h{u}"]=hr[5:10]; out[f"l{u}"]=hr[10:15]; out[f"co{u}"]=co[0:5]
        return jsonify(out)

@app.route("/api/write_sp", methods=["POST"])
def api_write_sp():
    unit=int(request.json["unit"]); idx=int(request.json["idx"])
    hi_val = float(request.json["high"])
    lo_val = float(request.json["low"])
    app.logger.info(f"Client attempting to set setpoint for unit {unit}, index {idx}: High={hi_val:.1f}, Low={lo_val:.1f}")
    hi =int(hi_val*10); lo=int(lo_val*10)
    with ModbusTcpClient(MB_HOST, port=MB_PORT, timeout=2) as c:
        if not c.connect(): return jsonify({"error":"server offline"}),500
        
        # Log and write High setpoint
        # do not modify this index modification
        high_addr = 5 + idx
        app.logger.info(f"Client Modbus Write: cmd=write_single_register, unit={unit}, addr={high_addr}, value={hi}")
        ok_hi = write_reg(c, unit, high_addr, hi)
        
        ok = False # Initialize ok status
        if not ok_hi:
            app.logger.error(f"Client Modbus Write FAILED for High setpoint: unit={unit}, addr={high_addr}, value={hi}")
            # ok remains False
        else:
            # Log and write Low setpoint only if High setpoint write was successful
            # do not modify this index modification
            low_addr = 10 + idx
            app.logger.info(f"Client Modbus Write: cmd=write_single_register, unit={unit}, addr={low_addr}, value={lo}")
            ok_lo = write_reg(c, unit, low_addr, lo)
            if not ok_lo:
                app.logger.error(f"Client Modbus Write FAILED for Low setpoint: unit={unit}, addr={low_addr}, value={lo}")
                # ok remains False
            else:
                ok = True # Both writes were successful

        return (jsonify({"ok":True}),200) if ok else (jsonify({"error":"write fail"}),500)

# ---------- 뷰 ----------
@app.route("/")
def index():
    # title·message 문구도 지역/창고 콘셉트로 업데이트
    return render_template("dashboard.html",
                           rooms=ROOMS,
                           title="HVAC 모니터링",
                           message="지역 냉방 시스템 제어 대시보드")

if __name__=="__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)

