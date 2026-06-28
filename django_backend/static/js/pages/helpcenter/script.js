/* ── Help Center – Warungio ── */
/* Chat panel, FAQ accordion, search, interactions */

(function() {
  'use strict';

  /* ── DOM refs (late-binding) ── */
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => document.querySelectorAll(s);

  let currentUser = null;
  let chatSocket = null;

  /* ── Chat Panel ── */
  function initChat() {
    const fab = $('.chat-fab');
    const overlay = $('#chatOverlay');
    const panel = $('#chatPanel');
    const closeBtn = $('#chatClose');
    const sendBtn = $('#chatSend');
    const input = $('#chatInput');
    const messages = $('#chatMessages');
    const typing = $('#chatTyping');

    if (!fab || !panel) return;

    function openPanel() {
      overlay.classList.add('open');
      panel.classList.add('open');
      document.body.style.overflow = 'hidden';
      if (input) {
        input.focus();
        setTimeout(() => input.focus(), 100);
      }
      // Reset badge
      const badge = $('.chat-fab-badge');
      if (badge) badge.classList.remove('show');
    }

    function closePanel() {
      overlay.classList.remove('open');
      panel.classList.remove('open');
      document.body.style.overflow = '';
    }

    fab.addEventListener('click', openPanel);
    if (closeBtn) closeBtn.addEventListener('click', closePanel);
    if (overlay) overlay.addEventListener('click', closePanel);

    // Quick reply buttons
    $$('.chat-quick-reply').forEach(btn => {
      btn.addEventListener('click', function() {
        if (input) {
          input.value = this.textContent.trim();
          input.focus();
        }
        if (!panel.classList.contains('open')) {
          openPanel();
        }
      });
    });

    // Send message
    function sendMessage() {
      if (!input) return;
      const text = input.value.trim();
      if (!text) return;
      input.value = '';

      addMessage(text, true);
      if (typing) typing.classList.add('show');

      // Simulate AI response (replace with real API call)
      setTimeout(() => {
        if (typing) typing.classList.remove('show');
        const responses = [
          'Baik, saya akan bantu Anda. Silakan tunggu sebentar ya.',
          'Terima kasih sudah menghubungi Warungio. Tim kami akan merespon pesan Anda.',
          'Mohon tunggu, kami sedang memeriksa informasi yang Anda butuhkan.',
          'Baik, kami akan segera membantu Anda terkait hal tersebut.',
        ];
        addMessage(responses[Math.floor(Math.random() * responses.length)], false);
      }, 1200 + Math.random() * 800);
    }

    if (sendBtn) sendBtn.addEventListener('click', sendMessage);
    if (input) {
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          sendMessage();
        }
      });
    }
  }

  function addMessage(text, isUser, time) {
    const container = document.getElementById('chatMessages');
    if (!container) return;

    const timeStr = time || new Date().toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
    const div = document.createElement('div');
    div.className = `chat-msg ${isUser ? 'user' : 'admin'}`;
    div.innerHTML = `<div>${escapeHtml(text)}</div><div class="time">${timeStr}</div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  }

  function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
  }

  /* ── FAQ Accordion ── */
  function initFAQ() {
    $$('.faq-item').forEach(item => {
      const question = item.querySelector('.faq-question');
      if (!question) return;
      question.addEventListener('click', function() {
        const isOpen = item.classList.contains('open');
        // Close all others
        $$('.faq-item.open').forEach(el => el.classList.remove('open'));
        if (!isOpen) {
          item.classList.add('open');
        }
      });
    });
  }

  /* ── Category Cards ── */
  function initCategories() {
    $$('.category-card').forEach(card => {
      card.addEventListener('click', function() {
        const slug = this.dataset.slug;
        if (slug) {
          window.location.href = '/bantuan/?category=' + slug;
        }
      });
    });
  }

  /* ── Search ── */
  function initSearch() {
    const input = document.getElementById('helpSearchInput');
    const results = document.getElementById('helpSearchResults');
    if (!input || !results) return;

    let debounceTimer = null;
    function doSearch(q) {
      q = q.trim().toLowerCase();
      if (q.length < 2) {
        results.classList.remove('show');
        return;
      }

      // Search locally first for instant results
      const articles = window.__helpArticles || [];
      const filtered = articles.filter(a =>
        a.title.toLowerCase().includes(q) ||
        (a.excerpt && a.excerpt.toLowerCase().includes(q))
      ).slice(0, 6);

      if (filtered.length > 0) {
        results.innerHTML = filtered.map(a => `
          <a href="/bantuan/artikel/${a.slug}/" class="result-item" style="text-decoration:none">
            <div class="icon">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
            </div>
            <div class="info">
              <h4>${escapeHtml(a.title)}</h4>
              <p>${a.excerpt ? escapeHtml(a.excerpt.substring(0, 80)) : ''}</p>
            </div>
          </a>
        `).join('');
        results.classList.add('show');
      } else {
        results.innerHTML = '<div class="result-empty">Tidak menemukan artikel. Silakan hubungi tim support kami.</div>';
        results.classList.add('show');
      }
    }

    input.addEventListener('input', function() {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => doSearch(this.value), 200);
    });

    // Close search results on outside click
    document.addEventListener('click', function(e) {
      if (!input.contains(e.target) && !results.contains(e.target)) {
        results.classList.remove('show');
      }
    });
  }

  /* ── Auth check ── */
  async function checkAuth() {
    try {
      if (window.WarungioAuth && window.WarungioAuth.isAuthenticated()) {
        const u = await window.WarungioAPI.checkAuth();
        if (u && u.user) {
          currentUser = u.user;
          // Update profile dropdown
          const userName = document.getElementById('userName');
          if (userName) userName.textContent = u.user.full_name || u.user.email;
          const userEmail = document.getElementById('userEmail');
          if (userEmail) userEmail.textContent = u.user.email;
        }
      }
    } catch(e) {
      // Not authenticated — that's ok, help center is public
    }
  }

  /* ── Init ── */
  document.addEventListener('DOMContentLoaded', function() {
    initChat();
    initFAQ();
    initCategories();
    initSearch();
    checkAuth();

    // Profile dropdown
    const profileBtn = document.getElementById('profileBtn');
    const profileDropdown = document.getElementById('profileDropdown');
    if (profileBtn && profileDropdown) {
      profileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        profileDropdown.classList.toggle('hidden');
      });
      document.addEventListener('click', () => {
        profileDropdown.classList.add('hidden');
      });
    }

    // CTA button opens chat
    const ctaBtn = document.getElementById('ctaOpenChat');
    const fab = document.querySelector('.chat-fab');
    if (ctaBtn && fab) {
      ctaBtn.addEventListener('click', function(e) {
        e.preventDefault();
        fab.click();
      });
    }
  });
})();
