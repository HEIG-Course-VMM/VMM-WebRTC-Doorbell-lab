import socketio
import random
import string 
import asyncio

#*****************************
# GLOBAL VARIABLES
#*****************************
SERVER_URL = "192.168.1.115:443"
ROOM_NAME_SIZE = 8

#*****************************
# FUNCTIONS
#*****************************
def getRandomName(length):
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))

def createQueue(sio):
    messagesQueue = asyncio.Queue()
    messages = ["created", "joined", "full", "new_peer", "invite", "ok", "ice_candidate", "bye"]
    for message in messages:
        sio.on(message, lambda content='', signal=message: messagesQueue.put_nowait((signal, content)))
    return messagesQueue

async def main():
    sio = socketio.AsyncClient(ssl_verify=False)
    messagesQueue = createQueue(sio)

    while True:
        #Wait until keypress (to be replaced later by the pushbutton press event)
        input("Press key to continue")

        #Connect to the signaling server.
        await sio.connect(SERVER_URL)
        
        #Join a conference room with a random name (send 'create' signal with room name).
        roomName = getRandomName(ROOM_NAME_SIZE)
        await sio.emit('create', roomName)

        #Wait for response. If response is 'joined' or 'full', stop processing and return to the loop. Go on if response is 'created'.
        response = await messagesQueue.get()
        responseMessage = response[0]

        if responseMessage == "full" or responseMessage == "joined":
            continue


        #Send a message (SMS, Telegram, email, ...) to the user with the room name. Or simply start by printing it on the terminal. 
        
        #Wait (with timeout) for a 'new_peer' message. If timeout, send 'bye' to signaling server and return to the loop. 
        
        #Wait (with timeout) for an 'invite' message. If timemout, send 'bye to signaling server and return to the loop. 
        
        #Acquire the media stream from the Webcam.
        
        #Create the PeerConnection and add the streams from the local Webcam.
        
        #Add the SDP from the 'invite' to the peer connection.
        
        #Generate the local session description (answer) and send it as 'ok' to the signaling server.
        
        #Wait (with timeout) for a 'bye' message. 
        
        #Send a 'bye' message back and clean everything up (peerconnection, media, signaling).

#*****************************
# MAIN PROGRAM
#*****************************
main()