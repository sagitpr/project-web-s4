'use strict';

require('dotenv').config();

const config = {
  // AI
  aiEnabled: process.env.AI_ENABLED === 'true',
  geminiApiKey: process.env.GEMINI_API_KEY || '',
  geminiModel: process.env.GEMINI_MODEL || 'gemini-2.0-flash',
  geminiTemperature: parseFloat(process.env.GEMINI_TEMPERATURE || '0.7'),
  geminiMaxTokens: parseInt(process.env.GEMINI_MAX_TOKENS || '1024', 10),

  // WhatsApp Session
  sessionDir: process.env.SESSION_DIR || './session',

  // Bot Identity
  botName: process.env.BOT_NAME || 'Warungio',
  botVersion: process.env.BOT_VERSION || '1.0.0',
  botDescription: process.env.BOT_DESCRIPTION || 'Asisten Virtual Warungio',

  // Connection
  // How often (ms) to check socket health. Default: 30 seconds.
  heartbeatIntervalMs: parseInt(process.env.HEARTBEAT_INTERVAL_MS || '30000', 10),
  // Maximum number of consecutive reconnect attempts before giving up.
  maxReconnectAttempts: parseInt(process.env.MAX_RECONNECT_ATTEMPTS || '50', 10),

  // Logging
  logLevel: process.env.LOG_LEVEL || 'info',
};

module.exports = config;
