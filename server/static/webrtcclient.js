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
  // Enable local video stream from camera or screen sharing
  var localStream = await enable_mic();

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
// Enable mic
async function enable_mic() {
  const constraints = {'audio': true};

  console.log('Getting user media with constraints', constraints);

  //use getUserMedia to get a local media stream from the mic.
  //  If this fails, print error and continue
  var stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia(constraints);
  } catch(e) {
    console.log('No mic ;(')
  }

  return stream;
}

// ==========================================================================
// 2. Signaling connection: create Socket.io connection and connect handlers
// ==========================================================================

// --------------------------------------------------------------------------
// Create a Socket.io connection with the Web server for signaling
function create_signaling_connection() {
  //create a socket by simply calling the io() function
  //  provided by the socket.io library (included in index.html).
  var socket = io();
  return socket;
}

// --------------------------------------------------------------------------
// Connect the message handlers for Socket.io signaling messages
function add_signaling_handlers(socket) {
  // Event handlers for joining a room. Just print console messages
  // --------------------------------------------------------------
  //use the 'socket.on' method to create handlers for the 
  //  messages 'created', 'joined', 'full'.
  //  For all three messages, simply write a console log.
  socket.on('created', (data) => {
    console.log("created: " + data);
  });

  socket.on('joined', (data) => {
    console.log("joined: " + data);
  });

  socket.on('full', (data) => {
    console.log("full: " + data);
  });

  // Event handlers for call establishment signaling messages
  // --------------------------------------------------------
  //use the 'socket.on' method to create signaling message handlers:

  // invite --> handle_invite
  socket.on('invite', (data) => {
    handle_invite(data);
  });

  // bye --> hangUp
  socket.on('bye', (room_name) => {
    if(room == room_name) {
      hangUp();
    }
  });

}

// --------------------------------------------------------------------------
// Prompt user for room name then send a "join" event to server
function call_room(socket) {
  room = prompt('Enter room name:');
  if (room != '') {
      console.log('Joining room: ' + room);
      //send a join message to the server with room as argument.
      socket.emit('join', room);
  }
}

// ==========================================================================
// 3. PeerConnection creation
// ==========================================================================

// --------------------------------------------------------------------------
// Create a new RTCPeerConnection and connect local stream
function create_peerconnection(localStream) {
  const pcConfiguration = {'iceServers': [{'urls': 'stun:stun.l.google.com:19302'}]}

  //create a new RTCPeerConnection with this configuration
  var pc = new RTCPeerConnection([pcConfiguration]);

  //add all tracks of the local stream to the peerConnection
  localStream.getTracks().forEach(track => {
    pc.addTrack(track, localStream);
  });

  return pc;
}

// --------------------------------------------------------------------------
// Set the event handlers on the peerConnection. 
// This function is called by the call function all on top of the file.
function add_peerconnection_handlers(peerConnection) {
  //add event handlers on the peerConnection

  // onicecandidate -> handle_local_icecandidate
  peerConnection.onicecandidate = event => handle_local_icecandidate(event);

  // ontrack -> handle_remote_track
  peerConnection.ontrack = event => handle_remote_track(event);
}

// ==========================================================================
// 4. Signaling for peerConnection negotiation
// ==========================================================================

// --------------------------------------------------------------------------

// --------------------------------------------------------------------------
// Caller has sent Invite with SDP offer. I am the Callee.
// Set remote description and send back an Ok answer.
async function handle_invite(offer) {
  console.log('Received Invite offer from Caller: ', offer);
  //use setRemoteDescription (with await) to add the offer SDP to peerConnection
  await peerConnection.setRemoteDescription(offer); 
  //use createAnswer (with await) to generate an answer SDP
  var answer = await peerConnection.createAnswer();
  //use setLocalDescription (with await) to add the answer SDP to peerConnection
  await peerConnection.setLocalDescription(answer);
  //wait to send an 'ok' message with the answer to the peer so that it will contain ICE candidates.
}

// ==========================================================================
// 5. ICE negotiation and remote stream handling
// ==========================================================================

// --------------------------------------------------------------------------
// A local ICE candidate has been created by the peerConnection.
// Send it to the peer via the server.
async function handle_local_icecandidate(event) {
  console.log('Received local ICE candidate: ', event);
  //check if there is a new ICE candidate.
  // Once there aren't anymore, send the localDescription containing ICE candidates
  if (!event.candidate) {
    socket.emit('ok', peerConnection.localDescription);
  }
}

// ==========================================================================
// 6. Function to handle remote video stream
// ==========================================================================

// --------------------------------------------------------------------------
// A remote track event has been received on the peerConnection.
// Show the remote track video on the web page.
function handle_remote_track(event) {
  console.log('Received remote track: ', event);
  //get the first stream of the event and show it in remoteVideo
  document.getElementById('remoteVideo').srcObject = event.streams[0];
}


// ==========================================================================
// 8. Functions to end call
// ==========================================================================

// --------------------------------------------------------------------------
// HangUp: Send a bye message to peer and close all connections and streams.
function hangUp() {
  //Write a console log
  console.log("Connection will be terminated")

  //send a bye message with the room name to the server
  socket.emit('bye', room);

  // Switch off the local stream by stopping all tracks of the local stream
  var remoteVideo = document.getElementById('remoteVideo')

  //remove the tracks from localVideo and remoteVideo
  if (remoteVideo.srcObject) {
    remoteVideo.srcObject.getTracks().forEach(track => track.stop());
  }

  //set localVideo and remoteVideo source objects to null
  remoteVideo.srcObject = null;

  //close the peerConnection and set it to null
  if(peerConnection) {
    peerConnection.close();
    peerConnection = null;
  }

}

// --------------------------------------------------------------------------
// Clean-up: hang up before unloading the window
window.onbeforeunload = function(e) {
  hangUp();
  //socket.emit('bye', room);
}
