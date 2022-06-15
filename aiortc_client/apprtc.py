import socketio
import asyncio
import os
import random
import string
import telegram
import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
import json

from time import sleep
from dotenv import load_dotenv
from aiortc import (
    RTCPeerConnection, 
    RTCSessionDescription, 
    VideoStreamTrack,
    RTCIceServer,
    RTCConfiguration
)
from aiortc.contrib.media import MediaPlayer, MediaRecorder

#dotenv
load_dotenv()
SERV_URL = os.getenv('SERV_URL')
LED = os.getenv('LED')
TIMEOUT = float(os.getenv('TIMEOUT'))
TOKEN = os.getenv('TOKEN')
CHATID = os.getenv('CHATID')

#Telegram
bot = telegram.Bot(token=TOKEN)

# asyncio
sio = socketio.AsyncClient(ssl_verify=False,logger=False, engineio_logger=False)
sio_messages = ["created", "joined", "full", "new_peer", "ok", "bye"]

#peerConnection
ice_server = RTCIceServer(urls='stun:stun.l.google.com:19302')
pc_messages = ["track"]

def blink_led(times):
    for _ in range(times):
        GPIO.output(8, GPIO.HIGH)
        sleep(0.3)                  
        GPIO.output(8, GPIO.LOW)  
        sleep(0.3)

async def cleanup_restart(room_name):
    print("Restarting...")
    if LED:
        blink_led(3)
    await sio.emit('bye', room_name)
    await asyncio.sleep(1) #Needed for server to receive bye message apparently...
    await sio.disconnect()
    await sio.wait()

def receiver_queue(signaling, messages):
    queue = asyncio.Queue()
    for signal in messages:
        signaling.on(signal, lambda content='', signal=signal: queue.put_nowait((signal, content)))
    return queue

async def run():
    while True:
        queue = receiver_queue(sio, sio_messages)

        #1. Wait until pushbutton press event.
        print('Press button...')
        GPIO.wait_for_edge(10, GPIO.RISING)

        #2. Connect to the signaling server.
        await sio.connect(SERV_URL)

        #3. Join a conference room with a random name (send 'join' signal with room name).
        room_name = ''.join(random.SystemRandom().choice(string.ascii_letters) for _ in range(10))

        while not sio.connected:
            pass
            
        await sio.emit('join', room_name)

        #4. Wait for response. If response is 'joined' or 'full', stop processing and return to the loop. Go on if response is 'created'.
        answer = await queue.get()
        if answer[0] == 'full' or answer[0] == 'joined':
            print('Room already exists')
            await cleanup_restart(room_name)
            continue
        
        #5. Send a Telegram message to the user with the room name. Or simply start by printing it on the terminal.
        message = "Someone just rang your doorbell! Go check who it is at " + SERV_URL + " in the room " + room_name
        print(message)
        bot.sendMessage(CHATID, message)

        #6. Wait (with timeout) for a 'new_peer' message. If timeout, send 'bye' to signaling server and return to the loop.
        try:
            answer = await asyncio.wait_for(queue.get(), timeout=TIMEOUT)
            if answer[0] != 'new_peer':
                raise Exception
        except (asyncio.TimeoutError, Exception):
                print('Peer failed to connect on time')
                await cleanup_restart(room_name)
                continue

        #8. Acquire the media stream from the Webcam.
        video_player = MediaPlayer('/dev/video0', format='v4l2', options={
            'video_size': '160x120'
        })
        audio_player = MediaPlayer("default", format="pulse")

        #9. Create the PeerConnection and add the streams from the local Webcam.
        pc = RTCPeerConnection(configuration=RTCConfiguration(iceServers=[ice_server]))
        pc.addTrack(video_player.video)
        pc.addTrack(audio_player.audio)
        pc_queue = receiver_queue(pc, pc_messages)

        #10. Generate the local session description (offer) and send it as 'invite' to the signaling server.
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)

        while pc.iceGatheringState != 'complete':
            pass
        
        sdp_offer = {"type": pc.localDescription.type, "sdp": pc.localDescription.sdp}
        await sio.emit('invite', sdp_offer)

        #11. Add the SDP from the 'ok' to the peer connection.
        try:
            answer = await asyncio.wait_for(queue.get(), timeout=TIMEOUT)
            if answer[0] != 'ok':
                raise Exception
        except (asyncio.TimeoutError, Exception):
                print("peer didn't send SDP answer")
                await cleanup_restart(room_name)
                continue

        sdp_answer = RTCSessionDescription(answer[1]['sdp'], answer[1]['type'])
        await pc.setRemoteDescription(sdp_answer)

        #12. Get the media from the browser and play it on the RPI
        try:
            track = await asyncio.wait_for(pc_queue.get(), timeout=TIMEOUT)
            if track[0] == "track":
                recorder = MediaRecorder("default", format="alsa")
                recorder.addTrack(track[1])
                await recorder.start()
        except asyncio.TimeoutError:
            pass

        #12. Wait (with timeout) for a 'bye' message.
        try:
            answer = await asyncio.wait_for(queue.get(), timeout=1*60)
            if answer[0] != 'bye':
                raise Exception
        except (asyncio.TimeoutError, Exception):
                print('No bye received from browser, closing connection...')

        #13. Send a 'bye' message back and clean everything up (peerconnection, media, signaling).
        await pc.close()
        video_player = None
        audio_player = None
        await recorder.stop()
        await cleanup_restart(room_name)
    

if __name__ == "__main__":  
    GPIO.setwarnings(False) # Ignore warning for now
    GPIO.setmode(GPIO.BOARD) # Use physical pin numbering
    GPIO.setup(10, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 10 to be an input pin and set initial value to be pulled low (off)
    if LED:
        GPIO.setup(8, GPIO.OUT, initial=GPIO.LOW)   # Set pin 8 to be an output pin and set initial value to low (off)
         

    # run event loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run())
    except KeyboardInterrupt:
        print("Ctrl+C pressed...")
        sys.exit(1)
    finally:
        GPIO.cleanup() # Clean up
        loop.run_until_complete(sio.disconnect())
    
