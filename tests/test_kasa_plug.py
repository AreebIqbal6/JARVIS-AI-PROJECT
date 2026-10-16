import asyncio
from kasa_controller import SmartDeviceController

async def test_smart_device_lifecycle():
    controller = SmartDeviceController(ip="192.168.1.100")
    
    # 1. Initial Status
    status = await controller.get_status()
    assert status["ok"] is True
    assert "energy" in status["data"]
    assert "current_watts" in status["data"]["energy"]
    assert "today_kwh" in status["data"]["energy"]

    # 2. Turn ON
    on_res = await controller.turn_on()
    assert on_res["ok"] is True
    assert on_res["data"]["state"] == "on"

    status_after_on = await controller.get_status()
    assert status_after_on["data"]["is_on"] is True
    assert status_after_on["data"]["energy"]["current_watts"] > 0

    # 3. Turn OFF
    off_res = await controller.turn_off()
    assert off_res["ok"] is True
    assert off_res["data"]["state"] == "off"

    status_after_off = await controller.get_status()
    assert status_after_off["data"]["is_on"] is False

    # 4. Toggle
    toggle_res = await controller.toggle()
    assert toggle_res["ok"] is True
    assert toggle_res["data"]["state"] == "on"

    # 5. Brightness adjustment
    bright_res = await controller.set_brightness(45)
    assert bright_res["ok"] is True
    assert bright_res["data"]["brightness"] == 45

    # 6. Color HSV
    color_res = await controller.set_color_hsv(180, 80, 90)
    assert color_res["ok"] is True

    # 7. Subnet Discovery
    devices = await controller.discover_devices(timeout_sec=0.5)
    assert isinstance(devices, list)
    assert len(devices) > 0
