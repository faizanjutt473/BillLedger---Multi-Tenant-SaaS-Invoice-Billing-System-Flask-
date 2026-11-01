(function () {
  const tb = document.getElementById('lines');
  if (!tb) return;
  const taxEl = document.querySelector('[name=tax_rate]');
  const money = n => 'Rs ' + Math.round(n).toLocaleString('en-PK');

  function calc() {
    let sub = 0;
    tb.querySelectorAll('tr').forEach(r => {
      const a = (+r.querySelector('.q').value || 0) * (+r.querySelector('.p').value || 0);
      r.querySelector('.a').textContent = money(a);
      sub += a;
    });
    const tax = sub * (+taxEl.value || 0) / 100;
    document.getElementById('sub').textContent = money(sub);
    document.getElementById('taxv').textContent = money(tax);
    document.getElementById('tot').textContent = money(sub + tax);
  }

  function addRow() {
    const tr = document.createElement('tr');
    tr.innerHTML =
      '<td><input name="description" placeholder="Item or service" aria-label="Description"></td>' +
      '<td style="width:90px"><input name="quantity" type="number" min="0.01" step="0.01" value="1" class="q" aria-label="Quantity"></td>' +
      '<td style="width:140px"><input name="unit_price" type="number" min="0" step="0.01" value="0" class="p" aria-label="Unit price"></td>' +
      '<td class="r a" style="width:130px">Rs 0</td>' +
      '<td><button type="button" class="btn ghost rm" aria-label="Remove line">x</button></td>';
    tb.append(tr);
  }

  tb.addEventListener('input', calc);
  tb.addEventListener('click', e => {
    if (!e.target.classList.contains('rm')) return;
    if (tb.querySelectorAll('tr').length > 1) e.target.closest('tr').remove();
    else tb.querySelectorAll('input').forEach(i => { i.value = i.classList.contains('q') ? 1 : (i.classList.contains('p') ? 0 : ''); });
    calc();
  });
  taxEl.addEventListener('input', calc);
  document.getElementById('add').onclick = addRow;
  calc();
})();