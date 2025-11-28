/**
 * 前端消息加密/解密工具
 * 使用 crypto-js 实现 AES 加密
 */
import CryptoJS from 'crypto-js'

/**
 * AES 加密工具类
 */
export class AESCrypto {
  constructor(masterKey) {
    this.masterKey = masterKey
  }


  /**
   * 加密消息
   * @param {Object} data - 要加密的数据对象
   * @returns {Promise<Object>} { success: boolean, encrypted: string, error: string }
   */
  async encrypt(data) {
    try {
      // 1. 将数据转换为 JSON 字符串
      const jsonStr = JSON.stringify(data)
      // 2. 使用 AES 加密（CryptoJS 自动处理 Base64）
      const encrypted = CryptoJS.AES.encrypt(jsonStr, this.masterKey).toString()
      return { success: true, encrypted, error: '' }
    } catch (e) {
      console.error('Encryption error:', e)
      return { success: false, encrypted: '', error: e.message }
    }
  }

  /**
   * 解密消息
   * @param {string} encryptedBase64 - 加密的字符串
   * @returns {Promise<Object>} { success: boolean, data: Object, error: string }
   */
  async decrypt(encryptedBase64) {
    try {
      // 1. 使用 AES 解密
      const decrypted = CryptoJS.AES.decrypt(encryptedBase64, this.masterKey)
      // 2. 转换为 UTF-8 字符串
      const jsonStr = decrypted.toString(CryptoJS.enc.Utf8)
      
      if (!jsonStr) {
        console.error('Decryption failed: invalid key or corrupted data')
        return { success: false, data: null, error: 'Decryption failed: invalid key or corrupted data' }
      }
      
      // 3. 解析 JSON
      const data = JSON.parse(jsonStr)
      
      return { success: true, data }
    } catch (e) {
      console.error('Full error:', e)
      return { success: false, data: null, error: e.message }
    }
  }
}
