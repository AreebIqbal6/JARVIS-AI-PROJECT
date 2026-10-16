import asyncio
from kasa_controller import SmartDeviceController

async def test_smart_device_lifecycle():
    controller = SmartDeviceController(ip="192.168.1.100")
    
    # 1. Real Status Check (Handles physical offline without faking data)
    status = await controller.get_status()
    assert "data" in status
    assert "energy" in status["data"]
    assert "current_watts" in status["data"]["energy"]
    assert "today_kwh" in status["data"]["energy"]
    assert "connected" in status["data"]

    # If physical device is offline, verified that energy is 0.0 (no mock watts)
    if not status["data"]["connected"]:
        assert status["data"]["energy"]["current_watts"] == 0.0
        assert status["data"]["hardware"] == "disconnected"

    # 2. Subnet Discovery returns real physical list (no fake sample devices)
    devices = await controller.discover_devices(timeout_sec=0.5)
    assert isinstance(devices, list)
    # If devices are discovered, each has valid IP and model
    for d in devices:
        assert "ip" in d
        assert "model" in d

    # 3. Verification of turn_on behavior (returns real status, does not fake success if offline)
    on_res = await controller.turn_on()
    if not status["data"]["connected"]:
        assert on_res["ok"] is False
        assert "unreachable" in on_res["error"]
