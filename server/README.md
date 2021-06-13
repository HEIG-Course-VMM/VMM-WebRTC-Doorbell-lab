Use SocketIO signaling server from the [VMM-WebRTC-lab](https://github.com/jehrensb/VMM-WebRTC-lab).

The socketio version used is `5.3.0-1`

Generate a self-signed SSL certificate using OpenSSL with the following command:

```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 --nodes
```

Launch the server with the following command:

```bash
sudo python3 app.py
```

