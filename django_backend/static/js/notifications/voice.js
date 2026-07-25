/**
 * Warungio Voice Notification Manager
 *
 * Uses the Web Speech API (SpeechSynthesis) for browser-native Text-to-Speech.
 * No external API key or service needed — works offline in modern browsers.
 *
 * Features:
 *   - Audio queue: sequential playback, no overlapping
 *   - Idempotency: tracks transaction IDs to prevent duplicate plays
 *   - Auto-reconnect: survives WebSocket disconnects
 *   - Settings: enable/disable, volume, test button
 *   - Indonesian language TTS (id-ID)
 *
 * Usage:
 *   VoiceNotificationManager.init({
 *     ws: window.WarungioWS,      // WebSocket client
 *     storageKey: 'warungio_voice_settings',  // localStorage key
 *   });
 *
 *   // Start listening (called after dashboard loads)
 *   VoiceNotificationManager.start();
 *
 *   // Stop (called on page leave)
 *   VoiceNotificationManager.stop();
 */
(function () {
  'use strict';

  // ── Constants ──
  var STORAGE_KEY = 'warungio_voice_settings';
  var PLAYED_KEY = 'warungio_voice_played';
  var MAX_QUEUE = 20;          // Max queued notifications
  var COOLDOWN_MS = 3000;      // Min gap between voice plays
  var MAX_PLAYED_IDS = 100;    // Max tracked IDs (LRU cleanup)
  var INDONESIAN_LANG = 'id-ID';
  var _keepAliveTimer = null;  // Chrome speechSynthesis bug workaround
  var _settingsCallback = null;

  // ── State ──
  var _ws = null;
  var _unsubscribers = [];
  var _queue = [];
  var _isPlaying = false;
  var _lastPlayedAt = 0;
  var _settings = {
    enabled: true,
    volume: 0.7,    // 0.0 to 1.0
    rate: 1.0,      // 0.1 to 10.0 (SpeechSynthesisUtterance.rate)
    pitch: 1.0,     // 0.0 to 2.0 (SpeechSynthesisUtterance.pitch)
  };
  var _initialized = false;

  // ── Helpers ──

  /** Load settings from localStorage. */
  function _loadSettings() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        var saved = JSON.parse(raw);
        if (saved.enabled !== undefined) _settings.enabled = saved.enabled;
        if (saved.volume !== undefined) _settings.volume = Math.max(0, Math.min(1, saved.volume));
        if (saved.rate !== undefined) _settings.rate = Math.max(0.1, Math.min(10, saved.rate));
        if (saved.pitch !== undefined) _settings.pitch = Math.max(0, Math.min(2, saved.pitch));
      }
    } catch (e) {
      // Corrupted settings — reset
      _saveSettings();
    }
  }

  /** Save settings to localStorage. */
  function _saveSettings() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(_settings));
    } catch (e) {
      // localStorage unavailable
    }
  }

  /** Load played transaction IDs from localStorage (idempotency). */
  function _loadPlayedIds() {
    try {
      var raw = localStorage.getItem(PLAYED_KEY);
      if (raw) {
        return JSON.parse(raw);
      }
    } catch (e) {
      // Corrupted — reset
    }
    return [];
  }

  /** Save played transaction IDs (LRU — max MAX_PLAYED_IDS). */
  function _savePlayedId(txId) {
    try {
      var played = _loadPlayedIds();
      // Remove if exists (to move to front)
      var idx = played.indexOf(txId);
      if (idx !== -1) played.splice(idx, 1);
      // Add to front
      played.unshift(txId);
      // LRU cleanup
      if (played.length > MAX_PLAYED_IDS) {
        played = played.slice(0, MAX_PLAYED_IDS);
      }
      localStorage.setItem(PLAYED_KEY, JSON.stringify(played));
    } catch (e) {
      // localStorage unavailable
    }
  }

  /** Check if a transaction ID has already been played. */
  function _hasBeenPlayed(txId) {
    if (!txId) return false;
    var played = _loadPlayedIds();
    return played.indexOf(txId) !== -1;
  }

  /** Get available Indonesian voices from Web Speech API. */
  function _getVoices() {
    if (!window.speechSynthesis) return [];
    return window.speechSynthesis.getVoices().filter(function (v) {
      return v.lang.startsWith('id') || v.lang.startsWith('ms');
    });
  }

  /** Speak text using Web Speech API with Indonesian voice. */
  function _speak(text, volume, callback) {
    if (!window.speechSynthesis) {
      if (callback) callback();
      return;
    }

    // Cancel any current speech (shouldn't happen with queue, but safe)
    window.speechSynthesis.cancel();

    var utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = INDONESIAN_LANG;
    utterance.volume = volume || _settings.volume;
    utterance.rate = _settings.rate;     // SpeechSynthesisUtterance.rate: 0.1–10
    utterance.pitch = _settings.pitch;    // SpeechSynthesisUtterance.pitch: 0–2

    // Try to find the user's preferred Indonesian voice, or fall back to any Indonesian voice
    var voices = _getVoices();
    if (voices.length > 0) {
      if (_settings.voiceURI) {
        var preferred = voices.find(function (v) { return v.voiceURI === _settings.voiceURI; });
        if (preferred) utterance.voice = preferred;
        else utterance.voice = voices[0];
      } else {
        utterance.voice = voices[0];
      }
    }

    utterance.onend = callback;
    utterance.onerror = function (e) {
      console.warn('[VoiceNotification] Speech error:', e.error);
      if (callback) callback();
    };

    window.speechSynthesis.speak(utterance);
  }

  /** Process the next item in the audio queue. */
  function _processQueue() {
    if (_isPlaying || _queue.length === 0) return;

    _isPlaying = true;
    var item = _queue.shift();

    // Cooldown check: ensure minimum gap between plays
    var now = Date.now();
    var gap = now - _lastPlayedAt;
    if (gap < COOLDOWN_MS && _lastPlayedAt > 0) {
      // Re-queue with delay
      _queue.unshift(item);
      setTimeout(function () {
        _isPlaying = false;
        _processQueue();
      }, COOLDOWN_MS - gap);
      return;
    }

    // Mark as played (idempotency)
    if (item.transactionId) {
      _savePlayedId(item.transactionId);
    }

    // Speak the text
    _speak(item.text, item.volume, function () {
      _lastPlayedAt = Date.now();
      _isPlaying = false;
      // Process next in queue
      _processQueue();
    });
  }

  /** Enqueue a voice notification for sequential playback. */
  function _enqueue(text, transactionId, volume) {
    if (_queue.length >= MAX_QUEUE) {
      // Queue full — drop oldest
      _queue.shift();
    }

    _queue.push({
      text: text,
      transactionId: transactionId,
      volume: volume || _settings.volume,
    });

    // Start processing if not already playing
    _processQueue();
  }

  /** Handle an incoming voice notification from WebSocket. */
  function _handleVoiceEvent(data) {
    if (!_settings.enabled) return;
    if (!data.text) return;

    // Idempotency: skip if already played
    if (data.transaction_id && _hasBeenPlayed(data.transaction_id)) {
      return;
    }

    _enqueue(data.text, data.transaction_id);
  }

  // ── Public API ──

  // ── Chrome speechSynthesis keepalive (prevents engine from going to sleep) ──
  function _startKeepAlive() {
    _stopKeepAlive();
    // Chrome kills speechSynthesis after ~30s of inactivity.
    // Sending a silent utterance every 10s keeps the engine alive.
    _keepAliveTimer = setInterval(function () {
      if (window.speechSynthesis && !_isPlaying && _queue.length === 0) {
        var silent = new SpeechSynthesisUtterance('');
        silent.volume = 0;
        silent.lang = INDONESIAN_LANG;
        window.speechSynthesis.speak(silent);
      }
    }, 10000);
  }

  function _stopKeepAlive() {
    if (_keepAliveTimer) {
      clearInterval(_keepAliveTimer);
      _keepAliveTimer = null;
    }
  }

  var VoiceNotificationManager = {};

  /**
   * Initialize the voice notification manager.
   *
   * @param {Object} options
   * @param {Object} options.ws - WarungioWS instance
   * @param {string} [options.storageKey] - localStorage key for settings
   */
  VoiceNotificationManager.init = function (options) {
    if (_initialized) return;
    options = options || {};
    _ws = options.ws || window.WarungioWS;
    if (options.storageKey) STORAGE_KEY = options.storageKey;

    _loadSettings();
    _initialized = true;

    // Start Chrome speechSynthesis keepalive
    _startKeepAlive();

    console.info('[VoiceNotification] Initialized (enabled:', _settings.enabled, 'volume:', _settings.volume, ')');
  };

  /**
   * Get available Indonesian voices.
   * Returns array of { name, voiceURI, lang }.
   */
  VoiceNotificationManager.getVoices = function () {
    return _getVoices().map(function (v) {
      return { name: v.name, voiceURI: v.voiceURI, lang: v.lang };
    });
  };

  /**
   * Start listening for voice notification events on WebSocket.
   * Call this after the seller dashboard loads.
   */
  VoiceNotificationManager.start = function () {
    if (!_ws) {
      console.warn('[VoiceNotification] No WebSocket client — voice unavailable');
      return;
    }

    // Listen for voice_notification events
    var unsub = _ws.on('voice_notification', _handleVoiceEvent);
    _unsubscribers.push(unsub);

    console.info('[VoiceNotification] Started listening for voice events');
  };

  /**
   * Stop listening and clear queue.
   * Call this when leaving the dashboard page.
   */
  VoiceNotificationManager.stop = function () {
    // Unsubscribe all
    _unsubscribers.forEach(function (fn) { try { fn(); } catch (e) {} });
    _unsubscribers = [];
    _queue = [];
    _isPlaying = false;

    // Stop keepalive
    _stopKeepAlive();

    // Cancel any ongoing speech
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }

    console.info('[VoiceNotification] Stopped');
  };

  /**
   * Manually test the voice notification system.
   * Speaks a sample text to verify TTS works.
   */
  VoiceNotificationManager.test = function () {
    var testText = 'Tes notifikasi suara Warungio. Sistem berfungsi dengan baik.';
    _enqueue(testText, 'test-' + Date.now(), _settings.volume);
    console.info('[VoiceNotification] Test voice played');
  };

  /**
   * Get current settings.
   */
  VoiceNotificationManager.getSettings = function () {
    return {
      enabled: _settings.enabled,
      volume: _settings.volume,
      rate: _settings.rate,
      pitch: _settings.pitch,
      voiceURI: _settings.voiceURI || null,
    };
  };

  /**
   * Update settings.
   *
   * @param {Object} newSettings - { enabled?: boolean, volume?: number }
   */
  /**
   * Register a callback that fires whenever settings change.
   * Useful for UI sync (e.g., the settings panel on seller dashboard).
   */
  VoiceNotificationManager.onSettingsChange = function (callback) {
    _settingsCallback = callback;
  };

  VoiceNotificationManager.updateSettings = function (newSettings) {
    var changed = false;

    if (newSettings.enabled !== undefined && newSettings.enabled !== _settings.enabled) {
      _settings.enabled = !!newSettings.enabled;
      changed = true;
      // Cancel all speech when disabled
      if (!_settings.enabled && window.speechSynthesis) {
        window.speechSynthesis.cancel();
        _queue = [];
        _isPlaying = false;
      }
    }

    if (newSettings.volume !== undefined) {
      var vol = Math.max(0, Math.min(1, Number(newSettings.volume) || 0.7));
      if (vol !== _settings.volume) {
        _settings.volume = vol;
        changed = true;
      }
    }

    if (newSettings.rate !== undefined) {
      var rate = Math.max(0.1, Math.min(10, Number(newSettings.rate) || 1.0));
      if (rate !== _settings.rate) {
        _settings.rate = rate;
        changed = true;
      }
    }

    if (newSettings.pitch !== undefined) {
      var pitch = Math.max(0, Math.min(2, Number(newSettings.pitch) || 1.0));
      if (pitch !== _settings.pitch) {
        _settings.pitch = pitch;
        changed = true;
      }
    }

    if (newSettings.voiceURI !== undefined) {
      if (newSettings.voiceURI !== _settings.voiceURI) {
        _settings.voiceURI = newSettings.voiceURI;
        changed = true;
      }
    }

    if (changed) {
      _saveSettings();
      if (_settingsCallback) {
        _settingsCallback(VoiceNotificationManager.getSettings());
      }
    }

    return VoiceNotificationManager.getSettings();
  };

  /**
   * Clear all played transaction IDs (for testing / reset).
   */
  VoiceNotificationManager.clearHistory = function () {
    try {
      localStorage.removeItem(PLAYED_KEY);
    } catch (e) {}
  };

  // ── Export ──
  window.VoiceNotificationManager = VoiceNotificationManager;

  // ── Pre-load voices (browser loads them asynchronously) ──
  if (window.speechSynthesis) {
    // Chrome loads voices asynchronously — trigger early
    window.speechSynthesis.getVoices();
    window.speechSynthesis.onvoiceschanged = function () {
      window.speechSynthesis.getVoices();
    };
  }
})();
