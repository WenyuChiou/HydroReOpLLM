(() => {
  const content = document.getElementById("manual-content");
  if (!content) return;

  const chinese = content.lang === "zh-Hant";
  const labels = chinese
    ? { copy: "複製", copied: "已複製", selected: "已選取，請手動複製" }
    : { copy: "Copy", copied: "Copied", selected: "Selected. Copy manually." };

  for (const code of content.querySelectorAll("pre > code")) {
    const controls = document.createElement("div");
    controls.className = "code-controls";

    const button = document.createElement("button");
    button.type = "button";
    button.textContent = labels.copy;

    const feedback = document.createElement("span");
    feedback.setAttribute("role", "status");

    button.addEventListener("click", async () => {
      feedback.textContent = "";
      try {
        await navigator.clipboard.writeText(code.textContent);
        feedback.textContent = labels.copied;
      } catch {
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(code);
        selection.removeAllRanges();
        selection.addRange(range);
        feedback.textContent = labels.selected;
      }
    });

    controls.append(feedback, button);
    code.parentElement.before(controls);
  }
})();
