'use strict';

const pino = require('pino');
const config = require('../config');

const logger = pino({
  level: config.logLevel,
  transport: {
    target: 'pino-pretty',
    options: {
      colorize: true,
      translateTime: 'SYS:dd-mm-yyyy HH:MM:ss',
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
