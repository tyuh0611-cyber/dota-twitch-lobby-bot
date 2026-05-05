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
});
