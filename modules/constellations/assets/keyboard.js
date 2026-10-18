document.addEventListener('keydown', function (event) {
  if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) {
    return;
  }

  const target = event.target;
  if (target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) {
    return;
  }

  const input = document.querySelector('input#keyboard-nav, #keyboard-nav input');
  if (!input) {
    return;
  }

  event.preventDefault();
  const command = event.key === 'ArrowLeft' || event.key === 'ArrowUp' ? 'previous' : 'next';
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(input, command);
  input.dispatchEvent(new Event('input', { bubbles: true }));
});
