document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-confirm]').forEach((element) => {
    element.addEventListener('submit', (event) => {
      const message = element.getAttribute('data-confirm') || 'Confirm action?';
      if (!window.confirm(message)) {
        event.preventDefault();
      }
    });
  });

  document.querySelectorAll('[data-auto-refresh]').forEach((element) => {
    const seconds = Number(element.getAttribute('data-auto-refresh') || '0');
    if (seconds > 0) {
      window.setTimeout(() => window.location.reload(), seconds * 1000);
    }
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
