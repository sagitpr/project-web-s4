/**
 * Warungio — Device Detection & Responsive Utilities
 *
 * Automatically detects device type, screen size, orientation,
 * and touch support. Stores results in window.WarungioDevice.
 *
 * Usage:
 *   if (WarungioDevice.isMobile) { ... }
 *   if (WarungioDevice.isTablet) { ... }
 *   if (WarungioDevice.isDesktop) { ... }
 *   WarungioDevice.onResize(() => { ... });
 */
(function () {
  'use strict';

  var Device = {
    deviceType: 'desktop',
    screenSize: { width: 0, height: 0 },
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    isPortrait: true,
    isLandscape: false,
    hasTouch: false,
    pixelRatio: 1,
    breakpoints: {
      mobile: 480,
      tablet: 720,
      desktop: 1024,
    },

    /** Detect device type from window width */
    detect: function () {
      var w = window.innerWidth;
      var h = window.innerHeight;

      this.screenSize.width = w;
      this.screenSize.height = h;
      this.isPortrait = h > w;
      this.isLandscape = w > h;
      this.pixelRatio = window.devicePixelRatio || 1;
      this.hasTouch = 'ontouchstart' in window ||
        navigator.maxTouchPoints > 0;

      if (w <= this.breakpoints.mobile) {
        this.deviceType = 'mobile';
        this.isMobile = true;
        this.isTablet = false;
        this.isDesktop = false;
      } else if (w <= this.breakpoints.tablet) {
        this.deviceType = 'mobile';
        this.isMobile = true;
        this.isTablet = false;
        this.isDesktop = false;
      } else if (w <= this.breakpoints.desktop) {
        this.deviceType = 'tablet';
        this.isMobile = false;
        this.isTablet = true;
        this.isDesktop = false;
      } else {
        this.deviceType = 'desktop';
        this.isMobile = false;
        this.isTablet = false;
        this.isDesktop = true;
      }

      // Dispatch event for other scripts
      document.dispatchEvent(new CustomEvent('warungio:devicechange', {
        detail: {
          deviceType: this.deviceType,
          isMobile: this.isMobile,
          isTablet: this.isTablet,
          isDesktop: this.isDesktop,
          width: w,
          height: h,
        }
      }));

      return this;
    },

    /** Register callback on resize */
    onResize: function (callback) {
      var self = this;
      var ticking = false;

      window.addEventListener('resize', function () {
        if (!ticking) {
          window.requestAnimationFrame(function () {
            self.detect();
            if (typeof callback === 'function') callback(self);
            ticking = false;
          });
          ticking = true;
        }
      });

      // Fire immediately
      if (typeof callback === 'function') callback(this);
    },

    /** Check if width is below breakpoint */
    below: function (bp) {
      return this.screenSize.width < (this.breakpoints[bp] || bp);
    },

    /** Check if width is above breakpoint */
    above: function (bp) {
      return this.screenSize.width >= (this.breakpoints[bp] || bp);
    },

    /** Get human-readable label */
    getLabel: function () {
      var labels = {
        mobile: 'Mobile',
        tablet: 'Tablet',
        desktop: 'Desktop',
      };
      return labels[this.deviceType] || 'Desktop';
    },
  };

  // Run initial detection
  Device.detect();

  // Expose globally
  window.WarungioDevice = Device;

  // Also add a convenience class to <html> for CSS hooks
  document.documentElement.classList.add('device-' + Device.deviceType);
  if (Device.hasTouch) {
    document.documentElement.classList.add('has-touch');
  }
  if (Device.isPortrait) {
    document.documentElement.classList.add('portrait');
  }

})();
