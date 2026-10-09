(() => {
  let theme = 'light';
  try { theme = localStorage.getItem('sunhaven-theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); } catch (_) {}
  document.documentElement.dataset.theme = theme === 'dark' ? 'dark' : 'light';
})();
