'use strict';

const config = require('./config');
const logger = require('./utils/logger');
const history = require('./history');
const { askGemini } = require('./ai/gemini');
const { getHelpMessage } = require('./commands/help');
const { getOTPInfo } = require('./commands/otp');
const {
  sendText,
  sendTextWithTyping,
} = require('./services/whatsapp');

/**
 * ── Per-phone in-memory welcome lock ──
 * Prevents TOCTOU race condition: if two messages from the same user
 * arrive near-simultaneously (in separate messages.upsert events),
 * both could pass the history.isWelcomeSent() check before either
 * calls history.markWelcomeSent().
 *
 * The in-memory lock is checked FIRST (fast, synchronous), before the
 * persistent file-based check. Once locked, no other handler invocation
 * for the same phone can enter the welcome block.
 *
 * The lock auto-clears when the phone leaves the welcome block.
 */
const welcomeLocks = new Set();

/**
 * Welcome message — sent ONLY ONCE per user, even across bot restarts.
 * Professional, warm, and service-oriented like WhatsApp Business.
 */
const WELCOME_MSG =
  'Halo! Terima kasih sudah menghubungi Warungio. 👋\n\n' +
  'Saya Admin Warungio, asisten resmi yang siap membantu Anda seputar:\n' +
  '• Informasi aplikasi dan fitur Warungio\n' +
  '• Cara pemesanan dan pembayaran\n' +
  '• Bantuan penggunaan toko online\n' +
  '• Info promo dan layanan terbaru\n\n' +
  'Silakan tanyakan apa pun yang Anda butuhkan. Saya akan dengan senang hati membantu! 🙌';

/**
 * Local fallback assistant — answers common questions when AI is disabled.
 * @param {string} message
 * @returns {string|null}
 */
