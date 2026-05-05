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

  document.querySelectorAll('.editable').forEach((cell) => {
    cell.title = 'Double-click to edit';
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

      const save = () => {
        const newValue = input.value.trim();
        const name = cell.getAttribute('data-name');
        const row = cell.closest('tr');
        const form = row ? row.querySelector('.inline-save-form') : null;
        if (form && name) {
          const hidden = form.querySelector(`input[name="${name}"]`);
          if (hidden) hidden.value = newValue;
        }
        cell.textContent = newValue;
        cell.classList.add('edited');
      };

      input.addEventListener('blur', save);
      input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
          event.preventDefault();
          input.blur();
        }
        if (event.key === 'Escape') {
          event.preventDefault();
          cell.textContent = oldValue;
        }
      });
    });
  });
});
