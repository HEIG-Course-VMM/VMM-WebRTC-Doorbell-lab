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
        rooms_db[user_id] = room_name
        join_room(room_name)
        emit('created', room_name)
    elif members == 1:
        print(f'Received join from user: {user_id} for EXISTING room: {room_name}.')
        rooms_db[user_id] = room_name
        join_room(room_name)
        emit('joined', room_name)
        emit('new_peer', room = room_name, broadcast=True, include_self=False)
    else:
        print(f'Refusing join from user: {user_id} for FULL room: {room_name}.')
        emit('full', room_name)

def handle_p2pmessage(msg_type, content):
    user_id = request.sid
    room_name = rooms_db.get(user_id)
    print(f"Received {msg_type} message: {content} from user: {user_id} in room {room_name}")
    emit(msg_type, content, room = room_name, broadcast=True, include_self=False)

@socketio.on('invite')
def handle_invite(data):
    handle_p2pmessage('invite', data)

@socketio.on('ok')
def handle_ok(data):
    handle_p2pmessage('ok', data)

@socketio.on('ice_candidate')
def handle_icecandidate(data):
    handle_p2pmessage('ice_candidate', data)

@socketio.on('bye')
def handle_bye(room_name):
    user_id = request.sid
    leave_room(room_name)
    handle_p2pmessage('bye', room_name)
    rooms_db.pop(user_id)

    pass

# ===========================================================================
# Run server
if __name__ == '__main__':
    socketio.run(app, "0.0.0.0", 443, ssl_context=('cert.pem', 'key.pem'))
