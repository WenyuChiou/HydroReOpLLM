// Progressively enhance the existing static manual. No requests or model calls.
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.contents-toggle');
  const chapters = document.getElementById('manual-chapters');
  if (!toggle || !chapters) return;

  const narrow = window.matchMedia('(max-width: 1000px)');
  toggle.hidden = false;
  document.documentElement.classList.add('manual-enhanced');

  function setOpen(open) {
    toggle.setAttribute('aria-expanded', String(open));
    chapters.hidden = narrow.matches && !open;
  }

  function resetMenu() {
    // Desktop resizing must never leave the full chapter navigation hidden.
    setOpen(!narrow.matches);
  }

  toggle.addEventListener('click', () => {
    setOpen(toggle.getAttribute('aria-expanded') !== 'true');
  });
  toggle.closest('nav').addEventListener('keydown', event => {
    if (event.key === 'Escape' && narrow.matches && toggle.getAttribute('aria-expanded') === 'true') {
      setOpen(false);
      toggle.focus();
    }
  });
  narrow.addEventListener('change', resetMenu);
  resetMenu();

  // Open the advanced group when it contains the current page.
  document.querySelectorAll('.manual-reference').forEach(group => {
    if (group.querySelector('[aria-current="page"]')) group.open = true;
  });

  // A visible hint accompanies the shortcut; native browser search still works.
  const search = document.querySelector('#searchbox input[name="q"]');
  if (search) {
    search.setAttribute('aria-label', 'Search the manual');
    search.placeholder = 'Search the manual…';
    search.setAttribute('aria-keyshortcuts', '/');
    const hint = document.createElement('span');
    hint.className = 'search-shortcut';
    hint.textContent = 'Press / to search';
    search.closest('form').after(hint);
    document.addEventListener('keydown', event => {
      const target = event.target;
      const editing = target instanceof Element && target.closest('input, textarea, select, [contenteditable]');
      if (event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey && !editing && !document.querySelector('dialog[open]')) {
        event.preventDefault();
        search.focus();
      }
    });
  }
});
