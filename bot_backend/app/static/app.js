document.addEventListener('DOMContentLoaded', () => {
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
  if (csrfToken) {
    document.querySelectorAll('form[method="post"], form[method="POST"]').forEach((form) => {
      if (!form.querySelector('input[name="csrf_token"]')) {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'csrf_token';
        input.value = csrfToken;
        form.appendChild(input);
      }
    });
  }

  const showToast = (message, level = 'success') => {
    const root = document.querySelector('#toast-root');
    if (!root) return;
    const toast = document.createElement('div');
    toast.className = `toast ${level}`;
    toast.textContent = message;
    root.appendChild(toast);
    window.setTimeout(() => toast.classList.add('hide'), 2800);
    window.setTimeout(() => toast.remove(), 3500);
  };

  document.querySelectorAll('.toast').forEach((toast) => {
    window.setTimeout(() => toast.classList.add('hide'), 3800);
    window.setTimeout(() => toast.remove(), 4500);
  });

  document.querySelectorAll('[data-confirm]').forEach((element) => {
    element.addEventListener('submit', (event) => {
      const message = element.getAttribute('data-confirm') || 'Confirm action?';
      if (!window.confirm(message)) event.preventDefault();
    });
  });

  document.querySelectorAll('[data-auto-refresh]').forEach((element) => {
    const seconds = Number(element.getAttribute('data-auto-refresh') || '0');
    if (seconds > 0) window.setTimeout(() => window.location.reload(), seconds * 1000);
  });

  document.querySelectorAll('[data-stepper]').forEach((stepper) => {
    const input = stepper.querySelector('input[type="number"]');
    stepper.querySelectorAll('[data-step]').forEach((button) => {
      button.addEventListener('click', () => {
        if (!input) return;
        const step = Number(button.getAttribute('data-step') || '1');
        const min = input.min === '' ? -Infinity : Number(input.min);
        const max = input.max === '' ? Infinity : Number(input.max);
        const current = Number(input.value || '0');
        input.value = String(Math.min(max, Math.max(min, current + step)));
        input.dispatchEvent(new Event('change', { bubbles: true }));
      });
    });
  });

  const autosaveCell = async (cell, newValue, oldValue) => {
    const row = cell.closest('tr');
    const dotaId = row ? row.getAttribute('data-dota-id') : '';
    const field = cell.getAttribute('data-name');
    if (!row || !dotaId || !field) return false;
    if (newValue === oldValue) return true;

    cell.textContent = newValue;
    cell.classList.add('saving');
    row.classList.add('is-dirty');

    const body = new URLSearchParams();
    body.set('csrf_token', csrfToken);
    body.set('field', field);
    body.set('value', newValue);

    try {
      const response = await fetch(`/player/${encodeURIComponent(dotaId)}/field`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || 'Save failed');
      }
      cell.classList.remove('saving');
      cell.classList.add('edited');
      row.classList.remove('is-dirty');
      row.classList.add('is-saved');
      window.setTimeout(() => row.classList.remove('is-saved'), 900);
      showToast('Saved', 'success');
      return true;
    } catch (error) {
      cell.classList.remove('saving');
      cell.classList.add('save-error');
      cell.textContent = oldValue;
      row.classList.remove('is-dirty');
      showToast(error.message || 'Save failed', 'error');
      window.setTimeout(() => cell.classList.remove('save-error'), 1500);
      return false;
    }
  };

  document.querySelectorAll('.editable').forEach((cell) => {
    cell.title = 'Double-click to edit. Enter or click outside saves automatically.';
    cell.addEventListener('dblclick', () => {
      if (cell.querySelector('input')) return;
      const oldValue = cell.textContent.trim();
      const input = document.createElement('input');
      input.value = oldValue;
      input.className = 'inline-edit-input';
      cell.textContent = '';
      cell.appendChild(input);
      input.focus();
      input.select();

      let isClosing = false;
      const finish = async (shouldSave = true) => {
        if (isClosing) return;
        isClosing = true;
        const newValue = input.value.trim();
        if (!shouldSave) {
          cell.textContent = oldValue;
          return;
        }
        await autosaveCell(cell, newValue, oldValue);
      };

      input.addEventListener('blur', () => finish(true));
      input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
          event.preventDefault();
          finish(true);
        }
        if (event.key === 'Escape') {
          event.preventDefault();
          finish(false);
        }
      });
    });
  });
});
