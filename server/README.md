# Server

Use SocketIO signaling server from the [VMM-WebRTC-lab](https://github.com/tiffanybonzon/VMM-WebRTC-lab).

The socketio version used is `5.3.0-1`

The static files have been modified

- `index.html`
  - Changed some titles
  - Removed datachannel area
  - Only display incoming stream
- `webrtcclient.js`
  - Removed some functions (sending invite, datachannel creation, ...)
  - SDP answer is only sent once all ICE Candidates have been discovered

## Generating certificates

Generate a self-signed SSL certificate using OpenSSL with the following command:

```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 --nodes
```

## Launching the server

```bash
sudo python3 app.py
```
