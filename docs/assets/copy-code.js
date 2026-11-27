(() => {
  const content = document.getElementById("manual-content");
  if (!content) return;

  const chinese = content.lang === "zh-Hant";
  const labels = chinese
    ? { copy: "複製", copied: "已複製", selected: "已選取，請手動複製" }
    : { copy: "Copy", copied: "Copied", selected: "Selected. Copy manually." };

  const copyIconSvg =
    '<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<rect x="5.5" y="5.5" width="8" height="8" rx="1.6"></rect>' +
    '<path d="M3.5 10.5H3a1.5 1.5 0 0 1-1.5-1.5V3A1.5 1.5 0 0 1 3 1.5h6A1.5 1.5 0 0 1 10.5 3v.5"></path>' +
    "</svg>";

  const checkIconSvg =
    '<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M3.2 8.4L6.4 11.6L12.8 4.8"></path>' +
    "</svg>";

  const renderButtonContent = (btn, iconSvg, text) => {
    btn.innerHTML = `<span class="copy-btn-inner">${iconSvg}<span>${text}</span></span>`;
  };

  for (const code of content.querySelectorAll("pre > code")) {
    const pre = code.parentElement;
    if (!pre || !pre.parentElement || pre.parentElement.classList.contains("code-block")) {
      continue;
    }

    const wrapper = document.createElement("div");
    wrapper.className = "code-block";

    const controls = document.createElement("div");
    controls.className = "code-controls";

    const langMatch = code.className.match(/\blanguage-([a-z0-9_+-]+)/i);
    if (langMatch) {
      const langLabel = document.createElement("span");
      langLabel.className = "code-lang";
      langLabel.textContent = langMatch[1].toUpperCase();
      controls.append(langLabel);
    }

    const button = document.createElement("button");
    button.type = "button";
    renderButtonContent(button, copyIconSvg, labels.copy);

    const feedback = document.createElement("span");
    feedback.setAttribute("role", "status");

    let resetTimer = null;
    let morphTimer = null;
    const setCopiedState = (statusText, isCopied) => {
      feedback.textContent = statusText;
      if (morphTimer !== null) window.clearTimeout(morphTimer);
      button.classList.add("is-morphing");
      morphTimer = window.setTimeout(() => {
        if (isCopied) {
          button.classList.add("is-copied");
          renderButtonContent(button, checkIconSvg, labels.copied);
        } else {
          button.classList.remove("is-copied");
          renderButtonContent(button, copyIconSvg, labels.copy);
        }
        button.classList.remove("is-morphing");
      }, 90);

      if (resetTimer !== null) {
        window.clearTimeout(resetTimer);
      }
      resetTimer = window.setTimeout(() => {
        button.classList.remove("is-copied", "is-morphing");
        renderButtonContent(button, copyIconSvg, labels.copy);
        feedback.textContent = "";
        resetTimer = null;
      }, 1700);
    };

    button.addEventListener("click", async () => {
      feedback.textContent = "";
      try {
        await navigator.clipboard.writeText(code.textContent);
        setCopiedState(labels.copied, true);
      } catch {
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(code);
        selection.removeAllRanges();
        selection.addRange(range);
        setCopiedState(labels.selected, false);
      }
    });

    controls.append(feedback, button);
    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.append(controls, pre);
  }
})();
