import asyncio
import json
import ssl
import secrets

import socketio

from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer, MediaRelay


# Loop forever:
#   1. Wait until keypress (to be replaced later by the pushbutton press event).
#   2. Connect to the signaling server.
#   3. Join a conference room with a random name (send 'join' signal with room name).
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


options_video = {"framerate": "30", "video_size": "320x240"}

sio = socketio.AsyncClient(ssl_verify=False)

MAX_RND = 512

# Reception des messages asynchrones
def receiver_queue(signaling, messages):
    queue = asyncio.Queue()
    for signal in messages:
        signaling.on(signal, lambda content, signal=signal: queue.put_nowait((signal, content)))
    return queue

async def main():
    input("Press Enter to continue...")

    await sio.connect('https://localhost:443')
    print("connected to my server")
    print("sending test message")

    room_name = "room_pi{}".format(secrets.randbelow(MAX_RND))

    queue = receiver_queue(sio, messages=["joined", "created", "full", "invite", "ice_candidate", "bye", "new_peer"])
    
    await sio.emit('join',room_name)

    while True :
        print("get signal from queue")
        message = await queue.get() 
        
        print(message)
        
        if message[0] == "created" :
            print(f"room {message[1]} has been created")

        if message[0] in ("full", "joined") : 
            print("error : room already exist")

        if message[0] == "new_peer" : 
            print("a new peer has entered the room")

        if message[0] == "invite" : 
            print("received an invite")

            remoteOffer = message[1]
            pc = RTCPeerConnection()
            
            # Aquire the media device

            video_player = MediaPlayer('/dev/video0', format='v4l2', options=options_video)
            audio_player = MediaPlayer("default", format="pulse")  

            pc.addTrack(video_player)
            pc.addTrack(audio_player)

            pc.setRemoteDescription(remoteOffer)
            answer = await pc.createAnswer()

            pc.setLocalDescription(answer)
            answer = pc.localDescription

            await sio.emit("ok",answer)
        
        if message[0] == "bye" :
            print("End of the call")
            await sio.emit("bye")
            

if __name__ == "__main__" :
    asyncio.run(main())