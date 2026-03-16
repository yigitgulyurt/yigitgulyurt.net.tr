(function () {
  'use strict';

  // --- Dil seçici ---
  const LANG_KEY = 'yg_lang';

  function applyLang(lang) {
    document.documentElement.setAttribute('data-lang', lang);
    const btn = document.getElementById('langbtn');
    if (btn) btn.textContent = lang === 'en' ? 'TR' : 'EN';
    localStorage.setItem(LANG_KEY, lang);
  }

  window.toggleLang = function () {
    const current = document.documentElement.getAttribute('data-lang') || 'tr';
    applyLang(current === 'tr' ? 'en' : 'tr');
  };

  // Kayıtlı dili uygula
  const saved = localStorage.getItem(LANG_KEY);
  if (saved) applyLang(saved);

})();
