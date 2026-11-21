const serviceTabs = Array.from(document.querySelectorAll('[data-tab]'));

function selectServiceTab(selectedTab) {
  serviceTabs.forEach(tab => {
    const selected = tab === selectedTab;
    tab.classList.toggle('active', selected);
    tab.setAttribute('aria-selected', String(selected));
    tab.tabIndex = selected ? 0 : -1;
    document.getElementById(tab.getAttribute('aria-controls')).hidden = !selected;
  });
}

serviceTabs.forEach((tab, index) => {
  tab.addEventListener('click', () => selectServiceTab(tab));
  tab.addEventListener('keydown', event => {
    let nextIndex;
    switch (event.key) {
      case 'ArrowRight':
        nextIndex = (index + 1) % serviceTabs.length;
        break;
      case 'ArrowLeft':
        nextIndex = (index + serviceTabs.length - 1) % serviceTabs.length;
        break;
      case 'Home':
        nextIndex = 0;
        break;
      case 'End':
        nextIndex = serviceTabs.length - 1;
        break;
      default:
        return;
    }
    event.preventDefault();
    selectServiceTab(serviceTabs[nextIndex]);
    serviceTabs[nextIndex].focus();
  });
});

document.getElementById('year').textContent = new Date().getFullYear();
