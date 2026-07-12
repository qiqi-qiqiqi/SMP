const { getDeviceShadow, parseDeviceData, sendCommand } = require('./huaweiCloudApi')
const mqtt = require('./mqttApi')

Page({
  data: {
    temp: '--',
    humi: '--',
    relay: 0,
    beep: 0,
    rain: 0,
    person: '--',
    relaySending: false,
    beepSending: false,
    loading: false,
    lastUpdate: '--',
    restStatus: 'idle',
    mqttConnected: false,
    logs: []
  },

  timer: null,

  onLoad() {
    this.loadLogs()
    this.initMQTT()
    this.refreshData()
  },

  onUnload() {
    this.stopTimer()
    mqtt.disconnect()
  },

  initMQTT() {
    mqtt.setOnMessageCallback((topic, message) => {
      try {
        const data = JSON.parse(message)
        if (data.services && data.services[0] && data.services[0].properties) {
          const props = data.services[0].properties
          this.updateDeviceData(props)
          this.addLog('success', '设备属性更新: ' + JSON.stringify(props))
        } else if (data.paras && data.command_name) {
          const { command_name, paras } = data
          let logMsg = `命令: ${command_name}`
          if (paras.beep !== undefined) {
            logMsg += ` 蜂鸣器: ${paras.beep}`
            this.setData({ beep: paras.beep })
          }
          if (paras.relay !== undefined) {
            logMsg += ` 继电器: ${paras.relay}`
            this.setData({ relay: paras.relay })
          }
          this.addLog('success', logMsg)
        }
      } catch (e) {
        this.addLog('error', '消息解析失败: ' + e.message)
      }
    })

    mqtt.setOnDisconnectCallback(() => {
      this.setData({ mqttConnected: false })
      this.addLog('error', 'MQTT连接断开')
    })

    mqtt.connect(() => {
      this.setData({ mqttConnected: true })
      this.addLog('success', 'MQTT连接成功')
      this.reportOnline()
      
      const deviceId = '6a50aec2cbb0cf6bb96dc3dc_1234'
      mqtt.subscribe(`$oc/devices/${deviceId}/sys/commands/request_id=+`)
      mqtt.subscribe(`$oc/devices/${deviceId}/sys/properties/set/#`)
    })
  },

  reportOnline() {
    mqtt.publish({
      relay: this.data.relay,
      beep: this.data.beep,
      temp: this.data.temp === '--' ? 0 : this.data.temp,
      humi: this.data.humi === '--' ? 0 : this.data.humi,
      rain: this.data.rain,
      person: this.data.person || '设备上线'
    })
    this.addLog('success', '设备上线状态已上报')
  },

  addLog(type, message) {
    const logs = [{ type, message, time: new Date().toLocaleTimeString() }, ...this.data.logs].slice(0, 20)
    this.setData({ logs })
    wx.setStorageSync('iotLogs', logs)
  },

  loadLogs() {
    const logs = wx.getStorageSync('iotLogs') || []
    this.setData({ logs })
  },

  clearLogs() {
    this.setData({ logs: [] })
    wx.removeStorageSync('iotLogs')
  },

  formatTime() {
    const now = new Date()
    return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`
  },

  refreshData() {
    this.setData({ loading: true, restStatus: 'connecting' })

    getDeviceShadow((err, data) => {
      if (err) {
        this.addLog('error', err.message)
        this.setData({ restStatus: 'failed', loading: false })
        return
      }

      const { temp, humi, relay, beep, rain, person } = parseDeviceData(data)
      this.setData({
        temp,
        humi,
        relay,
        beep,
        rain,
        person,
        lastUpdate: this.formatTime(),
        restStatus: 'connected',
        loading: false
      })

      this.addLog('success', `数据刷新成功 - 温度: ${temp}°C, 湿度: ${humi}%`)
    })
  },

  updateDeviceData(props) {
    const updates = {}
    if (props.temp !== undefined) updates.temp = props.temp
    if (props.temperature !== undefined) updates.temp = props.temperature
    if (props.humi !== undefined) updates.humi = props.humi
    if (props.humidity !== undefined) updates.humi = props.humidity
    if (props.relay !== undefined) updates.relay = props.relay
    if (props.beep !== undefined) updates.beep = props.beep
    if (props.buzzer !== undefined) updates.beep = props.buzzer
    if (props.rain !== undefined) updates.rain = props.rain
    if (props.person !== undefined) updates.person = props.person
    
    if (Object.keys(updates).length > 0) {
      updates.lastUpdate = this.formatTime()
      this.setData(updates)
    }
  },

  onRelayChange(e) {
    if (this.data.relaySending) return
    
    const value = e.detail.value ? 1 : 0
    this.setData({ relay: value, relaySending: true, loading: true })
    this.addLog('info', `继电器${value ? '开启' : '关闭'}`)

    mqtt.publish({ relay: value })
    
    sendCommand('relay', { relay: value }, (err, res) => {
      if (err) {
        console.log('[ERR] 命令下发失败:', err.message)
        this.addLog('error', '命令下发失败: ' + err.message)
      } else {
        console.log('[OK] 命令下发成功:', res)
        this.addLog('success', '命令下发成功')
      }
    })
    
    setTimeout(() => {
      this.setData({ relaySending: false, loading: false })
    }, 1000)
  },

  onBeepChange(e) {
    if (this.data.beepSending) return
    
    const value = e.detail.value ? 1 : 0
    this.setData({ beep: value, beepSending: true, loading: true })
    this.addLog('info', `蜂鸣器${value ? '开启' : '关闭'}`)

    mqtt.publish({ beep: value })
    
    sendCommand('beep', { beep: value }, (err, res) => {
      if (err) {
        console.log('[ERR] 命令下发失败:', err.message)
        this.addLog('error', '命令下发失败: ' + err.message)
      } else {
        console.log('[OK] 命令下发成功:', res)
        this.addLog('success', '命令下发成功')
      }
    })
    
    setTimeout(() => {
      this.setData({ beepSending: false, loading: false })
    }, 1000)
  },

  startAutoRefresh() {
    if (this.timer) {
      this.stopTimer()
      this.addLog('info', '已停止自动刷新')
      return
    }

    this.addLog('info', '开始自动刷新 (5秒间隔)')
    this.timer = setInterval(() => {
      getDeviceShadow((err, data) => {
        if (err) {
          this.addLog('error', '自动刷新失败: ' + err.message)
          return
        }
        const { temp, humi, relay, beep, rain, person } = parseDeviceData(data)
        this.setData({ temp, humi, relay, beep, rain, person, lastUpdate: this.formatTime() })
      })
    }, 5000)
  },

  stopTimer() {
    if (this.timer) {
      clearInterval(this.timer)
      this.timer = null
    }
  }
})