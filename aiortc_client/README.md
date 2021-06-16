Develop aiortc client to run on the Raspberry Pi here.

The Raspberry Pi has to use a socketio client version that is compatible with the [server](https://github.com/tiffanybonzon/VMM-WebRTC-Doorbell-lab/tree/master/server)

```bash
python3 -m pip install aiortc
python3 -m pip install "python-socketio[asyncio_client]==5.3.0"
```

Install the necessary Python libraries for the push button
```bash
sudo apt-get install python-rpi.gpio python3-rpi.gpio
```

Follow this tuto for the LED
https://raspberrypihq.com/making-a-led-blink-using-the-raspberry-pi-and-python/

Launching the client

```bash
python3 apprtc.py
```





