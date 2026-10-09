function confirmDanger(message) { return window.confirm(message); }
document.addEventListener('DOMContentLoaded', () => {
  const table = document.querySelector('#filterTable');
  const search = document.querySelector('#tableSearch');
  if (table && search) {
    search.setAttribute('aria-label', search.placeholder);
    const rows = Array.from(table.tBodies[0].rows);
    let page = 0;
    const size = 12;
    const bar = document.createElement('div'); bar.className = 'pagination';
    bar.innerHTML = '<span role="status" aria-live="polite"></span><div class="buttons"><button class="btn btn-ghost btn-small" type="button">Previous</button><button class="btn btn-ghost btn-small" type="button">Next</button></div>';
    table.parentElement.after(bar);
    const [prev, next] = bar.querySelectorAll('button');
    const status = document.querySelector('#statusFilter');
    const facility = document.querySelector('#facilityFilter');
    function draw() {
      const matched = rows.filter(row => row.textContent.toLowerCase().includes(search.value.toLowerCase()) && (!status?.value || row.cells[4]?.textContent.trim() === status.value) && (!facility?.value || row.cells[3]?.textContent.trim() === facility.value));
      page = Math.min(page, Math.max(0, Math.ceil(matched.length / size)-1));
      rows.forEach(row => row.hidden = true);
      matched.slice(page * size, (page+1)*size).forEach(row => row.hidden = false);
      bar.querySelector('[role="status"]').textContent = matched.length ? `${page*size+1}–${Math.min((page+1)*size,matched.length)} of ${matched.length} records` : 'No matching records. Try a different search or filter.';
      prev.disabled = page === 0; next.disabled = (page+1)*size >= matched.length;
    }
    [search,status,facility].filter(Boolean).forEach(el => el.addEventListener(el===search ? 'input' : 'change', () => {page=0;draw();}));
    prev.addEventListener('click',()=>{page--;draw();}); next.addEventListener('click',()=>{page++;draw();}); draw();
  }
  document.querySelector('#cardSearch')?.addEventListener('input', event => {
    document.querySelectorAll('[data-searchable]').forEach(card => card.hidden = !card.textContent.toLowerCase().includes(event.target.value.toLowerCase()));
  });
  // Associate legacy labels with their controls for keyboard and screen-reader users.
  document.querySelectorAll('.field,.form-card').forEach((field,index) => {
    const label=field.querySelector('label'); const control=field.querySelector('input:not([type="hidden"]),select,textarea');
    if (label && control && !label.htmlFor) {control.id ||= `legacy-control-${index}`;label.htmlFor=control.id;}
  });
  if (new URLSearchParams(location.search).get('saved')==='1') {
    const toast=document.createElement('div');toast.className='toast';toast.role='status';toast.textContent='Action completed successfully';document.body.append(toast);setTimeout(()=>toast.remove(),4500);
  }
});

document.addEventListener('DOMContentLoaded', () => {
  const themeButton = document.getElementById('themeToggle');
  function describeTheme() {
    const dark = document.documentElement.dataset.theme === 'dark';
    themeButton?.setAttribute('aria-label', `Switch to ${dark ? 'light' : 'dark'} mode`);
    themeButton?.setAttribute('aria-pressed', String(dark));
  }
  themeButton?.addEventListener('click', () => {
    const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('sunhaven-theme', theme); } catch (_) {}
    describeTheme();
  });
  describeTheme();
  document.getElementById('chartFacility')?.addEventListener('change', event => {
    document.querySelectorAll('.chart-view').forEach(view => view.hidden = view.dataset.facility !== event.target.value);
  });
  document.addEventListener('keydown', event => {
    if (event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey && !event.target.closest('input,textarea,select,[contenteditable]')) {
      const search = document.querySelector('.global-search input');
      if (search) { event.preventDefault(); search.focus(); }
    }
  });
  document.getElementById('checkAllSteps')?.addEventListener('click', () => {
    document.querySelectorAll('.checklist-row input:not(:disabled)').forEach(input => input.checked = true);
    document.getElementById('checkEvidence')?.focus();
  });
});

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('form[data-confirm]').forEach(form => form.addEventListener('submit', event => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  }));
  document.querySelectorAll('form[method="post"]:not(#assistantForm)').forEach(form => form.addEventListener('submit', event => {
    if (event.defaultPrevented || !form.checkValidity()) return;
    form.setAttribute('aria-busy','true');
    setTimeout(() => form.querySelectorAll('button[type="submit"],button:not([type])').forEach(b => b.disabled=true),0);
  }));
});

window.addEventListener('pageshow', () => {
  document.querySelectorAll('form[aria-busy="true"]').forEach(form => {
    form.removeAttribute('aria-busy');
    form.querySelectorAll('button[type="submit"],button:not([type])').forEach(button => button.disabled = false);
  });
});
