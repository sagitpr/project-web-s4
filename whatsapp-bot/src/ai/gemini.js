'use strict';

const fetch = require('node-fetch');
const config = require('../config');
const logger = require('../utils/logger');
const history = require('../history');

/**
 * System instruction that defines the chatbot's persona.
 * Professional customer service agent — never identifies as AI.
 */
const SYSTEM_INSTRUCTION = `Anda adalah Admin Customer Service Warungio — platform hyperlocal marketplace untuk UMKM di Indonesia.

IDENTITAS:
- Anda adalah staff customer service Warungio yang ramah, profesional, dan berpengalaman.
- Gunakan bahasa Indonesia yang natural, sopan, dan mudah dipahami.
- Jawab dengan singkat, padat, dan langsung ke inti (maksimal 3-4 paragraf).
- JANGAN PERNAH mengatakan bahwa Anda adalah AI, chatbot, asisten virtual, atau model bahasa.
- JANGAN PERNAH menggunakan format markdown, simbol khusus, atau emoji berlebihan dalam balasan.

PENGETAHUAN TENTANG WARUNGIO:
Warungio adalah platform marketplace hyperlocal yang menghubungkan pembeli dengan UMKM terdekat. Fitur utama meliputi: pembelian produk secara online, pemesanan antar menggunakan Grab/Gojek/Mitra Pengiriman Warungio, pembayaran digital melalui Midtrans/QRIS/transfer bank/tunai, sistem poin dan loyalitas untuk pembeli, serta dashboard lengkap untuk penjual mengelola toko, stok, dan laporan penjualan.

KEMAMPUAN MULTIMEDIA:
- Anda bisa menerima dan merespons gambar, dokumen, audio, video, lokasi, dan kontak.
- Jika pelanggan mengirim gambar dengan pertanyaan, jawablah dengan membantu.
- Jika pelanggan mengirim lokasi, respons dengan informasi yang relevan.
- Jika pelanggan mengirim dokumen atau file, akui penerimaan dan tawarkan bantuan.

ATURAN PERCAKAPAN:
1. Jika ditanya fitur yang sudah tersedia, jelaskan dengan jelas dan antusias.
2. Jika ditanya fitur yang belum tersedia, akui dengan sopan bahwa fitur tersebut masih dalam pengembangan tanpa perlu menjelaskan detail teknis.
3. Jika pelanggan bertanya di luar konteks Warungio, arahkan kembali ke topik secara alami.
4. Jangan pernah menyebutkan bahwa Anda adalah AI, bot, atau sistem otomatis.
5. Jangan pernah meminta maaf tanpa alasan yang jelas.
6. Jika pelanggan bertanya tentang status aplikasi, berikan jawaban positif dan profesional.`;

/**
 * Build a conversation context array from history.
 * @param {string} phone
 * @returns {Array} Contents array for Gemini API
 */
function buildContext(phone) {
  const messages = history.getConversation(phone);
  const contents = [];

  // Add up to last 10 exchanges for context
  const recentHistory = messages.slice(-20);

  for (const msg of recentHistory) {
    if (msg.role === 'user') {
      contents.push({ role: 'user', parts: [{ text: msg.text }] });
    } else if (msg.role === 'bot') {
      contents.push({ role: 'model', parts: [{ text: msg.text }] });
    }
  }

  return contents;
}

/**
 * Call Gemini REST API and return the generated text.
 * @param {string} phone - Sender's phone number
 * @param {string} message - User's message (text or media description)
 * @param {Object} [options] - Additional options
 * @param {string} [options.mediaType] - Type of media if applicable
 * @param {string} [options.mediaData] - Base64-encoded media data for vision (future)
 * @returns {Promise<string|null>} AI response or null on failure
 */
async function askGemini(phone, message, options = {}) {
  const { geminiApiKey, geminiModel, geminiTemperature, geminiMaxTokens } = config;

  if (!geminiApiKey || geminiApiKey === 'your_gemini_api_key_here') {
    logger.error('GEMINI_API_KEY tidak dikonfigurasi');
    return null;
  }

  try {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${geminiModel}:generateContent?key=${geminiApiKey}`;

    const contextHistory = buildContext(phone);

    // Build the parts array — include image data if provided for vision models
    const userParts = [{ text: message }];

    // Build request
    const requestBody = {
      contents: [
        {
          role: 'user',
          parts: [{ text: SYSTEM_INSTRUCTION }],
        },
        {
          role: 'model',
          parts: [{ text: 'Baik, saya akan mengikuti panduan tersebut sebagai Asisten Virtual Warungio.' }],
        },
        ...contextHistory,
        {
          role: 'user',
          parts: userParts,
        },
      ],
      generationConfig: {
        temperature: geminiTemperature,
        maxOutputTokens: geminiMaxTokens,
        topP: 0.9,
        topK: 40,
      },
    };

    // Log request type
    const mediaLabel = options.mediaType ? ` [media: ${options.mediaType}]` : '';
    logger.info(`Mengirim pertanyaan ke Gemini untuk ${phone}${mediaLabel}...`);

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorText = await response.text();
      logger.error(`Gemini API error (${response.status}): ${errorText}`);
      return null;
    }

    const data = await response.json();

    // Extract text from response
    const candidate = data.candidates?.[0];
    if (!candidate) {
      logger.error('Gemini: no candidates in response');
      return null;
    }

    const text = candidate.content?.parts?.[0]?.text;
    if (!text) {
      logger.error('Gemini: no text in response parts');
      return null;
    }

    // Save AI response to history
    history.saveMessage(phone, 'bot', text);
    logger.success(`Jawaban dari Gemini diterima untuk ${phone}${mediaLabel}`);

    return text.trim();
  } catch (err) {
    logger.error(`Gemini request gagal: ${err.message}`);
    return null;
  }
}

module.exports = { askGemini };
