'use strict';

// ==========================================================================
// Global variables
// ==========================================================================
var peerConnection; // WebRTC PeerConnection
var room; // Room name: Caller and Callee have to join the same 'room'.
var socket; // Socket.io connection to the Web server for signaling.

// ==========================================================================
// 1. Make call
// ==========================================================================

// --------------------------------------------------------------------------
// Function call, when call button is clicked.
async function call() {
  // Enable local video stream from micro or screen sharing
  var localStream = await enable_micro();
  
  // get room name from argument
  


  // Create Socket.io connection for signaling and add handlers
  // Then start signaling to join a room
  socket = create_signaling_connection();
  add_signaling_handlers(socket);
  call_room(socket);
  
  // Create peerConneciton and add handlers
  peerConnection = create_peerconnection(localStream);
  add_peerconnection_handlers(peerConnection);
}

// --------------------------------------------------------------------------
// Enable camera
// use getUserMedia or displayMedia (share screen). 
// Then show it on localVideo.
async function enable_micro() {

  const constraints = {
    'audio':true,
    'video':false
  };
  console.log('Getting user media with constraints', constraints);

  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia(constraints);
    console.log('Got MediaStream:', stream);
  } catch (error) {
    console.error('Error accessing media devices.', error);
  }

  return stream;
}

// ==========================================================================
// 2. Signaling connection: create Socket.io connection and connect handlers
// ==========================================================================

// --------------------------------------------------------------------------
// Create a Socket.io connection with the Web server for signaling
function create_signaling_connection() {
  //               provided by the socket.io library (included in index.html).
  let socket = io();
  return socket;
}

// --------------------------------------------------------------------------
// Connect the message handlers for Socket.io signaling messages
function add_signaling_handlers(socket) {
  // Event handlers for joining a room. Just print console messages
  // --------------------------------------------------------------
  //               messages 'created', 'joined', 'full'.
  //               For all three messages, simply write a console log.
  
  socket.on('created',(info) => {
    console.log(info);

  });

  socket.on('joined', (info) => {
    console.log(info);
    handle_joined()
  });

  socket.on('full', (info) => {
    console.log(info);
  });

  // Event handlers for call establishment signaling messages
  // --------------------------------------------------------
  // new_peer --> handle_new_peer
  socket.on('new_peer',(room) => {
    handle_new_peer(room);
  });

  // invite --> handle_invite
  socket.on('invite',(offer) => {
    handle_invite(offer);
  });
  // ok --> handle_ok
  socket.on('ok',(answer) => {
    handle_ok(answer);
  });
  // ice_candidate --> handle_remote_icecandidate
  socket.on('ice_candidate',(candidate) => {
    handle_remote_icecandidate(candidate);
  });
  // bye --> hangUp
  socket.on('bye',() => {
    hangUp();
  });

}
// --------------------------------------------------------------------------
// get room name from url parameter
function get_room_name_from_url() {
  let params = new URLSearchParams(document.location.search.substring(1));
  let room_name = params.get("room");

  return room_name
}


// --------------------------------------------------------------------------
// Prompt user for room name then send a "join" event to server
function call_room(socket) {

  room = get_room_name_from_url()
  if (room == null) {
    room = prompt('Enter room name:');
  }  
  if (room != '') {
      console.log('Joining room: ' + room);
      socket.emit('join',room);
  }
}

// ==========================================================================
// 3. PeerConnection creation
// ==========================================================================

// --------------------------------------------------------------------------
// Create a new RTCPeerConnection and connect local stream
function create_peerconnection(localStream) {
  const pcConfiguration = {'iceServers': [{'urls': 'stun:stun.l.google.com:19302'}]}

  var pc = new RTCPeerConnection(pcConfiguration);
  
  localStream.getTracks().forEach(track => {
    pc.addTrack(track, localStream);
  });

  return pc;
}

// --------------------------------------------------------------------------
// Set the event handlers on the peerConnection. 
// This function is called by the call function all on top of the file.
function add_peerconnection_handlers(peerConnection) {

  // onicecandidate -> handle_local_icecandidate
  peerConnection.onicecandidate = handle_local_icecandidate;

  // ontrack -> handle_remote_track
  peerConnection.ontrack = handle_remote_track;
  
}

// ==========================================================================
// 4. Signaling for peerConnection negotiation
// ==========================================================================

// --------------------------------------------------------------------------
// Handle new peer: another peer has joined the room. I am the Caller.
// Create SDP offer and send it to peer via the server.
async function handle_new_peer(room){
  console.log('Peer has joined room: ' + room + '. I am the Caller.');

  let offer = await peerConnection.createOffer();
  await peerConnection.setLocalDescription(offer);
  socket.emit('invite', offer); 
}

// --------------------------------------------------------------------------
// Caller has sent Invite with SDP offer. I am the Callee.
// Set remote description and send back an Ok answer.
async function handle_invite(offer) {
  console.log('Received Invite offer from Caller: ', offer);
  await peerConnection.setRemoteDescription(offer);
  var answer = await peerConnection.createAnswer();
  await peerConnection.setLocalDescription(answer);
  socket.emit('ok', answer); 
}

// --------------------------------------------------------------------------
// Callee has sent Ok answer. I am the Caller.
// Set remote description.
async function handle_ok(answer) {
  console.log('Received OK answer from Callee: ', answer);

  // since the answer is sent by aiortc we need to reinstantiate the object

  await peerConnection.setRemoteDescription(JSON.parse(answer));
}

async function handle_joined() {
  console.log("Received Joined message")

  peerConnection.addTransceiver('video', {direction: 'recvonly'});
  
  let offer = await peerConnection.createOffer();
  await peerConnection.setLocalDescription(offer);
  console.log("Create offer and setlocaledescription done!");
}

// ==========================================================================
// 5. ICE negotiation and remote stream handling
// ==========================================================================

// --------------------------------------------------------------------------
// A local ICE candidate has been created by the peerConnection.
// Send it to the peer via the server.
async function handle_local_icecandidate(event) {
  console.log('Received local ICE candidate: ', event);
  if (!event.candidate) {
    let offer = peerConnection.localDescription;
    socket.emit('invite', offer)
  }
}

// --------------------------------------------------------------------------
// The peer has sent a remote ICE candidate. Add it to the PeerConnection.
async function handle_remote_icecandidate(candidate) {
  console.log('Received remote ICE candidate: ', candidate);
  peerConnection.addIceCandidate(candidate); 

}

// ==========================================================================
// 6. Function to handle remote video stream
// ==========================================================================

// --------------------------------------------------------------------------
// A remote track event has been received on the peerConnection.
// Show the remote track video on the web page.
function handle_remote_track(event) {
  console.log('Received remote track: ', event);
  document.getElementById('remoteVideo').srcObject = event.streams[0];
}

// ==========================================================================
// 8. Functions to end call
// ==========================================================================

// --------------------------------------------------------------------------
// HangUp: Send a bye message to peer and close all connections and streams.
function hangUp() {
  console.log("Terminating the connection");

  socket.emit('bye',room)

  // Switch off the local stream by stopping all tracks of the local stream
  var remoteVideo = document.getElementById('remoteVideo')

  remoteVideo.srcObject.getTracks().forEach(track => track.stop());
  
  remoteVideo = null;

  peerConnection.close();
  peerConnection = null;
  
}

// --------------------------------------------------------------------------
// Clean-up: hang up before unloading the window
window.onbeforeunload = function(e) {
  hangUp();
}