const config = require('./config')

let ws = null
let clientId = ''
let deviceId = ''
let onConnectCallback = null
let onMessageCallback = null
let onDisconnectCallback = null
let isConnected = false
let pingTimer = null
let packetId = 1

function connect(callback) {
  const { mqttUsername, mqttPassword, mqttClientId, mqttHostname, mqttPort } = config
  
  clientId = mqttClientId
  deviceId = mqttClientId.split('_')[0] + '_' + mqttClientId.split('_')[1]
  onConnectCallback = callback
  
  console.log('[MQTT] 连接:', mqttHostname, mqttPort)
  
  const url = `wss://${mqttHostname}:${mqttPort}/mqtt`
  console.log('[MQTT] URL:', url)
  
  ws = wx.connectSocket({
    url: url,
    protocols: ['mqtt'],
    success: () => {
      console.log('[MQTT] WebSocket创建成功')
    },
    fail: (err) => {
      console.log('[MQTT] WebSocket创建失败:', err)
    }
  })
  
  ws.onOpen(() => {
    console.log('[MQTT] WebSocket打开')
    sendConnectPacket(mqttUsername, mqttPassword, mqttClientId)
  })
  
  ws.onMessage((res) => {
    console.log('[MQTT] 收到:', res.data)
    handleMQTTMessage(res.data)
  })
  
  ws.onError((err) => {
    console.log('[MQTT] 错误:', err)
    isConnected = false
    stopPing()
    if (onDisconnectCallback) onDisconnectCallback()
  })
  
  ws.onClose(() => {
    console.log('[MQTT] 关闭')
    isConnected = false
    stopPing()
    if (onDisconnectCallback) onDisconnectCallback()
    setTimeout(() => connect(callback), 5000)
  })
}

function sendConnectPacket(username, password, clientId) {
  const packet = []
  
  const protoName = 'MQTT'
  const protoVersion = 4
  const flags = 0xC2
  const keepalive = 60
  
  const payload = []
  
  payload.push((protoName.length >> 8) & 0xFF)
  payload.push(protoName.length & 0xFF)
  for (let i = 0; i < protoName.length; i++) {
    payload.push(protoName.charCodeAt(i))
  }
  
  payload.push(protoVersion)
  payload.push(flags)
  payload.push((keepalive >> 8) & 0xFF)
  payload.push(keepalive & 0xFF)
  
  payload.push((clientId.length >> 8) & 0xFF)
  payload.push(clientId.length & 0xFF)
  for (let i = 0; i < clientId.length; i++) {
    payload.push(clientId.charCodeAt(i))
  }
  
  payload.push((username.length >> 8) & 0xFF)
  payload.push(username.length & 0xFF)
  for (let i = 0; i < username.length; i++) {
    payload.push(username.charCodeAt(i))
  }
  
  payload.push((password.length >> 8) & 0xFF)
  payload.push(password.length & 0xFF)
  for (let i = 0; i < password.length; i++) {
    payload.push(password.charCodeAt(i))
  }
  
  let remainingLength = payload.length
  const remainingEncoded = []
  
  do {
    let byte = remainingLength % 128
    remainingLength = Math.floor(remainingLength / 128)
    if (remainingLength > 0) {
      byte |= 0x80
    }
    remainingEncoded.push(byte)
  } while (remainingLength > 0)
  
  packet.push(0x10)
  packet.push(...remainingEncoded)
  packet.push(...payload)
  
  const buffer = new Uint8Array(packet)
  console.log('[MQTT] CONNECT包长度:', buffer.length)
  
  ws.send({
    data: buffer,
    success: () => {
      console.log('[MQTT] CONNECT已发送')
    },
    fail: (err) => {
      console.log('[MQTT] CONNECT发送失败:', err)
    }
  })
}

function handleMQTTMessage(data) {
  if (!(data instanceof ArrayBuffer)) {
    return
  }
  
  const buffer = new Uint8Array(data)
  const packetType = (buffer[0] >> 4) & 0x0F
  
  if (packetType === 2) {
    console.log('[MQTT] CONNACK收到')
    const returnCode = buffer[3]
    
    if (returnCode === 0) {
      console.log('[MQTT] 连接成功!')
      isConnected = true
      startPing()
      if (onConnectCallback) onConnectCallback()
    } else {
      console.log('[MQTT] 连接失败，返回码:', returnCode)
      const reasons = ['连接成功', '不支持的协议版本', '客户端标识符无效', '服务器不可用', '用户名或密码错误', '未授权']
      console.log('[MQTT] 原因:', reasons[returnCode] || '未知错误')
    }
  } else if (packetType === 4) {
    console.log('[MQTT] PINGRESP收到')
  } else if (packetType === 3) {
    const topicLength = (buffer[2] << 8) | buffer[3]
    let topic = ''
    for (let i = 4; i < 4 + topicLength; i++) {
      topic += String.fromCharCode(buffer[i])
    }
    
    let payloadStart = 4 + topicLength
    if (buffer[0] & 0x01) {
      payloadStart += 2
    }
    
    const payload = buffer.slice(payloadStart)
    const message = new TextDecoder().decode(payload)
    
    console.log('[MQTT] PUBLISH收到:', topic, message)
    
    if (onMessageCallback) {
      onMessageCallback(topic, message)
    }
  }
}

