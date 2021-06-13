import socketio
import asyncio

# asyncio
sio = socketio.AsyncClient(ssl_verify=False)

async def connect():
    # connecting to the server
    await sio.connect('https://192.168.43.240:443')
    print('my sid is', sio.sid)

if __name__ == "__main__":
    # run event loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(connect())
    except KeyboardInterrupt:
        pass
    #finally:
     #   loop.run_until_complete(pc.close())
      #  loop.run_until_complete(signaling.close())
    

"""
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
"""
