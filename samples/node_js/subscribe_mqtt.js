/*
  This sample connects to the VSCP demo mqtt server and subscribe to events from a
  sensor located in the upper floor of the garage.
  
  GUID info is here https://github.com/grodansparadis/vscp/wiki/VSCP-Demo-GUID%27s#raspberry-pi-3

  https://www.npmjs.com/package/paho-mqtt
  https://www.emqx.com/en/blog/how-to-use-mqtt-in-nodejs
  https://www.hivemq.com/blog/ultimate-guide-on-how-to-use-mqtt-with-node-js/
*/

/*
  if using browser
  import fs from 'fs';
  import mqtt from 'mqtt';
*/
const fs = require('fs');
const mqtt = require('mqtt');

const options = {
  username: "vscp",
  password: "secret",
  protocol: 'mqtt',
  host: 'mqtt.vscp.org',
  port: 1883
  /*
    If using SSL
    ca: [fs.readFileSync('/path/to/ca.crt')],
    cert: fs.readFileSync('/path/to/client.crt'),
    key: fs.readFileSync('/path/to/client.key')
  */
};

// Temperature garage upper (~every minute)
// 25:00:00:00:00:00:00:00:00:00:00:00:05:01:00:02 = GUID for sensor
// 1040 = measurements
// 6 = temperature
// 2 = node id (nickname, same as GUID LSB)
// 0 = sensor index
const topic = "vscp/25:00:00:00:00:00:00:00:00:00:00:00:05:01:00:02/1040/6/2/0/#";

console.log("Connecting to MQTT broker...");
const client = mqtt.connect(options);


client.on('connect', () => {
  console.log('Connected to MQTT broker.')
  
  client.subscribe([topic], () => {
    console.log(`Subscribe to topic '${topic}'`)
  })
})

client.on('message', (topic, payload) => {
  console.log('Received Message:', topic, payload.toString())
})


 
// called when the client loses its connection
client.on('connectionlost', (responseObject) => {
  if (responseObject.errorCode !== 0) {
    console.log("onConnectionLost:"+responseObject.errorMessage);
  }
})
 






// client.on('auth', (packet, cb) => {
//   console.log('Authenticating with certificate...');

//   // Check the certificate properties and perform the authentication logic here.
//   // Call cb() with an error if authentication fails or null if it succeeds.
//   cb(null);
// });