# Client

Develop aiortc client to run on the Raspberry Pi here.

The clients acts a bit differently than what is described in the main [README](https://github.com/tiffanybonzon/VMM-WebRTC-Doorbell-lab/blob/master/README.md) file.

Here the client acts as the Caller. It creates the room and sends the SDP invite message to the browser.

## Installing libraries

The Raspberry Pi has to use a socketio client version that is compatible with the [server](https://github.com/tiffanybonzon/VMM-WebRTC-Doorbell-lab/tree/master/server).

The server uses socketio version `5.3.0-1`

```bash
python3 -m pip install aiortc
python3 -m pip install "python-socketio[asyncio_client]==5.3.0"
python3 -m pip install python-telegram-bot #telegram bot
python3 -m pip install python-dotenv #env vars file
sudo apt-get install python-rpi.gpio python3-rpi.gpio #push button + LED
```

## Connecting the LED

If you don't have a LED available, simply put `False` for the LED variable in the [.env](https://github.com/tiffanybonzon/VMM-WebRTC-Doorbell-lab/blob/master/aiortc_client/.env) file

The LED indicates when the main loop restarts by blinking 3 times.

Follow the [tutorial](https://raspberrypihq.com/making-a-led-blink-using-the-raspberry-pi-and-python/) to wire up the LED and program the GPIO pins on the Raspberry Pi.

## Create a Telegram Bot

- Start by sending a `/start` to @BotFather
- Create a new bot with the command `/newbot`
- Then follow the instructions (defining a name and username for your bot)
- Once this is done, BotFather will give you a `token` that has to be put into the [.env](https://github.com/tiffanybonzon/VMM-WebRTC-Doorbell-lab/blob/master/aiortc_client/.env) file

### Get the ChatID

You still need to get the ID of the chat between you and your bot.

- Start by sending any messages to your bot
- Then go to `https://api.telegram.org/bot<TOKEN>/getUpdates`, replacing `<TOKEN>` by the token previously given by BotFather
- You should get an output similar to the following one

```json
{"ok":true,"result":[{"update_id":24xxxxxxx,
"message":{"message_id":3,"from":{"id":42xxxxxx,"is_bot":false,"first_name":"Tiffany","last_name":"Bonzon","username":REDACTED,"language_code":"en"},"chat":{"id":42xxxxxx,"first_name":"Tiffany","last_name":"Bonzon","username":REDACTED,"type":"private"},"date":1623840757,"text":"/start","entities":[{"offset":0,"length":6,"type":"bot_command"}]}}]}
```

- Take the `id` field (here 42xxxxxx), and put it into the [.env](https://github.com/tiffanybonzon/VMM-WebRTC-Doorbell-lab/blob/master/aiortc_client/.env) file

## Launching the client

```bash
python3 apprtc.py
```
