import argparse
import asyncio
import json
import logging
import os
import platform
import ssl

import socketio

from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer, MediaRelay


# Loop forever:
#   1. Wait until keypress (to be replaced later by the pushbutton press event).
#   2. Connect to the signaling server.
#   3. Join a conference room with a random name (send 'create' signal with room name).
#   4. Wait for response. If response is 'joined' or 'full', stop processing and return to the loop. Go on if response is 'created'.
#   5. Send a message (SMS, Telegram, email, ...) to the user with the room name. Or simply start by printing it on the terminal. 
#   6. Wait (with timeout) for a 'new_peer' message. If timeout, send 'bye' to signaling server and return to the loop. 
#   7. Wait (with timeout) for an 'invite' message. If timemout, send 'bye to signaling server and return to the loop. 
#   8. Acquire the media stream from the Webcam.
#   9. Create the PeerConnection and add the streams from the local Webcam.
#   10. Add the SDP from the 'invite' to the peer connection.
#   11. Generate the local session description (answer) and send it as 'ok' to the signaling server.
#   12. Wait (with timeout) for a 'bye' message. 
#   13. Send a 'bye' message back and clean everything up (peerconnection, media, signaling).


options = {"framerate": "30", "video_size": "640x480"}

if __name__ == "__main__" :
    input("Press Enter to continue...")
    sio = socketio.Client(ssl_verify=False)
    sio.connect('https://localhost:443')
    sio.emit('test','aaa')
    print('my sid is', sio.sid)
    # create Peerconnection