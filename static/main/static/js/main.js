(function(){
  const yearSpans = document.querySelectorAll('[data-year]');
  yearSpans.forEach(el=> el.textContent = new Date().getFullYear());
})();

// Cursor Follower
document.addEventListener('DOMContentLoaded', function() {
  const cursorFollower = document.querySelector('.cursor-follower');

  document.addEventListener('mousemove', function(e) {
    cursorFollower.style.left = e.clientX - 10 + 'px';
    cursorFollower.style.top = e.clientY - 10 + 'px';
  });
});

