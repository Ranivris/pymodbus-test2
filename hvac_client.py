from flask import Flask, jsonify, request, render_template
from pymodbus.client import ModbusTcpClient

MB_HOST, MB_PORT = "127.0.0.1", 5020
ROOMS = [
    "창고 101","창고 102","창고 103","창고 104","창고 105",
    "창고 201","창고 202","창고 203","창고 204","창고 205"
]
SCALE = 0.1

app = Flask(__name__, template_folder="templates")  # templates/dashboard.html

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
    hi =int(float(request.json["high"])*10); lo=int(float(request.json["low"])*10)
    with ModbusTcpClient(MB_HOST, port=MB_PORT, timeout=2) as c:
        if not c.connect(): return jsonify({"error":"server offline"}),500
        ok=write_reg(c,unit,6+idx,hi) and write_reg(c,unit,11+idx,lo)
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
