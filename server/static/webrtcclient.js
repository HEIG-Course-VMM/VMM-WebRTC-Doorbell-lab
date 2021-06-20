'use strict';

// ==========================================================================
// Global variables
// ==========================================================================
var peerConnection; // WebRTC PeerConnection
var dataChannel; // WebRTC DataChannel
var room; // Room name: Caller and Callee have to join the same 'room'.
var socket; // Socket.io connection to the Web server for signaling.

// ==========================================================================
// 1. Make call
// ==========================================================================

// --------------------------------------------------------------------------
// Function call, when call button is clicked.
async function call() {
  // Enable local video stream from camera or screen sharing
  var localStream = await enable_camera();

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
async function enable_camera() {

  // *** TODO ***: define constraints: set video to true, audio to false
  const constraints = {
    'video': true,
    'audio': false
  }

  console.log('Getting user media with constraints', constraints);

  const openMediaDevices = async (constraints) => {
    console.log(constraints);
    return await navigator.mediaDevices.getUserMedia(constraints);
  }

  const openMediaSharing = async (constraints) => {
    return await navigator.mediaDevices.getDisplayMedia(constraints);
  }

  var stream;

  try {
    stream = await openMediaDevices(constraints);
    console.log('Got video stream:', stream);

  } catch(error) {
      console.error('Error accessing media devices.', error);
      console.error('Trying screen sharing', error);

      try {
        stream = await openMediaSharing(constraints);
        console.log('Got sharing stream:', stream);
      } catch(error) {
          console.error('Error accessing screen sharing', error);
          alert('Error accessing screen sharing');
      }
  }

  document.getElementById('localVideo').srcObject = stream;
  return stream;
}

// ==========================================================================
// 2. Signaling connection: create Socket.io connection and connect handlers
// ==========================================================================

// --------------------------------------------------------------------------
// Create a Socket.io connection with the Web server for signaling
function create_signaling_connection() {
  var socket = io();
  return socket;
}

// --------------------------------------------------------------------------
// Connect the message handlers for Socket.io signaling messages
function add_signaling_handlers(socket) {
  socket.on('created', (data) => 
    console.log("created : " + data)
  );

  socket.on('joined', (data) => 
    console.log("joined : " + data)
  );

  socket.on('full', (data) => 
    console.log("full : " + data)
  );

  // Event handlers for call establishment signaling messages
  // --------------------------------------------------------
  socket.on('new_peer', (room) => 
    handle_new_peer(room)
  );

  // invite --> handle_invite
  socket.on('invite', (offer) => 
    handle_invite(offer)
  );

  // ok --> handle_ok
  socket.on('ok', (answer) => 
    handle_ok(answer)
  );

  // ice_candidate --> handle_remote_icecandidate
  socket.on('ice_candidate', (candidate) => 
    handle_remote_icecandidate(candidate)
  );

  // bye --> hangUp
  socket.on('bye', () => 
    hangUp()
  );
}

// --------------------------------------------------------------------------
// Prompt user for room name then send a "join" event to server
function call_room(socket) {
  room = prompt('Enter room name:');
  if (room != '') {
      console.log('Joining room: ' + room);
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
  var pc = new RTCPeerConnection([pcConfiguration]);
  
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
  peerConnection.onicecandidate = function(event) {
    handle_local_icecandidate(event);
  }

  // ontrack -> handle_remote_track
  peerConnection.ontrack = function(event) {
    handle_remote_track(event);
  }

  // ondatachannel -> handle_remote_datachannel
  peerConnection.ondatachannel = function(event) {
    handle_remote_datachannel(event);
  }
}

// ==========================================================================
// 4. Signaling for peerConnection negotiation
// ==========================================================================

// --------------------------------------------------------------------------
// Handle new peer: another peer has joined the room. I am the Caller.
// Create SDP offer and send it to peer via the server.
async function handle_new_peer(room){
  console.log('Peer has joined room: ' + room + '. I am the Caller.');
  create_datachannel(peerConnection); // MUST BE CALLED BEFORE createOffer

  var offer = await peerConnection.createOffer();

  await peerConnection.setLocalDescription(offer);

  socket.emit('invite', offer); 
}

// --------------------------------------------------------------------------
// Caller has sent Invite with SDP offer. I am the Callee.
// Set remote description and send back an Ok answer.
async function handle_invite(offer) {
  console.log('Received Invite offer from Caller: ', offer);
  await peerConnection.setRemoteDescription(offer)

  var answer = await peerConnection.createAnswer()
  
  await peerConnection.setLocalDescription(answer)

  socket.emit('ok', answer); 
}

// --------------------------------------------------------------------------
// Callee has sent Ok answer. I am the Caller.
// Set remote description.
async function handle_ok(answer) {
  console.log('Received OK answer from Callee: ', answer);
  await peerConnection.setRemoteDescription(answer)
}

// ==========================================================================
// 5. ICE negotiation and remote stream handling
// ==========================================================================

// --------------------------------------------------------------------------
// A local ICE candidate has been created by the peerConnection.
// Send it to the peer via the server.
async function handle_local_icecandidate(event) {
  console.log('Received local ICE candidate: ', event);
  if (event.candidate) {
    console.log(event.candidate);
    socket.emit('ice_candidate', event.candidate); 
  }
}

// --------------------------------------------------------------------------
// The peer has sent a remote ICE candidate. Add it to the PeerConnection.
async function handle_remote_icecandidate(candidate) {
  console.log('Received remote ICE candidate: ', candidate);
  await peerConnection.addIceCandidate(candidate)
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
// 7. Functions to establish and use the DataChannel
// ==========================================================================

// --------------------------------------------------------------------------
// Create a data channel: only used by the Caller.
function create_datachannel(peerConnection) {
  console.log('Creating dataChannel. I am the Caller.');

  dataChannel = peerConnection.createDataChannel("chat");

  dataChannel.onopen = function(event) {
    handle_datachannel_open(event);
  }

  dataChannel.onmessage = function(event) {
    handle_datachannel_message(event);
  }
}

// --------------------------------------------------------------------------
// Handle remote data channel from Caller: only used by the Callee.
function handle_remote_datachannel(event) {
  console.log('Received remote dataChannel. I am Callee.');

  dataChannel = event.channel;

  dataChannel.onopen = function(event) {
    handle_datachannel_open(event);
  }

  dataChannel.onmessage = function(event) {
    handle_datachannel_message(event);
  }
}

// --------------------------------------------------------------------------
// Handle Open event on dataChannel: show a message.
// Received by the Caller and the Callee.
function handle_datachannel_open(event) {
  dataChannel.send('*** Channel is ready ***');
}

// --------------------------------------------------------------------------
// Send message to peer when Send button is clicked
function sendMessage() {
  var message = document.getElementById('dataChannelInput').value;
  document.getElementById('dataChannelInput').value = '';
  document.getElementById('dataChannelOutput').value += '        ME: ' + message + '\n';

  dataChannel.send(message);
}

// Handle Message from peer event on dataChannel: display the message
function handle_datachannel_message(event) {
  document.getElementById('dataChannelOutput').value += 'PEER: ' + event.data + '\n';
}

// ==========================================================================
// 8. Functions to end call
// ==========================================================================

// --------------------------------------------------------------------------
// HangUp: Send a bye message to peer and close all connections and streams.
function hangUp() {
  console.log('Connection will be terminated');

  socket.emit('bye', room); 

  // Switch off the local stream by stopping all tracks of the local stream
  var localVideo = document.getElementById('localVideo');
  var remoteVideo = document.getElementById('remoteVideo');

  if(localVideo.srcObject){
    localVideo.srcObject.getTracks().forEach(track => {
      track.stop();
    });
  }

  if(remoteVideo.srcObject){
    remoteVideo.srcObject.getTracks().forEach(track => {
      track.stop();
    });
  }

  if(localVideo){
    localVideo.srcObject = null;
  }

  if(remoteVideo){
    remoteVideo.srcObject = null;
  }
  
  if(peerConnection){
    peerConnection.close();
    peerConnection=null;
  }

  if(dataChannel){
    dataChannel.close();
    dataChannel = null;
  }

  socket.close();

  document.getElementById('dataChannelOutput').value += '*** Channel is closed ***\n';
}

// --------------------------------------------------------------------------
// Clean-up: hang up before unloading the window
window.onbeforeunload = function(e) {
  hangUp();
}