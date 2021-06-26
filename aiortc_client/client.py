import asyncio
import json
import ssl
import secrets

import socketio
import pprint

from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer, MediaRelay

options_video = {"framerate": "30", "video_size": "640x480"}

sio = socketio.AsyncClient(ssl_verify=False)

MAX_RND = 512

HOST = 'https://192.168.1.108'
PORT = 443

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
            print(f"Browse your navigator to {server}?room={message[1]} ")

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
            await pc.close()
            video_player = None
            video_player = None
            break 
            

if __name__ == "__main__" :
    server = HOST + ":" + str(PORT)
    
    asyncio.run(main(server))