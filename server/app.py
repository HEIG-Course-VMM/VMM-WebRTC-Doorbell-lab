from flask import Flask, request, session
from flask_socketio import SocketIO, emit, send, join_room, leave_room
from collections import defaultdict

# ===========================================================================
# 'Database' to store room of each user: user_id -> room_name
rooms_db = {}

# ===========================================================================
# Serve static HTML page with Javascript WebRTC client
app = Flask(__name__)
@app.route('/')
def index():
    return app.send_static_file('index.html')

# ===========================================================================
# Websocket signaling handlers 
# Messages allowed are:
#   - "join(room_name)": Join a conferencing room, or create if not exists
#   - "invite(offer)": Caller invites Callee with a SDP offer.
#   - "ok(answer)": Callee responds to SDP offer with a SDP answer.
#   - "bye(room_name)": quit connection and leave room.
#   - "ice_candidate(candidate)": send and ICE candidate to the peer.
# Additionally, the "connect" and "disconnect" events are received for clients
# ===========================================================================
socketio = SocketIO(app)

@socketio.on('connect')
def handle_connect():
    print("Received connect")

@socketio.on('disconnect')
def handle_disconnect():
    print("Received disconnect")

@socketio.on('join')
def handle_join(room_name):
    user_id = request.sid
    members = list(rooms_db.values()).count(room_name)
    if members == 0:
        print(f'Received join from user: {user_id} for NEW room: {room_name}.')
        #Add the user_id to the rooms_db dictionary with the room_name as value
        rooms_db[user_id] = room_name
        #Use the SocketIO function join_room to add the user to a SocketIO room.
        join_room(room_name)
        #Use the SocketIO emit function to send a 'created' message back with the room_name as argument
        emit('created', room_name)
    elif members == 1:
        print(f'Received join from user: {user_id} for EXISTING room: {room_name}.')
        #Add the user_id to rooms_db with room_name as value.
        rooms_db[user_id] = room_name
        #Use join_room to add the user to a SocketIO room.
        join_room(room_name)
        #Emit a 'joined' message back to the client, with the room_name as data.
        emit('joined', room_name)
        #Broadcast to existing client that there is a new peer
        emit('new_peer', room=room_name, broadcast=True, include_self=False)
    else:
        print(f'Refusing join from user: {user_id} for FULL room: {room_name}.')
        #Emit a 'full' message back to the client, with the room_name as data.
        emit('full', room_name)

def handle_p2pmessage(msg_type, content):
    #Get the user_id from the request variable (see handle_join)
    user_id = request.sid
    #Get the room_name of the user from rooms_db
    room_name = rooms_db.get(user_id)

    print(f"Received {msg_type} message: {content} from user: {user_id} in room {room_name}")
    
    #Broadcast the message to existing client in the SocketIO room.
    # Exclude the sender of the orignal message.
    emit(msg_type, content, room=room_name, broadcast=True, include_self=False)


#Create a message handler for 'invite' messages
@socketio.on('invite')
def handle_invite(content):
    handle_p2pmessage('invite', content)

#Create a message handler for 'ok' messages
@socketio.on('ok')
def handle_ok(content):
    handle_p2pmessage('ok', content)

#Create a message handler for 'ice_candidate' messages 
@socketio.on('ice_candidate')
def handle_icecandidate(content):
    handle_p2pmessage('ice_candidate', content)

@socketio.on('bye')
def handle_bye(room_name):
    #Get the user_id from the request variable
    user_id = request.sid
    #Use leave_room to remove the sender from the SocketIO room
    leave_room(room_name)
    #Remove the user from rooms_db
    print(rooms_db)
    if(rooms_db.get(user_id) == room_name):
        del rooms_db[user_id]
    #Forward the 'bye' message using p2p_message
    if(list(rooms_db.values()).count(room_name) > 0):
        handle_p2pmessage('bye', room_name)

    pass

# ===========================================================================
# Run server
if __name__ == '__main__':
    #socketio.run(app, "0.0.0.0", 443, ssl_context=('cert.pem', 'key.pem'))
    socketio.run(app, "0.0.0.0", 443, certfile='cert.pem', keyfile='key.pem')