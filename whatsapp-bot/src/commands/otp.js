'use strict';

const config = require('../config');
const logger = require('../utils/logger');

/**
 * OTP diagnostic information for debugging delivery issues.
 * @returns {string}
 */
function getOTPInfo() {
  return (
    `🔐 *Sistem OTP Warungio*\n\n` +
    `OTP (One-Time Password) digunakan untuk:\n` +
    `• Verifikasi akun baru (Register)\n` +
    `• Verifikasi login jika akun belum aktif\n` +
    `• Reset password\n` +
    `• Keamanan perubahan data sensitif\n\n` +
    `*Jika Anda tidak menerima OTP:*\n` +
    `1️⃣ Periksa folder *Spam* atau *Promosi* di email\n` +
    `2️⃣ Pastikan email yang didaftarkan benar\n` +
    `3️⃣ Klik *"Kirim Ulang OTP"* setelah 60 detik\n` +
    `4️⃣ Jika masih belum diterima, hubungi warungio.id@gmail.com\n\n` +
    `*Penting:*\n` +
    `• Kode OTP berlaku ${config.otpExpiryMinutes || 15} menit\n` +
    `• Jangan bagikan kode OTP kepada siapa pun\n` +
    `• Tim Warungio tidak akan pernah meminta kode OTP Anda\n\n` +
    `Ada yang bisa saya bantu?`
  );
}

module.exports = { getOTPInfo };
