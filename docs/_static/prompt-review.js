// Read local saved evidence only. Text uses textContent, never HTML injection.
document.addEventListener('DOMContentLoaded', async () => {
  const root = document.getElementById('prompt-review');
  if (!root) return;
  const make = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };
  const download = (text, filename) => {
    const url = URL.createObjectURL(new Blob([text], {type: 'text/plain;charset=utf-8'}));
    const anchor = make('a'); anchor.href = url; anchor.download = filename;
    anchor.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  function block(title, value, filename, open = false) {
    const details = make('details'); details.open = open;
    details.append(make('summary', title));
    const text = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
    const tools = make('div', undefined, 'review-tools');
    const copy = make('button', 'Copy'); copy.type = 'button';
    const save = make('button', 'Download'); save.type = 'button';
    const pre = make('pre', text, 'review-text'); pre.tabIndex = 0;
    copy.addEventListener('click', async () => {
      try { await navigator.clipboard.writeText(text); copy.textContent = 'Copied'; }
      catch { const range = document.createRange(); range.selectNodeContents(pre);
        const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
        copy.textContent = 'Text selected; copy manually'; }
    });
    save.addEventListener('click', () => download(text, filename));
    tools.append(copy, save); details.append(tools, pre); return details;
  }
  try {
    const response = await fetch(root.dataset.source);
    if (!response.ok) throw new Error('Saved evidence could not be loaded.');
    const data = await response.json(); root.replaceChildren();
    const proposedResponse = await fetch(root.dataset.preview);
    if (!proposedResponse.ok) throw new Error('The proposed context preview could not be loaded.');
    const proposed = await proposedResponse.json();
    const label = make('label', 'Simulation date '); const select = make('select');
    select.id = 'review-date'; label.htmlFor = select.id;
    data.days.forEach(day => { const option = make('option', day.date); option.value = day.date; select.append(option); });
    const body = make('div'); body.setAttribute('aria-live', 'polite');
    root.append(label, select, body);
    function show() {
      const day = data.days.find(item => item.date === select.value); body.replaceChildren();
      body.append(make('p', 'Same: system, retrieved text, schema and model settings. Different: user state/history and replies.', 'review-parity'));
      body.append(block('Actual user prompt differences · exact changed lines', day.user_differences, `${day.date}-user-differences.json`));
      const columns = make('div', undefined, 'review-columns');
      [['anik', 'Anik'], ['hydroopsllm', 'HydroReOpLLM']].forEach(([key, name]) => {
        const record = day[key]; const section = make('section');
        section.append(make('h3', name));
        const prefix = `${day.date}-${key}`;
        section.append(block('System prompt · same', record.system, `${prefix}-system.txt`));
        section.append(block('User prompt · different state and history', record.user, `${prefix}-user.txt`));
        section.append(block('Retrieved text · same; also present in user prompt', record.retrieved, `${prefix}-retrieved.txt`));
        section.append(block('Raw JSON reply · different', record.raw_reply, `${prefix}-reply.json`, true));
        section.append(block('Reply schema · same', record.schema, `${prefix}-schema.json`));
        section.append(block('Provider model settings · same', record.model_settings, `${prefix}-settings.json`));
        section.append(block('Complete actual provider payload', record.payload, `${prefix}-payload.json`));
        section.append(block('Source and SHA256 hashes', {source: record.source, line: record.source_line, sha256: record.sha256}, `${prefix}-source.json`));
        columns.append(section);
      });
      body.append(columns);
      body.append(block('Internal record · not sent to the LLM', day.internal_record_only, `${day.date}-internal-record.json`));
      body.append(block('Client timeout and retry settings', data.client_settings, 'client-settings.json'));
      const candidate = proposed.days.find(item => item.date === day.date);
      body.append(make('h3', 'Proposed addition · not sent to a model'));
      body.append(make('p', 'The text below is a separate preview. Historical requests above remain unchanged.'));
      body.append(block('Daily seasonal context · same text for both engines', candidate.added_context, `${day.date}-proposed-context.txt`));
      body.append(block('Proposed Anik user prompt', candidate.anik_user_preview, `${day.date}-anik-proposed-user.txt`));
      body.append(block('Proposed HydroReOpLLM user prompt', candidate.hydroopsllm_user_preview, `${day.date}-hydroopsllm-proposed-user.txt`));
    }
    select.addEventListener('change', show); show();
  } catch (error) { root.textContent = `${error.message} Use the complete evidence download below.`; }
});
