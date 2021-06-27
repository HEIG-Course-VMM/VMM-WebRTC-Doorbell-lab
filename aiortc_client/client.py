import socketio
import asyncio
import asyncio
import random
from aiortc.contrib.media import MediaPlayer
from aiortc import RTCPeerConnection,RTCSessionDescription

''''
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
'''

sio = socketio.AsyncClient(ssl_verify=False)
messages = ["joined","full", "created", "new_peer", "invite", "ok", "bye"]
SERVER = "https://192.168.0.27:443"

def receiver_queue(signaling, messages):
    
    queue = asyncio.Queue()
    for signal in messages:
        signaling.on(signal, lambda content, signal=signal: queue.put_nowait((signal, content)))
    return queue

async def clean_up():
    await sio.emit("bye")
    await sio.disconnect()

async def main():
    while True:
        
        #1. Wait until keypress (to be replaced later by the pushbutton press event).
        input("Please, press enter to continue...")

        #2. Connect to the signaling server.
        await sio.connect(SERVER)
        #crlation de la queue APRES avoir connection SIO
        queue = receiver_queue(sio, messages)
        print("Connected")
        #3. Join a conference room with a random name (send 'create' signal with room name).
        room_name = str(random.choice(range(1, 1000)))
        #vraiment create ? Modifier programme
        await sio.emit("join", room_name)
        #4. Wait for response. If response is 'joined' or 'full', stop processing and return to the loop. Go on if response is 'created'.
        response = await queue.get()

        #check if response is joined of full -> stop process
        #pourquoi [0] ? 
        if response[0] == "joined" or response[0] == "full":
            print("joined or full! ")
            continue
        

        #5. Send a message (SMS, Telegram, email, ...) to the user with the room name. Or simply start by printing it on the terminal. 
        print("Room " + room_name + " created ! ")

        #6. Wait (with timeout) for a 'new_peer' message. If timeout, send 'bye' to signaling server and return to the loop. 
        #If you want to limit the waiting time for a new message, you can wrap the queue.get() in an asyncio.wait_for() function.
        #https://stackoverflow.com/questions/45220783/purpose-of-asyncio-wait-for/45224153
        #time in sec  
        try: 
            response = await asyncio.wait_for(queue.get(), 30)
            if response[0] == "new_peer":
                print("new peer")
            else:
                raise Exception
        
        except (asyncio.TimeoutError, Exception):
            print("timeout")
            clean_up()
            continue

        #7. Wait (with timeout) for an 'invite' message. If timemout, send 'bye to signaling server and return to the loop. 
        try: 
            response = await asyncio.wait_for(queue.get(), 15)
            if response[0] == "invite" :
                print("Invite")
            else:
                raise Exception

        except (asyncio.TimeoutError, Exception):
            print("timeout")
            clean_up()

            continue
            
        #8. Acquire the media stream from the Webcam.
        # Open webcam on Linux.
        video = MediaPlayer('/dev/video0', format='v4l2', options={'video_size': '320x240'})
        audio = MediaPlayer("default", format="pulse")  

        #9. Create the PeerConnection and add the streams from the local Webcam.
        pc = RTCPeerConnection()
        pc.addTrack(video.video)
        pc.addTrack(audio.audio)

        #10. Add the SDP from the 'invite' to the peer connection.
        sdp = RTCSessionDescription(response[1]['sdp'], response[1]['type'])
        await pc.setRemoteDescription(sdp)
        answer = await pc.createAnswer()
        #  11. Generate the local session description (answer) and send it as 'ok' to the signaling server.
        await pc.setLocalDescription(answer)
        answer = pc.localDescription #pas asynchrone !
        await sio.emit("ok",answer)
        
        #12. Wait (with timeout) for a 'bye' message.
        try: 
            response = await asyncio.wait_for(queue.get(), 5)
            
            if response[0] == "bye" :
                print("Bye")
            else:
                raise responseError
        except (asyncio.TimeoutError, responseError):
            print("no bye before timeout")

        #13. Send a 'bye' message back and clean everything up (peerconnection, media, signaling).
        del video
        del audio
        clean_up()
        pc.close()

asyncio.run(main())