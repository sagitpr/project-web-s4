/**
 * Warungio Smart AI Scan — Real Tesseract.js OCR + TensorFlow.js MobileNet
 * Replaces simulated if/else freshness detection with actual AI inference.
 *
 * MDN Web Speech API: https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API
 * Tesseract.js: https://tesseract.projectnaptha.com/
 * TensorFlow.js: https://www.tensorflow.org/js
 */

window.WarungioAIScan = (function () {
  'use strict';

  var tfReady = false;
  var tesseractReady = false;
  var mobilenetModel = null;
  
  // ── TensorFlow.js / MobileNet ──
  function initTF() {
    if (typeof tf === 'undefined' || typeof mobilenet === 'undefined') {
      console.warn('TensorFlow.js or MobileNet not loaded');
      return Promise.resolve(false);
    }
    if (mobilenetModel) return Promise.resolve(true);
    
    return mobilenet.load().then(function (model) {
      mobilenetModel = model;
      tfReady = true;
      console.info('AI Scan: MobileNet model loaded');
      return true;
    }).catch(function (err) {
      console.warn('AI Scan: MobileNet load failed:', err);
      return false;
    });
  }

  // ── Classify image using MobileNet ──
  function classifyImage(videoElement) {
    if (!mobilenetModel || !videoElement || !videoElement.videoWidth) {
      return Promise.resolve(null);
    }

    // Capture frame from video to a canvas
    var canvas = document.createElement('canvas');
    canvas.width = 224;
    canvas.height = 224;
    var ctx = canvas.getContext('2d');
    ctx.drawImage(videoElement, 0, 0, 224, 224);

    return mobilenetModel.classify(canvas).then(function (predictions) {
      if (!predictions || predictions.length === 0) return null;
      
      // Map predictions to freshness/quality
      // MobileNet returns classes like "green salad", "vegetable", etc.
      var topPrediction = predictions[0];
      var className = (topPrediction.className || '').toLowerCase();
      var confidence = topPrediction.probability || 0;
      
      // Food-related classes indicate the product is present and looks fresh
      var foodKeywords = ['salad', 'vegetable', 'fruit', 'food', 'produce', 'leaf', 'green'];
      var isFoodRelated = foodKeywords.some(function(kw) { return className.indexOf(kw) !== -1; });
      
      // Note: MobileNet classifies objects, NOT freshness.
      // "freshness_score" is an estimate based on whether the detected
      // object is food-related. Use as a hint, not a precise measurement.
      return {
        label: className,
        confidence: confidence,
        quality_status: isFoodRelated && confidence > 0.3 ? 'fresh' : 'warning',
        freshness_score: isFoodRelated ? Math.min(95, Math.round(confidence * 100)) : Math.round(confidence * 60),
        is_valid: isFoodRelated && confidence > 0.2,
        _disclaimer: 'Freshness score is estimated from object classification — not a precise measurement'
      };
    }).catch(function (err) {
      console.warn('AI Scan: Classification failed:', err);
      return null;
    });
  }

  // ── Tesseract.js OCR ──
  function initTesseract() {
    if (typeof Tesseract === 'undefined') {
      console.warn('Tesseract.js not loaded');
      return Promise.resolve(false);
    }
    tesseractReady = true;
    return Promise.resolve(true);
  }

  function runOCR(videoElement) {
    if (!tesseractReady || typeof Tesseract === 'undefined') {
      return Promise.resolve(null);
    }

    var canvas = document.createElement('canvas');
    canvas.width = 640;
    canvas.height = 480;
    var ctx = canvas.getContext('2d');
    ctx.drawImage(videoElement, 0, 0, 640, 480);

    var imageData = canvas.toDataURL('image/png');

    return Tesseract.recognize(imageData, 'eng+ind', {
      logger: function(m) {
        if (m.status === 'recognizing text') {
          // Update progress in UI if needed
        }
      }
    }).then(function(result) {
      if (!result || !result.data) return null;
      
      var text = (result.data.text || '').trim();
      var confidence = result.data.confidence || 0;
      
      // Extract useful info from OCR text
      var barcode = '';
      var expirationDate = '';
      var bpomNumber = '';
      
      // Look for date patterns like "EXP: 2025-12-31" or "KD: 2027-12-31"
      var dateMatch = text.match(/(?:EXP|KD|ED|BB|best before|use by)[:\s]*(\d{2,4}[\-\/]\d{1,2}[\-\/]\d{1,4})/i);
      if (dateMatch) expirationDate = dateMatch[1];
      
      // Look for barcode-like numbers (13 digits)
      var barcodeMatch = text.match(/\b(\d{13})\b/);
      if (barcodeMatch) barcode = barcodeMatch[1];
      
      // Look for BPOM numbers
      var bpomMatch = text.match(/\b((?:MD|ML|BPOM|POM)[-\s]?\d{6,})\b/i);
      if (bpomMatch) bpomNumber = bpomMatch[1];
      
      return {
        text: text,
        confidence: confidence,
        barcode: barcode,
        expiration_date: expirationDate,
        bpom_number: bpomNumber,
        confidence_uncertain: confidence < 60
      };
    }).catch(function(err) {
      console.warn('AI Scan: OCR failed:', err);
      return null;
    });
  }

  // ── Public API ──
  return {
    initTF: initTF,
    initTesseract: initTesseract,
    classifyImage: classifyImage,
    runOCR: runOCR,
    isTfReady: function() { return tfReady; },
    isTesseractReady: function() { return tesseractReady; }
  };
})();
