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
    VideoStreamTrack
)
from aiortc.contrib.media import MediaPlayer
from aiortc.contrib.signaling import BYE, add_signaling_arguments, create_signaling

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
sio = socketio.AsyncClient(ssl_verify=False,logger=True, engineio_logger=True)

messages = ["created", "joined", "full", "new_peer", "ok"]

def blink_led(times):
    for _ in range(times):
        GPIO.output(8, GPIO.HIGH)
        sleep(0.3)                  
        GPIO.output(8, GPIO.LOW)  
        sleep(0.3)

async def cleanup_restart(room_name):
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
    '''
    @sio.event
    async def created(data):
        queue.put_nowait('created')

    @sio.event
    async def joined(data):
        queue.put_nowait('joined')

    @sio.event
    async def full(data):
        queue.put_nowait('full')

    @sio.event
    async def new_peer():
        queue.put_nowait('new_peer')

    @sio.event
    async def ok(data):
        queue.put_nowait(('ok', data))
    '''


    while True:
        #queue = asyncio.Queue() # Create a queue that we will use to store the server responses.
        queue = receiver_queue(sio, messages)
        #1. Wait until pushbutton press event.
        print('press button...')
        GPIO.wait_for_edge(10, GPIO.RISING)

        #2. Connect to the signaling server.
        await sio.connect(SERV_URL)

        #3. Join a conference room with a random name (send 'create' signal with room name).
        room_name = ''.join(random.SystemRandom().choice(string.ascii_letters) for _ in range(10))

        while not sio.connected:
            pass
            
        await sio.emit('join', room_name)


        #4. Wait for response. If response is 'joined' or 'full', stop processing and return to the loop. Go on if response is 'created'.
        answer = await queue.get()
        print(answer[0])
        if answer[0] == 'full' or answer[0] == 'joined':
            print('wrong answer')
            await cleanup_restart(room_name)
            continue
        
        print('room created')
        #5. Send a message (SMS, Telegram, email, ...) to the user with the room name. Or simply start by printing it on the terminal.
        message = "Someone just rang your doorbell! Go check who it is at " + SERV_URL + " in the room " + room_name
        print(message)
        #bot.sendMessage(CHATID, message)
        #6. Wait (with timeout) for a 'new_peer' message. If timeout, send 'bye' to signaling server and return to the loop.
        
        try:
            answer = await asyncio.wait_for(queue.get(), timeout=TIMEOUT)
            if answer[0] != 'new_peer':
                raise Exception
        except (asyncio.TimeoutError, Exception):
                print('peer failed to connect on time')
                await cleanup_restart(room_name)
                continue
            

        

        #8. Acquire the media stream from the Webcam.
        video_player = MediaPlayer('/dev/video0', format='v4l2', options={
            'video_size': '320x240'
        })
        audio_player = MediaPlayer("default", format="pulse")

        #9. Create the PeerConnection and add the streams from the local Webcam.
        #11. Generate the local session description (offer) and send it as 'invite' to the signaling server.
        pc = RTCPeerConnection()
        pc.addTrack(video_player.video)
        pc.addTrack(audio_player.audio)

        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        print("offer", offer)

        sdp_offer = {"type": offer.type, "sdp": offer.sdp}
        await sio.emit('invite', sdp_offer)

        #10. Add the SDP from the 'ok' to the peer connection.
        answer = await queue.get()
        if answer[0] != 'ok':
            print("peer didn't send SDP answer")
            cleanup_restart(room_name)

        sdp_answer = RTCSessionDescription(answer[1]['sdp'], answer[1]['type'])
        await pc.setRemoteDescription(sdp_answer)

        #12. Wait (with timeout) for a 'bye' message.    
        #13. Send a 'bye' message back and clean everything up (peerconnection, media, signaling).
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
    
