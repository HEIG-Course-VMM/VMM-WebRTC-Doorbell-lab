import socketio
import random
import string 
import asyncio
from aiortc.contrib.media import MediaPlayer
from aiortc import RTCPeerConnection,RTCSessionDescription

#*****************************
# GLOBAL VARIABLES
#*****************************
SERVER_URL = "https://192.168.1.115:443"
ROOM_NAME_SIZE = 8
TIMEOUT=30
VIDEO_SIZE = "320x240"

#*****************************
# FUNCTIONS
#*****************************
def getRandomName(length):
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))

def receiver_queue(signaling, messages):
    queue = asyncio.Queue()
    for signal in messages:
        signaling.on(signal, lambda content, signal=signal: queue.put_nowait((signal, content)))
    return queue

async def main():
    while True:
        sio = socketio.AsyncClient(ssl_verify=False)
        messages = ["created", "joined", "full", "new_peer", "invite", "ok", "ice_candidate", "bye"]
        messagesQueue = receiver_queue(sio, messages)
        
        #Wait until keypress (to be replaced later by the pushbutton press event)
        input("Press enter to continue")
        print("Connecting...")
        
        #Connect to the signaling server.
        await sio.connect(SERVER_URL)
        print("Connected")
        
        #Join a conference room with a random name (send 'create' signal with room name).
        roomName = getRandomName(ROOM_NAME_SIZE)
        await sio.emit("join", roomName)
        print("create room : " + roomName)
        
        #Wait for response. If response is 'joined' or 'full', stop processing and return to the loop. Go on if response is 'created'.
        response = await messagesQueue.get()
        responseMessage = response[0]
        
        print(responseMessage)
        
        if responseMessage == "full" or responseMessage == "joined":
            continue
        
        #Send a message (SMS, Telegram, email, ...) to the user with the room name. Or simply start by printing it on the terminal. 
        print("Dring dring : " + SERVER_URL + "?id=" + roomName)

        videoPlayer = None
        audioPlayer = None

        #Wait (with timeout) for a 'new_peer' message. If timeout, send 'bye' to signaling server and return to the loop.        
        try:
            response = await asyncio.wait_for(messagesQueue.get(), timeout=TIMEOUT)
            responseMessage = response[0]
            if responseMessage == "new_peer":
                print("new_peer")
        except asyncio.TimeoutError:
            print("Timeout 'new_peer' after " + str(TIMEOUT) + " s")
            await sio.emit("bye", roomName)
            
        #Wait (with timeout) for an 'invite' message. If timemout, send 'bye to signaling server and return to the loop.  
        try:
            response = await asyncio.wait_for(messagesQueue.get(), timeout=TIMEOUT)
            responseMessage = response[0]
            if responseMessage == "invite":
                print("invite")
                #Acquire the media stream from the Webcam.
                videoPlayer = MediaPlayer("/dev/video0", format="v4l2", options={"video_size": VIDEO_SIZE})
                audioPlayer = MediaPlayer("default", format="pulse")  
                #Create the PeerConnection and add the streams from the local Webcam.
                pc = RTCPeerConnection()
                
                #Add the SDP from the 'invite' to the peer connection.
                offer = response[1]
                sdp = RTCSessionDescription(offer['sdp'], offer['type'])
                await pc.setRemoteDescription(sdp)
                #Generate the local session description (answer) and send it as 'ok' to the signaling server.
                
        except asyncio.TimeoutError:
            print("Timeout 'invite' after " + str(TIMEOUT) + " s")
            await sio.emit("bye", roomName)
            continue
        
        #Wait (with timeout) for a 'bye' message.
        try:
            response = await asyncio.wait_for(messagesQueue.get(), timeout=TIMEOUT)
            responseMessage = response[0]
            if responseMessage == "bye":
                print("bye")
                #Send a 'bye' message back and clean everything up (peerconnection, media, signaling).
                await sio.emit("bye")
                del videoPlayer
                del audioPlayer
        except asyncio.TimeoutError:
            print("Timeout bye " + str(TIMEOUT) + " s")
            await sio.emit("bye", roomName)                
            continue
        
#*****************************
# MAIN PROGRAM
#*****************************
asyncio.run(main())
