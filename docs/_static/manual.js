// Enlarge saved figures without changing their bytes or making a model request.
document.addEventListener('DOMContentLoaded', () => {
  const dialog = document.createElement('dialog');
  dialog.className = 'figure-dialog';
  dialog.setAttribute('aria-label', 'Figure viewer');
  const header = document.createElement('div');
  header.className = 'figure-toolbar';
  const title = document.createElement('span');
  const actual = document.createElement('button');
  actual.type = 'button';
  actual.textContent = 'Actual size';
  actual.setAttribute('aria-pressed', 'false');
  const close = document.createElement('button');
  close.type = 'button';
  close.textContent = 'Close';
  const viewport = document.createElement('div');
  viewport.className = 'figure-viewport';
  viewport.tabIndex = 0;
  viewport.setAttribute('aria-label', 'Figure; scroll to inspect at actual size');
  const full = document.createElement('img');
  viewport.append(full);
  header.append(title, actual, close);
  dialog.append(header, viewport);
  document.body.append(dialog);
  let opener;
  close.addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => opener?.focus());
  actual.addEventListener('click', () => {
    const enabled = viewport.classList.toggle('actual-size');
    actual.setAttribute('aria-pressed', String(enabled));
  });
  document.querySelectorAll('.body img').forEach(img => {
    // Linked badges and the cover already have a separate role in the manual.
    if (img.closest('a') || img.src.includes('hydroopslm-cover') || img.src.includes('docs-badge')) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'figure-open';
    button.setAttribute('aria-label', `Expand figure: ${img.alt || 'Figure'}`);
    img.before(button);
    button.append(img);
    button.addEventListener('click', () => {
      opener = button;
      title.textContent = img.alt || 'Figure';
      full.src = img.currentSrc || img.src;
      full.alt = img.alt;
      viewport.classList.remove('actual-size');
      actual.setAttribute('aria-pressed', 'false');
      dialog.showModal();
    });
  });
});

// Copy only the displayed block text. This never runs a command or a model.
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.highlight, pre.prompt-text').forEach(block => {
    const pre = block.matches('pre') ? block : block.querySelector('pre');
    if (!pre) return;
    let container = block;
    if (block.matches('pre')) {
      container = document.createElement('div');
      container.className = 'copy-block';
      block.before(container);
      container.append(block);
    }
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'copy-code';
    button.textContent = 'Copy';
    button.setAttribute('aria-label', 'Copy block to clipboard');
    button.setAttribute('aria-live', 'polite');
    container.append(button);
    button.addEventListener('click', async () => {
      try {
        if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
        await navigator.clipboard.writeText(pre.textContent);
        button.textContent = 'Copied';
      } catch {
        // Keep the original text selectable when browser clipboard access is denied.
        const range = document.createRange();
        range.selectNodeContents(pre);
        const selection = window.getSelection();
        selection?.removeAllRanges();
        selection?.addRange(range);
        button.textContent = 'Select and copy';
      }
      window.setTimeout(() => { button.textContent = 'Copy'; }, 1800);
    });
  });
});
