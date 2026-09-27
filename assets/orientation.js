// Detect orientation and add class to body
function updateOrientationClass() {
  if (window.matchMedia('(orientation: landscape)').matches) {
    document.body.classList.add('landscape');
    document.body.classList.remove('portrait');
  } else {
    document.body.classList.add('portrait');
    document.body.classList.remove('landscape');
  }
}

// Run on load
updateOrientationClass();

// Run on resize
window.addEventListener('resize', updateOrientationClass);
