import asyncio
import json
import ssl
import secrets

import socketio
import pprint

import env

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

async def main(server):
    input("Press Enter to continue...")

    await sio.connect(server)
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

            remoteOffer = RTCSessionDescription(sdp=message[1]['sdp'],type=message[1]['type']) 
            pc = RTCPeerConnection()
            
            await pc.setRemoteDescription(remoteOffer)
            print("remote description set")
            
            # Aquire the media device
            video_player = MediaPlayer('/dev/video0', format='v4l2', options=options_video)
            audio_player = MediaPlayer("default", format="pulse")  
            print("Media aquired")

            for t in pc.getTransceivers():
                print(t.kind)
                if t.kind == "audio" and video_player.video:
                    pc.addTrack(video_player.video)
                if t.kind == "video" and audio_player.audio:
                    pc.addTrack(audio_player.audio)

            print("track added")

            print("generating answer...")
            answer = await pc.createAnswer()

            print("generated answer")

            await pc.setLocalDescription(answer)

            answer = pc.localDescription
            print(answer)

            answer_json = json.dumps({
                "sdp":answer.sdp,
                "type":answer.type
            })

            await sio.emit("ok",answer_json)
        
        
        if message[0] == "bye" :
            print("End of the call")
            await sio.emit("bye")
            
            # Cleanup
            pc.close()
            video_player = None
            video_player = None
            
            

if __name__ == "__main__" :
    server = env.HOST + ":" + str(env.PORT)
    try :
        asyncio.run(main(server))
    except KeyboardInterrupt :
        pc.close()