'use strict';

const fs = require('fs');
const path = require('path');
const logger = require('./utils/logger');

const HISTORY_FILE = path.join(__dirname, '..', 'data', 'history.json');
const MAX_HISTORY_PER_USER = 50;

/**
 * Ensure the history file exists and is valid JSON.
 * Creates the file with an empty object if missing or corrupted.
 */
function ensureHistoryFile() {
  const dir = path.dirname(HISTORY_FILE);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  if (!fs.existsSync(HISTORY_FILE)) {
    fs.writeFileSync(HISTORY_FILE, '{}', 'utf-8');
    return {};
  }
  try {
    const raw = fs.readFileSync(HISTORY_FILE, 'utf-8');
    return JSON.parse(raw);
  } catch (_) {
    logger.warn('History file corrupted — resetting to empty');
    fs.writeFileSync(HISTORY_FILE, '{}', 'utf-8');
    return {};
  }
}

/**
 * Load full history object { phone: [messages] }.
 * @returns {Object}
 */
function loadHistory() {
  return ensureHistoryFile();
}

/**
 * Persist history object to disk atomically.
 * @param {Object} data
 */
function persistHistory(data) {
  fs.writeFileSync(HISTORY_FILE, JSON.stringify(data, null, 2), 'utf-8');
}

/**
 * Get conversation array for a specific phone number.
 * @param {string} phone
 * @returns {Array}
 */
function getConversation(phone) {
  const data = loadHistory();
  return data[phone] || [];
}

/**
 * Save a message (user or bot) to the conversation history.
 * @param {string} phone
 * @param {'user'|'bot'} role
 * @param {string} text
 */
function saveMessage(phone, role, text) {
  const data = loadHistory();
  if (!data[phone]) {
    data[phone] = [];
  }
  data[phone].push({
    role,
    text,
    timestamp: new Date().toISOString(),
  });
  // Trim to prevent unbounded growth
  if (data[phone].length > MAX_HISTORY_PER_USER) {
    data[phone] = data[phone].slice(-MAX_HISTORY_PER_USER);
  }
  persistHistory(data);
}

/**
 * Clear conversation history for a specific phone.
 * @param {string} phone
 */
function clearHistory(phone) {
  const data = loadHistory();
  delete data[phone];
  persistHistory(data);
}

/**
 * Set a session state key-value pair for a phone number.
 * Session state is persistent across bot restarts.
 * @param {string} phone
 * @param {string} key
 * @param {*} value
 */
function setSessionState(phone, key, value) {
  const data = loadHistory();
  if (!data[phone]) {
    data[phone] = [];
  }
  if (!data[phone]._session) {
    data[phone]._session = {};
  }
  data[phone]._session[key] = value;
  persistHistory(data);
}

/**
 * Get a session state value for a phone number.
 * @param {string} phone
 * @param {string} key
 * @param {*} [defaultValue]
 * @returns {*}
 */
function getSessionState(phone, key, defaultValue) {
  const data = loadHistory();
  if (!data[phone] || !data[phone]._session) {
    return defaultValue;
  }
  const val = data[phone]._session[key];
  return val !== undefined ? val : defaultValue;
}

/**
 * Check if the welcome message has been sent to this user.
 * @param {string} phone
 * @returns {boolean}
 */
function isWelcomeSent(phone) {
  return getSessionState(phone, 'welcomeSent', false) === true;
}

/**
 * Mark that the welcome message has been sent to this user.
 * @param {string} phone
 */
function markWelcomeSent(phone) {
  setSessionState(phone, 'welcomeSent', true);
}

module.exports = {
  loadHistory,
  getConversation,
  saveMessage,
  clearHistory,
  setSessionState,
  getSessionState,
  isWelcomeSent,
  markWelcomeSent,
};
