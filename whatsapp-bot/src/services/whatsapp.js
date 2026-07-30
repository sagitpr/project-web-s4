'use strict';

const logger = require('../utils/logger');

/**
 * Send a text message to a WhatsApp JID.
 * @param {import('@whiskeysockets/baileys').WASocket} sock
 * @param {string} jid
 * @param {string} text
 * @returns {Promise<Object|null>}
 */
async function sendText(sock, jid, text) {
  try {
    const sent = await sock.sendMessage(jid, { text });
    logger.success(`Pesan terkirim ke ${jid.split('@')[0]}`);
    return sent;
  } catch (err) {
    logger.error(`Gagal mengirim pesan ke ${jid.split('@')[0]}: ${err.message}`);
    return null;
  }
}

/**
 * Send text with typing indicator.
 * @param {import('@whiskeysockets/baileys').WASocket} sock
 * @param {string} jid
 * @param {string} text
 * @param {number} typingMs
 * @returns {Promise<Object|null>}
 */
async function sendTextWithTyping(sock, jid, text, typingMs = 1500) {
  try {
    await sock.sendPresenceUpdate('composing', jid);
    await new Promise((resolve) => setTimeout(resolve, typingMs));
    const result = await sendText(sock, jid, text);
    await sock.sendPresenceUpdate('paused', jid);
    return result;
  } catch (err) {
    logger.error(`sendWithTyping error: ${err.message}`);
    return sendText(sock, jid, text);
  }
}

/**
 * Send an image message with optional caption.
 * @param {import('@whiskeysockets/baileys').WASocket} sock
 * @param {string} jid
 * @param {Buffer|string} image - Image buffer or URL
 * @param {string} caption - Optional caption text
 * @returns {Promise<Object|null>}
 */
async function sendImage(sock, jid, image, caption = '') {
  try {
    const sent = await sock.sendMessage(jid, {
      image,
      caption: caption || undefined,
    });
    logger.success(`Gambar terkirim ke ${jid.split('@')[0]}`);
    return sent;
  } catch (err) {
    logger.error(`Gagal mengirim gambar: ${err.message}`);
    return null;
  }
}

/**
 * Send a document/file message.
 * @param {import('@whiskeysockets/baileys').WASocket} sock
 * @param {string} jid
 * @param {Buffer|string} document - Document buffer or URL
 * @param {string} filename - Display filename
 * @param {string} [mimetype] - MIME type (default: application/pdf)
 * @param {string} [caption] - Optional caption
 * @returns {Promise<Object|null>}
 */
async function sendDocument(sock, jid, document, filename, mimetype = 'application/pdf', caption = '') {
  try {
    const sent = await sock.sendMessage(jid, {
      document,
      mimetype,
      fileName: filename,
      caption: caption || undefined,
    });
    logger.success(`Dokumen terkirim ke ${jid.split('@')[0]}: ${filename}`);
    return sent;
  } catch (err) {
    logger.error(`Gagal mengirim dokumen: ${err.message}`);
    return null;
  }
}

/**
 * Send an audio message.
 * @param {import('@whiskeysockets/baileys').WASocket} sock
 * @param {string} jid
 * @param {Buffer|string} audio - Audio buffer or URL
 * @param {boolean} [ptt] - True for voice note (push-to-talk)
 * @returns {Promise<Object|null>}
 */
async function sendAudio(sock, jid, audio, ptt = false) {
  try {
    const sent = await sock.sendMessage(jid, {
      audio,
      mimetype: 'audio/mp4',
      ptt,
    });
    logger.success(`Audio terkirim ke ${jid.split('@')[0]}`);
    return sent;
  } catch (err) {
    logger.error(`Gagal mengirim audio: ${err.message}`);
    return null;
  }
}

/**
 * Send a video message with optional caption.
 * @param {import('@whiskeysockets/baileys').WASocket} sock
 * @param {string} jid
 * @param {Buffer|string} video - Video buffer or URL
 * @param {string} [caption] - Optional caption
 * @returns {Promise<Object|null>}
 */
async function sendVideo(sock, jid, video, caption = '') {
  try {
    const sent = await sock.sendMessage(jid, {
      video,
      caption: caption || undefined,
    });
    logger.success(`Video terkirim ke ${jid.split('@')[0]}`);
    return sent;
  } catch (err) {
    logger.error(`Gagal mengirim video: ${err.message}`);
    return null;
  }
}

/**
 * Send a location message.
 * @param {import('@whiskeysockets/baileys').WASocket} sock
 * @param {string} jid
 * @param {number} latitude
 * @param {number} longitude
 * @param {string} [name] - Location name
 * @param {string} [address] - Address text
 * @returns {Promise<Object|null>}
 */
async function sendLocation(sock, jid, latitude, longitude, name = '', address = '') {
  try {
    const sent = await sock.sendMessage(jid, {
      location: {
        degreesLatitude: latitude,
        degreesLongitude: longitude,
        name: name || undefined,
        address: address || undefined,
      },
    });
    logger.success(`Lokasi terkirim ke ${jid.split('@')[0]}`);
    return sent;
  } catch (err) {
    logger.error(`Gagal mengirim lokasi: ${err.message}`);
    return null;
  }
}

