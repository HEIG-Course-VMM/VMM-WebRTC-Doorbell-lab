import socketio
import asyncio
from aiortc import (
    RTCPeerConnection, 
    RTCSessionDescription,
    RTCIceServer,
    RTCConfiguration
)
from aiortc.contrib.media import MediaPlayer, MediaRecorder
import time
import random
import logging

import RPi.GPIO as GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(10, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

URL_SERVER = 'https://192.168.50.212:443'
VIDEO_SIZE = '320x240'
TIMEOUT = 30
ICESERVER = RTCIceServer(urls='stun:stun.l.google.com:19302')

signals = ["created", "joined", "full", "new_peer", "invite", "bye"]
pc_signal = ["track"]
sio = socketio.AsyncClient(ssl_verify=False)

def receiver_queue(signaling, messages):
    queue = asyncio.Queue()
    for signal in messages:
        signaling.on(signal, lambda content='', signal=signal: queue.put_nowait((signal, content)))
    return queue

async def stop_client(room_name):
    await sio.emit('bye', room_name)
    time.sleep(1) # Used to not get connection refused by server when restarting the loop
    await sio.disconnect()
    await sio.wait()

async def main():
    while True:
        queue = receiver_queue(sio, signals)

        #1. Wait until keypress (to be replaced later by the pushbutton press event).
        print("Keypress")
        GPIO.wait_for_edge(10, GPIO.RISING)
        #2. Connect to the signaling server.
        await sio.connect(URL_SERVER)
        #3. Join a conference room with a random name (send 'create' signal with room name).
        room_name = "Room" + str(random.randint(1000, 10000))
        await sio.emit('join', room_name)
        #4. Wait for response. If response is 'joined' or 'full', stop processing and return to the loop. Go on if response is 'created'.
        resp = await asyncio.wait_for(queue.get(), None)
        if resp[0] != "created":
            await stop_client(room_name)
        #5. Send a message (SMS, Telegram, email, ...) to the user with the room name. Or simply start by printing it on the terminal. 
        print(room_name)
        #6. Wait (with timeout) for a 'new_peer' message. If timeout, send 'bye' to signaling server and return to the loop. 
        try:
            resp = await asyncio.wait_for(queue.get(), TIMEOUT)
            if(resp[0] != "new_peer"):
                raise Exception
            else:
                print("New peer connected to the room !")
        except (asyncio.TimeoutError, Exception):
            print("No response 'new_peer' from server or bad response. Leaving...")
            await stop_client(room_name)
            continue
        #7. Wait (with timeout) for an 'invite' message. If timemout, send 'bye to signaling server and return to the loop.
        offer = ''
        try:
            resp = await asyncio.wait_for(queue.get(), TIMEOUT)
            if(resp[0] == "invite"):
                print("Invite received from the client !")
                offer = resp[1]
        except:
            print("No invite received from the client. Leaving...")
            await stop_client(room_name)
            continue
        #8. Acquire the media stream from the Webcam.
        video_player = MediaPlayer('/dev/video0', format='v4l2', options={'video_size': VIDEO_SIZE})
        audio_player = MediaPlayer('default', format='pulse')
        #9. Create the PeerConnection and add the streams from the local Webcam.
        pc = RTCPeerConnection(configuration=RTCConfiguration(iceServers=[ICESERVER]))
        queue_PC = receiver_queue(pc, pc_signal)
        pc.addTrack(video_player.video)
        pc.addTrack(audio_player.audio)
        #10. Add the SDP from the 'invite' to the peer connection.
        sdp = RTCSessionDescription(offer['sdp'], offer['type'])
        await pc.setRemoteDescription(sdp)

        try:
            resp = await asyncio.wait_for(queue_PC.get(), TIMEOUT)
            if(resp[0] == "track"):
                recorder = MediaRecorder("default", format="alsa")
                recorder.addTrack(resp[1])
                await recorder.start()
        except asyncio.TimeoutError:
            await recorder.stop()
            del video_player
            del audio_player
            await stop_client(room_name)
            await pc.close()
        #11. Generate the local session description (answer) and send it as 'ok' to the signaling server.
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        answer = pc.localDescription
        sio.emit("ok", answer)
        #12. Wait (with timeout) for a 'bye' message. 
        try:
            resp = await asyncio.wait_for(queue.get(), TIMEOUT*4)
            if(resp[0] == "bye"):
                print("End of the call. Leaving...")
        except asyncio.TimeoutError:
            print("No 'bye' from server. Forcing disconnection...")
        #13. Send a 'bye' message back and clean everything up (peerconnection, media, signaling).
        await recorder.stop()
        del video_player
        del audio_player
        await stop_client(room_name)
        await pc.close()

try:
    asyncio.run(main(), debug=True)
except KeyboardInterrup:
    sys.exit(1)
finally:
    GPIO.cleanup()