'use strict';

const pino = require('pino');
const config = require('../config');

/**
 * Logger with safe UTF-8 encoding.
 *
 * FIX: The 'SYS:' prefix in pino-pretty's translateTime option
 * outputs non-ASCII Unicode characters (like \u2014 / —) on Windows,
 * which show as garbage characters (ΓÇö, ΓÇô). Using 'UTC:' prefix
 * or a pure-numeric format avoids this encoding issue entirely.
 */
const logger = pino({
  level: config.logLevel,
  transport: {
    target: 'pino-pretty',
    options: {
      colorize: true,
      translateTime: 'UTC:dd-mm-yyyy HH:MM:ss.l',
      ignore: 'pid,hostname',
    },
  },
});

/**
 * Custom success log level (pino does not have .success natively,
 * so we map it to 'info' with a [SUCCESS] prefix).
 */
logger.success = (msg, ...args) => {
  logger.info({ type: 'SUCCESS' }, `[SUCCESS] ${msg}`, ...args);
};

module.exports = logger;
