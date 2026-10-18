(function () {
  'use strict';
  const P = window.Pentest;

  /** 动态数据始终作为文本，不解释为 HTML。 */
  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text);
    return node;
  }

  function empty(title, detail) {
    const box = el('div', 'empty');
    box.append(el('h3', '', title));
    if (detail) box.append(el('p', 'muted', detail));
    return box;
  }

  function section(title, subtitle) {
    const box = el('section', 'section');
    const heading = el('div', 'section-heading');
    heading.append(el('h2', '', title));
    if (subtitle) heading.append(el('p', 'muted', subtitle));
    box.append(heading);
    return box;
  }

  function badge(text, tone) {
    return el('span', `badge tone-${tone}`, text);
  }

  function field(title, value, code = false) {
    const box = el('div', 'field');
    box.append(el('h4', '', title));
    box.append(el(code ? 'pre' : 'p', code ? 'code' : 'multiline', value || '未记录'));
    return box;
  }

  function list(values, fallback = '未记录') {
    if (!values?.length) return el('p', 'muted', fallback);
    const node = el('ul', 'text-list');
    values.forEach(value => node.append(el('li', 'multiline', value)));
    return node;
  }

  function evidence(refs) {
    const box = el('div', 'evidence');
    box.append(el('span', 'muted', '证据引用：'));
    box.append(el('span', 'mono', refs?.join(' · ') || '未记录'));
    return box;
  }

  function select(label, id, options, selected, onChange) {
    const wrapper = el('label', 'control');
    wrapper.append(el('span', '', label));
    const node = el('select');
    node.id = id;
    Object.entries(options).forEach(([value, text]) => {
      const option = el('option', '', text);
      option.value = value;
      node.append(option);
    });
    node.value = selected;
    node.addEventListener('change', () => onChange(node.value));
    wrapper.append(node);
    return wrapper;
  }

  function pager(result, id, onChange) {
    const box = el('div', 'pager');
    box.append(el('span', 'muted', `共 ${result.total} 条 · 第 ${result.page} / ${result.pages} 页`));
    [['上一页', -1], ['下一页', 1]].forEach(([label, delta]) => {
      const button = el('button', 'button small', label);
      button.id = `${id}-${delta === -1 ? 'previous' : 'next'}`;
      button.disabled = delta === -1 ? result.page <= 1 : result.page >= result.pages;
      button.addEventListener('click', () => onChange(result.page + delta));
      box.append(button);
    });
    return box;
  }

  function table(headers, rows) {
    const wrap = el('div', 'table-wrap');
    const node = el('table');
    const head = el('thead');
    const tr = el('tr');
    headers.forEach(title => { const th = el('th', '', title); th.scope = 'col'; tr.append(th); });
    head.append(tr);
    const body = el('tbody');
    rows.forEach(cells => {
      const row = el('tr');
      cells.forEach(value => {
        const td = el('td');
        td.append(value instanceof Node ? value : document.createTextNode(String(value ?? '—')));
        row.append(td);
      });
      body.append(row);
    });
    node.append(head, body);
    wrap.append(node);
    return wrap;
  }

  P.dom = { el, empty, section, badge, field, list, evidence, select, pager, table };
}());
