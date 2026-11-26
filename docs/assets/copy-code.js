(() => {
  const content = document.getElementById("manual-content");
  if (!content) return;

  const chinese = content.lang === "zh-Hant";
  const labels = chinese
    ? { copy: "複製", copied: "已複製", selected: "已選取，請手動複製" }
    : { copy: "Copy", copied: "Copied", selected: "Selected. Copy manually." };

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
    button.textContent = labels.copy;

    const feedback = document.createElement("span");
    feedback.setAttribute("role", "status");

    let resetTimer = null;
    const setCopiedState = (statusText, isCopied) => {
      feedback.textContent = statusText;
      if (isCopied) {
        button.classList.add("is-copied");
        button.textContent = labels.copied;
      } else {
        button.classList.remove("is-copied");
        button.textContent = labels.copy;
      }
      if (resetTimer !== null) {
        window.clearTimeout(resetTimer);
      }
      resetTimer = window.setTimeout(() => {
        button.classList.remove("is-copied");
        button.textContent = labels.copy;
        feedback.textContent = "";
        resetTimer = null;
      }, 1600);
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
