'use strict';

/**
 * Generate interactive help message for the chatbot.
 * @param {string} [phone] - User's phone number for personalized help
 * @returns {string}
 */
function getHelpMessage(phone = '') {
  return (
    `🤖 *Asisten Virtual Warungio — Bantuan*\n\n` +
    `Saya adalah chatbot resmi Warungio. Berikut yang bisa saya lakukan:\n\n` +
    `📝 *Pertanyaan Umum*\n` +
    `• Tanya tentang Warungio, fitur, cara pesan, pembayaran\n` +
    `• Kontak dan informasi toko\n` +
    `• Bantuan penggunaan aplikasi\n\n` +
    `🖼️ *Pesan Multimedia*\n` +
    `• Kirim *gambar* — Saya bisa melihat dan meresponsnya\n` +
    `• Kirim *dokumen* — Saya bisa menerima file\n` +
    `• Kirim *pesan suara* — Saya bisa mendengarkan\n` +
    `• Kirim *video* — Saya bisa menerimanya\n` +
    `• Kirim *lokasi* — Saya bisa membalas dengan lokasi\n` +
    `• Bagikan *kontak* — Saya bisa menyimpannya\n\n` +
    `💡 *Tips Penggunaan*\n` +
    `• Ketik *"Halo"* untuk memulai percakapan\n` +
    `• Tanyakan *"Fitur Warungio"* untuk info lengkap\n` +
    `• Kirim *"Bantuan"* atau *"Help"* untuk pesan ini lagi\n` +
    `• Kirim *"Lokasi saya"* untuk berbagi lokasi\n\n` +
    `Ada yang bisa saya bantu? 😊`
  );
}

module.exports = { getHelpMessage };
