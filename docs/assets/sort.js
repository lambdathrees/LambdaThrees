document.querySelectorAll('table.sortable').forEach(table => {
  const headers = table.querySelectorAll('thead th');
  let lastCol = -1, asc = true;

  headers.forEach((th, col) => {
    th.addEventListener('click', () => {
      asc = (col === lastCol) ? !asc : true;
      lastCol = col;

      headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
      th.classList.add(asc ? 'sort-asc' : 'sort-desc');

      const tbody = table.querySelector('tbody');
      const rows = Array.from(tbody.querySelectorAll('tr'));

      rows.sort((a, b) => {
        const va = a.cells[col]?.textContent.trim() ?? '';
        const vb = b.cells[col]?.textContent.trim() ?? '';
        const na = parseFloat(va), nb = parseFloat(vb);
        const cmp = (!isNaN(na) && !isNaN(nb)) ? na - nb : va.localeCompare(vb);
        return asc ? cmp : -cmp;
      });

      rows.forEach(r => tbody.appendChild(r));
    });
  });
});

// Per Game / Totals toggle
document.querySelectorAll('.vtog').forEach(btn => {
  btn.addEventListener('click', () => {
    const targetId = btn.dataset.viewShow;
    // find sibling toggle buttons (same .view-toggle parent)
    btn.closest('.view-toggle').querySelectorAll('.vtog').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    // find all view divs that share a common parent with the toggle
    const container = btn.closest('.page') || document.body;
    container.querySelectorAll('[id$="-view"]').forEach(el => {
      el.style.display = el.id === targetId ? '' : 'none';
    });
  });
});

// History season tabs
document.querySelectorAll('.season-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.season-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.season-section').forEach(s => s.classList.remove('visible'));
    tab.classList.add('active');
    const target = document.getElementById(tab.dataset.target);
    if (target) target.classList.add('visible');
  });
});
// Show first tab by default
const firstTab = document.querySelector('.season-tab');
if (firstTab) firstTab.click();
