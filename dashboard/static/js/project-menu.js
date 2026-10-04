(() => {
  const bar = document.querySelector('#project-bar');
  const menu = document.querySelector('#project-menu');
  const dialog = document.querySelector('#project-site-dialog');
  const name = document.querySelector('#project-site-name');
  const source = document.querySelector('#project-site-source');
  const count = (n, singular, plural) => `${n ?? '—'} ${n === 1 ? singular : plural}`;
  // Mockup 4: the current row first (highlighted), the rest by name, ignoring case.
  const currentFirst = (rows, current, key) => [...rows].sort((a,b) =>
    Number(key(b) === current) - Number(key(a) === current)
    || String(key(a)).localeCompare(String(key(b)), undefined, {sensitivity: 'base', numeric: true}));
  // Opening always rebuilds, before the menu shows: hidden, it still holds the
  // last open's rows, and focus can still sit on one of its buttons. A state
  // update while it is open leaves a focused row alone.
  function render(opening = false) {
    if (!opening && (!menu.matches(':popover-open') || menu.contains(document.activeElement))) return;
    const locked = installation.supervisor?.mode && installation.supervisor.mode !== 'off';
    menu.innerHTML = `<h3>Project</h3>${currentFirst(installation.projects || [], installation.project, row => row.name).map(row => {
      const current = row.name === installation.project;
      return `<div class="project-menu-row ${current ? 'current' : ''}"><div><strong>${esc(row.name)}</strong><small>${count(row.seats,'Seat','Seats')} · ${count(row.devices,'device','devices')}</small></div><button data-project="${esc(row.name)}" data-action="${current ? 'rename' : 'open'}" ${locked ? 'disabled' : ''}>${current ? 'Rename' : 'Open'}</button></div>`;
    }).join('')}<button data-action="new-project" ${locked ? 'disabled' : ''}>New Project</button>
      <h3>Site</h3>${currentFirst(installation.sites || [], installation.current_site, site => site).map(site => {
        const current = site === installation.current_site;
        const room = installation.site_rooms?.[site];
        return `<div class="project-menu-row ${current ? 'current' : ''}"><div><strong>${esc(site)}</strong><small>${room ? `${room.width} × ${room.depth} m` : '—'}</small></div>${current ? '<span class="dim">current</span>' : `<button data-site="${esc(site)}" data-action="use">Use</button>`}</div>`;
      }).join('')}<button data-action="new-site">New Site</button>`;
  }
  menu.addEventListener('beforetoggle', event => {
    bar.setAttribute('aria-expanded', String(event.newState === 'open'));
    if (event.newState === 'open') {
      const rect = bar.getBoundingClientRect();
      menu.style.top = `${rect.bottom + 2}px`;
      menu.style.left = `${Math.max(8, Math.min(rect.left, innerWidth - 408))}px`;
      render(true);
    }
  });
  menu.addEventListener('click', event => {
    const button = event.target.closest('button[data-action]');
    if (!button) return;
    const action = button.dataset.action;
    menu.hidePopover();
    if (action === 'open') ws.send('open_project', {name:button.dataset.project});
    if (action === 'use') ws.send('select_site', {name:button.dataset.site});
    if (action === 'rename' || action === 'new-project') {
      const value = prompt(action === 'rename' ? 'Rename' : 'New Project', action === 'rename' ? installation.project : '');
      if (value) ws.send(action === 'rename' ? 'rename_project' : 'create_project', {name:value});
    }
    if (action === 'new-site') {
      dialog.querySelector('form').reset();
      source.innerHTML = (installation.sites || []).map(site => `<option value="${esc(site)}" ${site === installation.current_site ? 'selected' : ''}>${esc(site)}</option>`).join('');
      source.disabled = false;
      dialog.returnValue = '';
      dialog.showModal();
      name.focus();
    }
  });
  dialog.addEventListener('change', () => {
    source.disabled = dialog.querySelector('[name=start]:checked').value === 'empty';
  });
  document.querySelector('#project-site-cancel').onclick = () => dialog.close('cancel');
  dialog.addEventListener('close', () => {
    if (dialog.returnValue === 'create') ws.send('create_site', {
      name:name.value, source:dialog.querySelector('[name=start]:checked').value === 'empty' ? null : source.value,
    });
    bar.focus();
  });
  window.ProjectMenu = {render};
})();
