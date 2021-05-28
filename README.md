VMM-WebRTC-Doorbell-lab
=======================

The goal of this lab is to develop a video doorbell with WebRTC and Python (aiortc) on a Raspberry Pi.

You will need:

* A [Raspberry Pi](https://www.raspberrypi.org/products/raspberry-pi-4-model-b/) with Wifi and storage card 
* A supported Webcam such as the [Logitech C505e](https://www.logitech.com/en-ch/products/webcams/c505e-business-webcam.html)
* A (virtual) machine to run the signaling server on
* Breadboard, jumper wires, a push button and 1kOhm resistor (see [here](https://raspberrypihq.com/use-a-push-button-with-raspberry-pi-gpio/))

For the initial installation of the Raspberry Pi you will need a monitor, keyboard and mouse.

Description
===========

The system to develop should work as follows:

* When the push button is pressed, the aiortc WebRTC implementation starts a video call with the signaling server.
* Ideally, a user should receive a message (SMS, Telegram, ...) with the link to the video call.
* Using the URL the user can connect to the video call with a browser.
* The user can talk with the visitor and quit the call at the end.

Instructions
============

Install the Raspberry Pi
------------------------

See [here](https://www.raspberrypi.org/software/) for installation instructions. You will need a monitor, keyboard and mouse as well as probably a micro-HDMI adapter (for the RPi 4 model).

Change the [user password](https://www.raspberrypi.org/documentation/configuration/security.md) and enable [SSH](https://www.raspberrypi.org/documentation/remote-access/ssh/).

Then you can connect to the RPi through SSH without the need for a monitor, keyboard or mouse.

Deploying the signaling server
------------------------------

You can reuse the signaling server developed in the [VMM-WebRTC-lab](https://github.com/jehrensb/VMM-WebRTC-lab), without any modifications. Just deploy it on a (virtual) machine that is accessible from the Raspberry Pi. You also have to install the required packages:

```bash
sudo apt install python3-flask python3-flask-socketio
```

SocketIO has different protocol version, which may be incompatible. Therefore you have to check the installed version:
```bash
$ apt search socketio
Sorting... Done
Full Text Search... Done
python3-flask-socketio/focal,now 4.2.1-1 all [installed]
  Socket.IO integration for Flask applications

python3-socketio/focal,now 4.4.0-2 all [installed,automatic]
  python3 implementation of the Socket.IO realtime client and server

python3-socketio-client/focal 0.6.5-0.2 all
  socket.io-client library for Python3
```
Here, python3-socketio version 4.4.0-2 is installed. The client on the Raspberry Pi has to use a compatible version.

Development environment
--------------------------

Ideally you will develop the WebRTC client in Python directly on the Raspberry Pi. We recommend using VS Code with a remote SSH connection to the RPi.

Start VS Code on your laptop and create a remote connection to the RPi by clicking on the red icon "Open a Remote Window" all on the bottom left of VS Code.

Developing the WebRTC client
----------------------------

The WebRTC client is a Python 3 program running on the Raspberry Pi. It uses [aiortc](https://aiortc.readthedocs.io/), which is a Python implementation of WebRTC, as well as SocketIO to communicate with the signaling server.

### Install the required Python packages

Install the Python packages `aiortc` and `SocketIO`:

```
python3 -m pip install aiortc
python3 -m pip install "python-socketio[asyncio_client]==4.6.1"
```
Here the SocketIO version is fixed to 4.6.1, which is compatible with the version 4.4.0-2 used by the server.

### Overall structure of the WebRTC client

The overall structure of the WebRTC client is:
```
Loop forever:
  1. Wait until keypress (to be replaced later by the pushbutton press event).
  2. Connect to the signaling server.
  3. Join a conference room with a random name (send 'create' signal with room name).
  4. Wait for response. If response is 'joined' or 'full', stop processing and return to the loop. Go on if response is 'created'.
  5. Send a message (SMS, Telegram, email, ...) to the user with the room name. Or simply start by printing it on the terminal. 
  6. Wait (with timeout) for a 'new_peer' message. If timeout, send 'bye' to signaling server and return to the loop. 
  7. Wait (with timeout) for an 'invite' message. If timemout, send 'bye to signaling server and return to the loop. 
  8. Acquire the media stream from the Webcam.
  9. Create the PeerConnection and add the streams from the local Webcam.
  10. Add the SDP from the 'invite' to the peer connection.
  11. Generate the local session description (answer) and send it as 'ok' to the signaling server.
  12. Wait (with timeout) for a 'bye' message. 
  13. Send a 'bye' message back and clean everything up (peerconnection, media, signaling).
```  

As a starting point, use the [examples provided by aiortc](https://github.com/aiortc/aiortc/tree/main/examples), in particular the apprtc example and the videostream-cli example. You can also try the webcam example, which should work out of the box but is harder to adapt (the server runs on the RPi in this example).

The following sections provide some details for the steps above.

### Connecting to the signaling server

In a first step, you have to develop the signaling between the RPi client on the RPi and the Flask server.
Follow the [SocketIO examples](https://python-socketio.readthedocs.io/en/latest/client.html#creating-a-client-instance) to create a *AsyncClient*. Since the server uses a self-signed certificate, set `ssl_verify=False`, to allow the client to establish the connection.

### Handling messages on the client

Here is one difficulty that you have to overcome: SocketIO is callback oriented, such that a specific callback handler is called for each message type. However, the client has to wait simultaneously for different messages. E.g., after sending a 'create' message, the response may be 'created', 'joined' or 'full'. This is difficult to handle with SocketIO.

Here is how you can implement this behavior:
* aiortc uses the Python asynchoronous library [asyncio](https://docs.python.org/3/library/asyncio.html).
* Write a function that creates a [asyncio Queue](https://docs.python.org/3/library/asyncio-queue.html).
* For each message type ('created, 'joined', ...), the function create a SocketIO message handler. The handler adds the received message to the Queue.
* The main program can then wait for a new message on the queue (`queue.get()`) and handle the message depending on the type.
* If you want to limit the waiting time for a new message, you can wrap the `queue.get()` in an `asyncio.wait_for()` function.

### Media streams on the Raspberry Pi

The Raspberry Pi has to handle several media streams:
* The Webcam (with built-in microphone) generates two streams: a video stream and and audio stream. They have to be transmitted over the peer connection.
* The remote peer sends and audio stream: it has to be send to the audio output (headphone connected to USB or the audio jack.)

**Outgoing streams**
On the Raspberry Pi (Linux), the Webcam device is `/dev/video0`. See the [aiortc Media sources](https://aiortc.readthedocs.io/en/latest/helpers.html#media-sources) for an example. You have to create a MediaPlayer for this stream. Use a small image size (320x240), otherwise the transmission will be very slow.  You have to add the video track of the this MediaPlayer to the peerConnection.

Another MediaPlayer is required for the audio track. The device for this stream is 'default' and the format is 'pulse' (see [aiortc](https://github.com/aiortc/aiortc/issues/213#issuecomment-539047783)). You have to add the audio track of this player to the peerConnection, too.

|              | Source      | Format |
|--------------|-------------|--------|
| Video stream | /dev/video0 | v4l2   |
| Audio stream | default     | pulse  |

**Incoming stream**
You will also have to handle the incoming audio stream. The [aiortc videostream-cli example](https://github.com/aiortc/aiortc/tree/main/examples) uses a MediaRecoder for the incoming stream. The MediaRecorder can write the stream to a file, but also to the audio output. Use 'default' as file name and 'alsa' as format. You should hear the incoming audio stream on the headphones.

### Handling ICE 

Here is the second difficulty that you have to handle.  Aiortc does not yet implement trickle ICE. The RPi client therefore won't generate ICE candidates and won't handle remote ICE candidates correctly. Without trickle ICE, WebRTC has to wait until the ICE agent has gathered all local candidates. It can then include them in the SDP (offer or answer) and send them to the peer.

Therefore you have to do the following:

**In the RPi client**
* Wait until an 'invite' is received (see overall structure above, step 7.)
* Get the SDP from the invite message.
* Use `pc.setRemoteDescription` to register the SDP.
* Use `pc.createAnswer` to generate an answer SDP.
* Use `pc.setLocalDescription(answer)` to register the local SDP.
* **Very important**: then re-read the answer using `pc.localDescription`. Only this SDP will contain the ICE candidates!

**In the Javascript client (webrtcclient.js)**
* When a 'joined' message is received: 
  * use `pc.createOffer` to generate an offer SDP.
  * Use `pc.setLocalDescription`to register the local SDP. This will start the ICE agent.
  * Do *not* yet send and 'invite' message to the remote peer. Just wait.
* When a local `pc.oncicecandidate` event is received:
  * Do *not* send the candidate to the remote peer. Just ignore it.
  * If the candidate is empty, the ICE agent has finished. In this case:
    * Use `pc.localDescription` to get the offer SDP. It should contain the ICE candidates. 
    * Send an 'invite' message to the remote peer with the offer SDP.

The JavaScript client will therefore not use trickle ICE but send all ICE candidates directly in the invite message.

### Connecting the push button

The push button simulates the doorbell button. When the button is pushed, the Raspberry Pi should establish a new video call, with a random string as call ID (room identifier).

Follow the [tutorial](https://raspberrypihq.com/use-a-push-button-with-raspberry-pi-gpio/) to wire up the push button and program the GPIO pins on the Raspberry Pi.

### Informing the user

The Raspberry Pi should inform the user when somebody rings the door. 

Find a way to send a message to the user (SMS, Telegram, email, ...) with the URL to connect to the video call.

Project submission
==================

You have to provide the following elements to the professor:

* A link to the GitHub repository with your final code.
* A short video (maximum 10 minutes) in which you:
  * give a demonstration of your system,
  * explain how you sent a message to the user
  * show how you structured the code of the RPi client and how you implemented the difficult parts.

All students will vote and the best project will get an additional 0.5 on the grade.