/**
 * Send a contact vCard message.
 * @param {import('@whiskeysockets/baileys').WASocket} sock
 * @param {string} jid
 * @param {string} contactName
 * @param {string} contactPhone
 * @returns {Promise<Object|null>}
 */
async function sendContact(sock, jid, contactName, contactPhone) {
  try {
    const vcard =
      'BEGIN:VCARD\n' +
      'VERSION:3.0\n' +
      `FN:${contactName}\n` +
      `TEL;TYPE=CELL:${contactPhone}\n` +
      'END:VCARD';

    const sent = await sock.sendMessage(jid, {
      contacts: {
        displayName: contactName,
        contacts: [{ vcard }],
      },
    });
    logger.success(`Kontak terkirim ke ${jid.split('@')[0]}: ${contactName}`);
    return sent;
  } catch (err) {
    logger.error(`Gagal mengirim kontak: ${err.message}`);
    return null;
  }
}

/**
 * Extract message type and content from a received message.
 * Returns { type, text, media, location, caption } or null.
 * @param {Object} msg - Baileys message object
 * @returns {Object|null}
 */
function extractMessageContent(msg) {
  if (!msg.message) return null;

  const m = msg.message;

  // Text message
  if (m.conversation) {
    return { type: 'text', text: m.conversation };
  }

  // Extended text (includes URL preview, mentions)
  if (m.extendedTextMessage) {
    return { type: 'text', text: m.extendedTextMessage.text || '' };
  }

  // Image
  if (m.imageMessage) {
    return {
      type: 'image',
      text: m.imageMessage.caption || '[Mengirim gambar]',
      caption: m.imageMessage.caption || '',
      media: {
        mimetype: m.imageMessage.mimetype,
        fileLength: m.imageMessage.fileLength,
        height: m.imageMessage.height,
        width: m.imageMessage.width,
        jpegThumbnail: m.imageMessage.jpegThumbnail,
      },
    };
  }

  // Document
  if (m.documentMessage) {
    return {
      type: 'document',
      text: `[Mengirim dokumen: ${m.documentMessage.fileName || 'file'}]`,
      caption: m.documentMessage.caption || '',
      media: {
        mimetype: m.documentMessage.mimetype,
        fileName: m.documentMessage.fileName,
        fileLength: m.documentMessage.fileLength,
        pageCount: m.documentMessage.pageCount,
      },
    };
  }

  // Audio / Voice note
  if (m.audioMessage) {
    return {
      type: 'audio',
      text: m.audioMessage.ptt ? '[Mengirim pesan suara]' : '[Mengirim audio]',
      media: {
        mimetype: m.audioMessage.mimetype,
        fileLength: m.audioMessage.fileLength,
        seconds: m.audioMessage.seconds,
        ptt: m.audioMessage.ptt,
      },
    };
  }

  // Video
  if (m.videoMessage) {
    return {
      type: 'video',
      text: m.videoMessage.caption || '[Mengirim video]',
      caption: m.videoMessage.caption || '',
      media: {
        mimetype: m.videoMessage.mimetype,
        fileLength: m.videoMessage.fileLength,
        seconds: m.videoMessage.seconds,
        height: m.videoMessage.height,
        width: m.videoMessage.width,
      },
    };
  }

  // Location
  if (m.locationMessage) {
    return {
      type: 'location',
      text: `[Mengirim lokasi: ${m.locationMessage.degreesLatitude}, ${m.locationMessage.degreesLongitude}]`,
      location: {
        latitude: m.locationMessage.degreesLatitude,
        longitude: m.locationMessage.degreesLongitude,
        name: m.locationMessage.name || '',
        address: m.locationMessage.address || '',
      },
    };
  }

  // Contact vCard
  if (m.contactsArrayMessage) {
    const contacts = m.contactsArrayMessage;
    const firstContact = contacts.contacts?.[0];
    const displayName = contacts.displayName || firstContact?.displayName || 'Kontak';
    return {
      type: 'contact',
      text: `[Membagikan kontak: ${displayName}]`,
      contact: { displayName },
    };
  }

  // Live location
  if (m.liveLocationMessage) {
    return {
      type: 'live_location',
      text: '[Mengirim lokasi langsung]',
      location: {
        latitude: m.liveLocationMessage.degreesLatitude,
        longitude: m.liveLocationMessage.degreesLongitude,
      },
    };
  }

  // Sticker
  if (m.stickerMessage) {
    return {
      type: 'sticker',
      text: '[Mengirim stiker]',
      media: {
        mimetype: m.stickerMessage.mimetype,
        isAnimated: m.stickerMessage.isAnimated,
      },
    };
  }

  // Unknown message type — try any available caption/text
  const anyText =
    m.listResponseMessage?.title ||
    m.buttonsResponseMessage?.selectedButtonId ||
    m.templateButtonReplyMessage?.selectedId ||
    m.orderMessage?.title ||
    '';
  if (anyText) {
    return { type: 'interactive', text: anyText };
  }

  return { type: 'unknown', text: '[Pesan tidak dikenal]' };
}

module.exports = {
  sendText,
  sendTextWithTyping,
  sendImage,
  sendDocument,
  sendAudio,
  sendVideo,
  sendLocation,
  sendContact,
  extractMessageContent,
};
