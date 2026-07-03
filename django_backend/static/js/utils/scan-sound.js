/**
 * Warungio Scan Sound Effect Utility
 *
 * Plays "Tit_kasir" sound on barcode, QR, OCR, or AI scan success.
 * Features:
 *   - Zero delay: pre-buffered AudioBuffer plays instantly
 *   - No overlap: debounce prevents stacked sounds (300ms cooldown)
 *   - Desktop + mobile: Web Audio API primary, HTMLAudio fallback
 *   - No performance impact: tiny 10KB file, singleton AudioContext
 *   - Auto-detects static file path (Django {% static %} or standalone)
 *
 * Usage:
 *   ScanSound.play();           // Play once
 *   ScanSound.play(true);       // Play with haptic feedback (mobile)
 *
 * Dependencies:
 *   /static/audio/Tit_kasir.mp3 (or /assets/audio/Tit_kasir.mp3 for standalone)
 */
(function () {
  'use strict';

  var ScanSound = {
    _audioContext: null,
    _buffer: null,
    _lastPlayed: 0,
    _debounceMs: 300,
    _loadAttempted: false,
    _loadSuccess: false,
    _fallbackAudio: null,

    /**
     * Auto-detect the correct audio URL.
     * Django templates use {% static %}, standalone pages use relative path.
     */
    _getAudioUrl: function () {
      // Prefer injected URL, fallback to default /static/ path
      if (window.WARUNGIO_SCAN_SOUND_URL) {
        return window.WARUNGIO_SCAN_SOUND_URL;
      }
      return '/static/audio/Tit_kasir.mp3';
    },

    /**
     * Initialize: fetch and decode the audio file into a buffer.
     * Called once on first play — no startup delay.
     */
    _init: function () {
      if (this._loadAttempted) return;
      this._loadAttempted = true;

      try {
        // Use Web Audio API for zero-latency playback
        var AudioContext = window.AudioContext || window.webkitAudioContext;
        if (!AudioContext) {
          // Fallback: HTMLAudioElement
          this._fallbackAudio = new Audio();
          this._fallbackAudio.src = this._getAudioUrl();
          this._fallbackAudio.preload = 'auto';
          this._loadSuccess = true;
          return;
        }

        this._audioContext = new AudioContext();
        var self = this;
        var url = this._getAudioUrl();

        // Fetch as ArrayBuffer and decode
        fetch(url)
          .then(function (res) {
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.arrayBuffer();
          })
          .then(function (arrayBuffer) {
            return self._audioContext.decodeAudioData(arrayBuffer);
          })
          .then(function (audioBuffer) {
            self._buffer = audioBuffer;
            self._loadSuccess = true;
          })
          .catch(function () {
            // Fallback to HTMLAudio on error
            self._fallbackAudio = new Audio(url);
            self._fallbackAudio.preload = 'auto';
            self._loadSuccess = true;
          });
      } catch (e) {
        // Last resort: HTMLAudio fallback
        try {
          this._fallbackAudio = new Audio(this._getAudioUrl());
          this._fallbackAudio.preload = 'auto';
          this._loadSuccess = true;
        } catch (e2) {
          // Audio not supported — fail silently
          this._loadSuccess = false;
        }
      }
    },

    /**
     * Play the scan sound effect.
     *
     * @param {boolean} [haptic=false] - Also trigger vibration on supported mobile devices
     * @returns {boolean} Whether the sound was played
     */
    play: function (haptic) {
      // Debounce: prevent overlap within debounce window
      var now = Date.now();
      if (now - this._lastPlayed < this._debounceMs) {
        return false;
      }
      this._lastPlayed = now;

      // Lazy init on first play
      if (!this._loadAttempted) {
        this._init();
        // Init is async — play fallback immediately on first call
        this._playFallback();
        return true;
      }

      // Play via Web Audio API (primary, zero-latency)
      if (this._audioContext && this._buffer) {
        // Resume context if suspended (autoplay policy — user gesture required)
        if (this._audioContext.state === 'suspended') {
          this._audioContext.resume().catch(function () {});
        }

        try {
          var source = this._audioContext.createBufferSource();
          source.buffer = this._buffer;
          source.connect(this._audioContext.destination);
          source.start(0);
        } catch (e) {
          this._playFallback();
        }
      } else {
        // Buffer still loading or fallback mode — never re-fetch
        this._playFallback();
      }

      // Haptic feedback (mobile vibration)
      if (haptic && navigator.vibrate) {
        try {
          navigator.vibrate(50);
        } catch (e) {
          // Vibration not supported
        }
      }

      return true;
    },

    /**
     * Fallback: play via HTMLAudioElement.
     * Clones the audio element to allow rapid re-plays.
     */
    _playFallback: function () {
      try {
        if (this._fallbackAudio && this._fallbackAudio.src) {
          var clone = this._fallbackAudio.cloneNode(true);
          clone.volume = 1.0;
          clone.play().catch(function () {});
        } else if (!this._fallbackAudio || !this._fallbackAudio.src) {
          // Create on-demand fallback if not yet initialized
          this._fallbackAudio = new Audio(this._getAudioUrl());
          this._fallbackAudio.preload = 'auto';
          this._fallbackAudio.play().catch(function () {});
        }
      } catch (e) {
        // Silently fail — audio is non-critical
      }
    },

    /**
     * Force reinitialize (e.g., after page navigation in SPA).
     */
    reset: function () {
      this._loadAttempted = false;
      this._loadSuccess = false;
      this._buffer = null;
      this._lastPlayed = 0;
    }
  };

  // Expose globally
  window.WarungioScanSound = ScanSound;
})();
