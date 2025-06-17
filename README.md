# pymodbus-test2

This project is based on MODBUS_PLC_Python_SCADA_Simulator.

Tested with Python 3.10 and pymodbus 3.9.2.

Please note: Due to an apparent indexing issue observed in pymodbus 3.9.2 (possibly a library-side bug), this implementation includes workarounds to handle or mitigate the behavior accordingly.

##  Key Files 
hvac_server.py: Very Simple Simulator + Modbus Slave(Server) 

hvac_client.py: Very Simple Weberver(Flask) + Modbus Master(Client)

read_hvac_server.py: CLI + Modbus Master(Client) 

dashboard.html : HTML Structure. 

## Results

![Flask Server Web Page](image.png)