function fallbackAssistant(message) {
  const lower = message.toLowerCase().trim();

  // Help / Bantuan
  if (/^(bantuan|help|tolong|menu|command|fitur\s*bot|bot\s*fitur)/i.test(lower)) {
    return getHelpMessage();
  }

  // OTP diagnostic
  if (/^(otp|kode\s*otp|verifikasi|tidak\s*terima\s*otp|otp\s*tidak\s*sampai|email\s*otp|masalah\s*otp)/i.test(lower)) {
    return getOTPInfo();
  }

  // Greetings
  if (/^(halo|hai|hi|hey|pagi|siang|sore|malam|selamat\s*(pagi|siang|sore|malam)|test|tes|assalamualaikum|assalamu'alaikum)/i.test(lower)) {
    return 'Halo! Ada yang bisa saya bantu seputar Warungio hari ini?';
  }

  // How are you
  if (/apa\s*kabar|bagaimana\s*kabar|kamu\s*sehat|gimana\s*kabar/i.test(lower)) {
    return 'Alhamdulillah baik. Terima kasih sudah bertanya! Ada yang bisa saya bantu seputar Warungio?';
  }

  // Thank you
  if (/^(terima\s*kasih|makasih|thanks|thank\s*you|trimakasih|trims|tq)$/i.test(lower)) {
    return 'Sama-sama! Senang bisa membantu. Jika ada pertanyaan lain, jangan ragu untuk menghubungi lagi ya.';
  }

  // Goodbye
  if (/^(selamat\s*tinggal|dadah|bye|sampai\s*jumpa|dada|salam)/i.test(lower)) {
    return 'Sampai jumpa! Terima kasih telah menghubungi Warungio. Semoga harimu menyenangkan!';
  }

  // Who are you
  if (/siapa\s*kamu|kamu\s*siapa|bot\s*apa|perkenalkan/i.test(lower)) {
    return 'Saya adalah Asisten Virtual Warungio, chatbot resmi yang siap membantu Anda seputar aplikasi Warungio — platform hyperlocal marketplace untuk UMKM di Indonesia.';
  }

  // What is Warungio
  if (/apa\s*itu\s*warungio|warungio\s*apa|tentang\s*warungio|warungio\s*itu\s*apa/i.test(lower)) {
    return 'Warungio adalah platform marketplace hyperlocal yang menghubungkan pembeli dengan UMKM terdekat. Melalui Warungio, Anda bisa membeli berbagai kebutuhan sehari-hari, memesan antar menggunakan Grab/Gojek, dan melakukan pembayaran secara digital. Warungio juga menyediakan dashboard khusus untuk penjual agar bisa mengelola toko mereka dengan mudah.';
  }

  // Features
  if (/fitur\s*apa|apa\s*saja\s*fitur|keunggulan|bisa\s*apa\s*aja/i.test(lower)) {
    return 'Warungio memiliki beberapa fitur utama:\n\n1. Pembelian produk secara online dari UMKM terdekat\n2. Pengiriman menggunakan Grab, Gojek, atau Mitra Pengiriman Warungio\n3. Pembayaran digital melalui Midtrans, QRIS, E-Wallet, dan metode lainnya\n4. Sistem poin dan loyalitas untuk pembeli\n5. Dashboard lengkap untuk penjual mengelola toko, stok, dan laporan penjualan\n6. Notifikasi realtime untuk setiap update pesanan\n\nAda fitur yang ingin Anda tanyakan lebih lanjut?';
  }

  // How to order
  if (/cara\s*(pesan|beli|order|memesan|membeli)|bagaimana\s*cara\s*(pesan|beli|order)|gimana\s*cara/i.test(lower)) {
    return 'Untuk memesan di Warungio, caranya mudah:\n\n1. Buka link toko Warungio yang Anda terima\n2. Pilih produk yang diinginkan\n3. Klik "Tambah ke Keranjang"\n4. Lanjut ke halaman checkout dan isi data pengiriman\n5. Pilih metode pembayaran\n6. Konfirmasi pesanan\n\nSetelah itu Anda akan mendapatkan notifikasi realtime mengenai status pesanan. Ada yang bisa saya bantu lebih lanjut?';
  }

  // Payment
  if (/pembayaran|bayar|payment|metode\s*pembayaran|cara\s*bayar/i.test(lower) && !/kerusakan|rusak|error|bug|masalah/i.test(lower)) {
    return 'Warungio mendukung berbagai metode pembayaran:\n\n- Pembayaran Digital: Midtrans, QRIS, E-Wallet (GoPay, OVO, DANA, dll)\n- Transfer Bank: BCA, Mandiri, BRI, BNI, dan bank lainnya\n- Tunai: Tersedia untuk pengiriman dengan Mitra Warungio\n\nPilih metode yang paling nyaman untuk Anda! Ada yang ingin ditanyakan lagi?';
  }

  // Contact
  if (/kontak|hubungi|customer\s*service|cust\s*service|cs\s*warungio|nomor\s*(cs|help|support)/i.test(lower)) {
    return 'Untuk pertanyaan lebih lanjut, Anda bisa menghubungi tim Warungio melalui:\n- Email: warungio.id@gmail.com\n- WhatsApp: wa.me/6287833847895\n- Atau melalui chat ini, saya siap membantu!';
  }

  // Features in development
  if (/laporan|export\s*pdf|pdf|excel|analitik|grafik|ai\s*scan|ocr|computer\s*vison|smart\s*scan|pos\s*offline/i.test(lower)) {
    return 'Fitur yang Anda tanyakan masih dalam tahap pengembangan dan peningkatan keamanan. Tim Warungio sedang bekerja keras untuk menghadirkan fitur tersebut segera. Nantikan update selanjutnya ya! Ada yang bisa saya bantu yang lain?';
  }

  // Multimedia
  if (/gambar|image|photo|foto|media|upload/i.test(lower)) {
    return 'Saya bisa menerima dan membalas berbagai jenis pesan multimedia seperti gambar, dokumen, audio, video, dan lokasi. Silakan kirimkan apa yang ingin Anda bagikan!';
  }

  if (/lokasi|location|alamat|maps|dimana/i.test(lower)) {
    return 'Saya bisa menerima dan mengirim informasi lokasi. Silakan bagikan lokasi Anda atau tanyakan alamat toko Warungio terdekat!';
  }

  return null;
}

/**
 * Describe multimedia content for AI context.
 */
function describeMultimedia(content) {
  if (!content || content.type === 'text') return '';

  switch (content.type) {
    case 'image':
      return '[Pengguna mengirim GAMBAR: ' + (content.caption || 'tanpa caption') + ']';
    case 'document':
      return '[Pengguna mengirim DOKUMEN: ' + (content.media?.fileName || 'file') + ' (' + (content.media?.mimetype || 'unknown') + ')]';
    case 'audio':
      return content.media?.ptt
        ? '[Pengguna mengirim PESAN SUARA: ' + (content.media?.seconds || '?') + ' detik]'
        : '[Pengguna mengirim AUDIO: ' + (content.media?.seconds || '?') + ' detik]';
    case 'video':
      return '[Pengguna mengirim VIDEO: ' + (content.caption || 'tanpa caption') + ' (' + (content.media?.seconds || '?') + ' detik)]';
    case 'location':
      return '[Pengguna mengirim LOKASI: ' + (content.location?.name || '') + ' (' + (content.location?.latitude || '?') + ', ' + (content.location?.longitude || '?') + ')]';
    case 'contact':
      return '[Pengguna membagikan KONTAK: ' + (content.contact?.displayName || 'Kontak') + ']';
    case 'sticker':
      return '[Pengguna mengirim STIKER]';
    case 'interactive':
      return '[Pengguna memilih: ' + content.text + ']';
    default:
      return '[Pesan multimedia: ' + content.type + ']';
  }
}

/**
 * Respond to multimedia messages.
 */
async function handleMultimediaMessage(sock, jid, content) {
  switch (content.type) {
    case 'location':
      await sendText(sock, jid, 'Lokasi Anda telah saya terima. Apakah Anda ingin mengetahui Warungio terdekat? Ketik "cari warung" untuk mencari.');
      return;

    case 'image':
      await sendText(sock, jid, 'Terima kasih! Saya sudah menerima gambar Anda. ' + (content.caption ? 'Catatan: "' + content.caption + '"' : 'Ada yang bisa saya bantu?'));
      return;

    case 'audio':
      await sendText(sock, jid, 'Pesan suara Anda telah saya terima (' + (content.media?.seconds || 'beberapa') + ' detik). Ada yang bisa saya bantu?');
      return;

    case 'video':
      await sendText(sock, jid, 'Video Anda telah saya terima. ' + (content.caption ? 'Catatan: "' + content.caption + '"' : 'Ada yang bisa saya bantu?'));
      return;

    case 'document':
      await sendText(sock, jid, 'Dokumen "' + (content.media?.fileName || 'file') + '" telah saya terima. Ada yang bisa saya bantu?');
      return;

    case 'contact':
      await sendText(sock, jid, 'Kontak ' + (content.contact?.displayName || 'tersebut') + ' telah saya terima.');
      return;

    case 'sticker':
      await sendText(sock, jid, 'Stiker yang lucu! Ada yang bisa saya bantu?');
      return;

    default:
      await sendText(sock, jid, 'Pesan Anda telah saya terima. Silakan kirim teks untuk pertanyaan seputar Warungio.');
      return;
  }
}

/**
 * Process an incoming message with full multimedia support.
 */
async function handleMessage(sock, jid, text, content) {
  const phone = jid.split('@')[0];
  const msgContent = content || { type: 'text', text };

  // Save user message
  const displayText = text || msgContent.text || '[Pesan multimedia]';
  history.saveMessage(phone, 'user', displayText);

  try {
    // ── Welcome message: ONLY ONCE per user ──
    // Uses TWO layers of protection:
    // 1. In-memory Set (fast, prevents TOCTOU race)
    // 2. Persistent file check (survives bot restart)
    if (!welcomeLocks.has(phone) && !history.isWelcomeSent(phone)) {
      welcomeLocks.add(phone);
      try {
        history.markWelcomeSent(phone);
        history.saveMessage(phone, 'bot', WELCOME_MSG);
        await sendTextWithTyping(sock, jid, WELCOME_MSG, 2000);
      } finally {
        welcomeLocks.delete(phone);
      }
      return;
    }

    // ── Multimedia message handling ──
    if (msgContent.type !== 'text') {
      if (config.aiEnabled) {
        const mediaDescription = describeMultimedia(msgContent);
        const aiContext = mediaDescription + '\n\nPesan pengguna: ' + text;
        const aiResponse = await askGemini(phone, aiContext);

        if (aiResponse) {
          await sendTextWithTyping(sock, jid, aiResponse, 1000);
          return;
        }
      }

      await handleMultimediaMessage(sock, jid, msgContent);
      return;
    }

    // ── Text message with AI ──
    if (config.aiEnabled) {
      const aiResponse = await askGemini(phone, text);
      if (aiResponse) {
        await sendTextWithTyping(sock, jid, aiResponse, 1000);
        return;
      }
    }

    // ── Fallback assistant (used when AI disabled OR AI fails) ──
    const fallbackResponse = fallbackAssistant(text);
    if (fallbackResponse) {
      history.saveMessage(phone, 'bot', fallbackResponse);
      await sendTextWithTyping(sock, jid, fallbackResponse, 1000);
      return;
    }

    // ── Generic fallback ──
    const genericResponse =
      'Terima kasih atas pesannya. Saat ini saya masih dalam tahap pengembangan untuk fitur yang lebih lengkap. ' +
      'Namun, saya bisa membantu menjawab pertanyaan seputar:\n\n' +
      '• Informasi tentang Warungio\n' +
      '• Cara pemesanan dan pembayaran\n' +
      '• Fitur-fitur yang tersedia\n\n' +
      'Silakan tanyakan apa yang ingin Anda ketahui, atau hubungi tim Warungio melalui email warungio.id@gmail.com untuk pertanyaan lebih lanjut.';

    history.saveMessage(phone, 'bot', genericResponse);
    await sendTextWithTyping(sock, jid, genericResponse, 1000);
  } catch (err) {
    logger.error('Handler error untuk ' + phone + ': ' + err.message);
    await sendText(sock, jid, 'Maaf, terjadi kesalahan teknis. Silakan coba lagi nanti.');
  }
}

module.exports = { handleMessage };
