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

Python lib for TG bot
```bash
python3 -m pip install python-telegram-bot
```

Env vars file
```bash
python3 -m pip install python-dotenv
```

Follow this tuto for the LED
https://raspberrypihq.com/making-a-led-blink-using-the-raspberry-pi-and-python/

Launching the client

```bash
python3 apprtc.py
```


## Créer Bot Telegram
Envoyer un /start à @BotFather
puis /newbot
Répondre aux questions (Name et userneme du bot)
Après un token est donné, il faut le copier dans le fichier .env (TOKEN)

### Récup. le chatID du chat avec le bot
Envoyer n'importe quel message a votre nouveau bot
aller à https://api.telegram.org/bot<TOKEN>/getUpdates en remplacant <TOKEN> par le token donné par @BotFather
Il y aura une sortie similaire
```json
{"ok":true,"result":[{"update_id":24xxxxxxx,
"message":{"message_id":3,"from":{"id":426650819,"is_bot":false,"first_name":"Tiffany","last_name":"Bonzon","username":REDACTED,"language_code":"en"},"chat":{"id":42xxxxxx,"first_name":"Tiffany","last_name":"Bonzon","username":REDACTED,"type":"private"},"date":1623840757,"text":"/start","entities":[{"offset":0,"length":6,"type":"bot_command"}]}}]}
```
il faut prendre le champ `id` (ici 42xxxxxx) et mettre cet ID dans le fichier .env (CHATID)





