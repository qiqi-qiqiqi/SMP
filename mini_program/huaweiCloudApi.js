const config = require('./config')

const REQUEST_TIMEOUT = 15000

let cachedToken = null
let tokenExpireTime = 0

function getToken(callback) {
  const now = Date.now()
  if (cachedToken && now < tokenExpireTime) {
    callback(null, cachedToken)
    return
  }

  const { accountName, iamUser, iamPwd, region, iamEndpoint } = config

  if (!accountName || !iamUser || !iamPwd) {
    callback(new Error('请先配置华为云账号信息'), null)
    return
  }

  wx.request({
    url: `${iamEndpoint}/v3/auth/tokens`,
    method: 'POST',
    timeout: REQUEST_TIMEOUT,
    header: { 'Content-Type': 'application/json' },
    data: {
      auth: {
        identity: {
          methods: ['password'],
          password: {
            user: { name: iamUser, password: iamPwd, domain: { name: accountName } }
          }
        },
        scope: { project: { name: region } }
      }
    },
    success: (res) => {
      if (res.statusCode === 200 || res.statusCode === 201) {
        cachedToken = res.header['X-Subject-Token']
        tokenExpireTime = now + 3600 * 1000
        callback(null, cachedToken)
      } else {
        callback(new Error(`获取Token失败 [${res.statusCode}]`), null)
      }
    },
    fail: (err) => callback(new Error(`获取Token失败: ${err.errMsg || JSON.stringify(err)}`), null)
  })
}

function getDeviceShadow(callback) {
  const { projectId, deviceId, iotEndpoint } = config

  if (!projectId || !deviceId) {
    callback(new Error('请先配置项目ID和设备ID'), null)
    return
  }

  getToken((err, token) => {
    if (err) {
      callback(err, null)
      return
    }

    wx.request({
      url: `${iotEndpoint}/v5/iot/${projectId}/devices/${deviceId}/shadow`,
      method: 'GET',
      timeout: REQUEST_TIMEOUT,
      header: { 'Content-Type': 'application/json', 'X-Auth-Token': token },
      success: (res) => {
        if (res.statusCode === 200) {
          callback(null, res.data)
        } else {
          cachedToken = null
          callback(new Error(`获取设备数据失败 [${res.statusCode}]`), null)
        }
      },
      fail: (err) => {
        cachedToken = null
        callback(new Error(`获取设备数据失败: ${err.errMsg || JSON.stringify(err)}`), null)
      }
    })
  })
}

function sendCommand(commandName, params, callback) {
  const { projectId, deviceId, iotEndpoint } = config

  if (!projectId || !deviceId) {
    callback(new Error('请先配置项目ID和设备ID'), null)
    return
  }

  getToken((err, token) => {
    if (err) {
      callback(err, null)
      return
    }

    wx.request({
      url: `${iotEndpoint}/v5/iot/${projectId}/devices/${deviceId}/commands`,
      method: 'POST',
      timeout: REQUEST_TIMEOUT,
      header: { 'Content-Type': 'application/json', 'X-Auth-Token': token },
      data: {
        service_id: '1234',
        command_name: commandName,
        paras: params || {}
      },
      success: (res) => {
        if (res.statusCode === 200 || res.statusCode === 201) {
          callback(null, res.data)
        } else {
          cachedToken = null
          callback(new Error(`下发命令失败 [${res.statusCode}]: ${res.data?.error_message || '未知错误'}`), null)
        }
      },
      fail: (err) => {
        cachedToken = null
        callback(new Error(`下发命令失败: ${err.errMsg || JSON.stringify(err)}`), null)
      }
    })
  })
}

function parseDeviceData(rawData) {
  let temp = '--'
  let humi = '--'
  let relay = 0
  let beep = 0
  let rain = 0
  let person = '--'
  let rawProperties = null
  
  try {
    if (rawData && rawData.shadow && rawData.shadow[0]) {
      rawProperties = rawData.shadow[0].reported.properties
      if (rawProperties) {
        if (rawProperties.temperature !== undefined) temp = rawProperties.temperature
        else if (rawProperties.temp !== undefined) temp = rawProperties.temp
        if (rawProperties.humidity !== undefined) humi = rawProperties.humidity
        else if (rawProperties.humi !== undefined) humi = rawProperties.humi
        if (rawProperties.relay !== undefined) relay = rawProperties.relay
        if (rawProperties.beep !== undefined) beep = rawProperties.beep
        else if (rawProperties.buzzer !== undefined) beep = rawProperties.buzzer
        if (rawProperties.rain !== undefined) rain = rawProperties.rain
        if (rawProperties.person !== undefined) person = rawProperties.person
      }
    }
  } catch (e) {
    console.warn('解析设备数据失败:', e)
  }
  
  return { temp, humi, relay, beep, rain, person, rawProperties }
}

module.exports = { config, getToken, getDeviceShadow, sendCommand, parseDeviceData }