function startPing() {
  stopPing()
  pingTimer = setInterval(() => {
    if (isConnected && ws) {
      const packet = [0xC0, 0x00]
      const buffer = new Uint8Array(packet)
      ws.send({
        data: buffer,
        success: () => {
          console.log('[MQTT] PINGREQ发送')
        },
        fail: (err) => {
          console.log('[MQTT] PINGREQ发送失败:', err)
        }
      })
    }
  }, 30000)
}

function stopPing() {
  if (pingTimer) {
    clearInterval(pingTimer)
    pingTimer = null
  }
}

function publish(properties) {
  if (!isConnected || !ws) {
    console.log('[MQTT] 未连接')
    return
  }
  
  const topic = `$oc/devices/${deviceId}/sys/properties/report`
  
  const payload = {
    services: [{
      service_id: '1234',
      properties: properties
    }]
  }
  
  const payloadStr = JSON.stringify(payload)
  
  const packet = []
  packet.push(0x30)
  
  const topicLength = topic.length
  const remainingLength = 2 + topicLength + payloadStr.length
  
  const remainingEncoded = []
  let rl = remainingLength
  do {
    let byte = rl % 128
    rl = Math.floor(rl / 128)
    if (rl > 0) {
      byte |= 0x80
    }
    remainingEncoded.push(byte)
  } while (rl > 0)
  
  packet.push(...remainingEncoded)
  
  packet.push((topicLength >> 8) & 0xFF)
  packet.push(topicLength & 0xFF)
  for (let i = 0; i < topic.length; i++) {
    packet.push(topic.charCodeAt(i))
  }
  
  for (let i = 0; i < payloadStr.length; i++) {
    packet.push(payloadStr.charCodeAt(i))
  }
  
  const buffer = new Uint8Array(packet)
  
  ws.send({
    data: buffer,
    success: () => {
      console.log('[MQTT] 发布成功:', topic)
    },
    fail: (err) => {
      console.log('[MQTT] 发布失败:', err)
    }
  })
}

function subscribe(topic) {
  if (!isConnected || !ws) {
    console.log('[MQTT] 未连接')
    return
  }
  
  const packet = []
  packet.push(0x82)
  
  const currentPacketId = packetId++
  const topicLength = topic.length
  
  const remainingLength = 2 + 2 + topicLength + 1
  
  const remainingEncoded = []
  let rl = remainingLength
  do {
    let byte = rl % 128
    rl = Math.floor(rl / 128)
    if (rl > 0) {
      byte |= 0x80
    }
    remainingEncoded.push(byte)
  } while (rl > 0)
  
  packet.push(...remainingEncoded)
  
  packet.push((currentPacketId >> 8) & 0xFF)
  packet.push(currentPacketId & 0xFF)
  
  packet.push((topicLength >> 8) & 0xFF)
  packet.push(topicLength & 0xFF)
  for (let i = 0; i < topic.length; i++) {
    packet.push(topic.charCodeAt(i))
  }
  
  packet.push(0x00)
  
  const buffer = new Uint8Array(packet)
  
  ws.send({
    data: buffer,
    success: () => {
      console.log('[MQTT] 订阅:', topic)
    },
    fail: (err) => {
      console.log('[MQTT] 订阅失败:', err)
    }
  })
}

function publishCommand(commandName, paras) {
  if (!isConnected || !ws) {
    console.log('[MQTT] 未连接')
    return
  }
  
  const requestId = `req_${Date.now()}`
  const topic = `$oc/devices/${deviceId}/sys/commands/request_id=${requestId}`
  
  const payload = {
    paras: paras,
    command_name: commandName,
    service_id: '1234'
  }
  
  const payloadStr = JSON.stringify(payload)
  
  const packet = []
  packet.push(0x30)
  
  const topicLength = topic.length
  const remainingLength = 2 + topicLength + payloadStr.length
  
  const remainingEncoded = []
  let rl = remainingLength
  do {
    let byte = rl % 128
    rl = Math.floor(rl / 128)
    if (rl > 0) {
      byte |= 0x80
    }
    remainingEncoded.push(byte)
  } while (rl > 0)
  
  packet.push(...remainingEncoded)
  
  packet.push((topicLength >> 8) & 0xFF)
  packet.push(topicLength & 0xFF)
  for (let i = 0; i < topic.length; i++) {
    packet.push(topic.charCodeAt(i))
  }
  
  for (let i = 0; i < payloadStr.length; i++) {
    packet.push(payloadStr.charCodeAt(i))
  }
  
  const buffer = new Uint8Array(packet)
  
  ws.send({
    data: buffer,
    success: () => {
      console.log('[MQTT] 命令下发成功:', topic)
    },
    fail: (err) => {
      console.log('[MQTT] 命令下发失败:', err)
    }
  })
}

function disconnect() {
  stopPing()
  if (ws) {
    ws.close()
    ws = null
  }
  isConnected = false
}

function setOnMessageCallback(callback) {
  onMessageCallback = callback
}

function setOnDisconnectCallback(callback) {
  onDisconnectCallback = callback
}

function getStatus() {
  return isConnected
}

module.exports = {
  connect,
  publish,
  publishCommand,
  subscribe,
  disconnect,
  setOnMessageCallback,
  setOnDisconnectCallback,
  getStatus
}