(() => {
  let last = 0;
  document.addEventListener('click', event => {
    const el = event.target.closest('a, button, input[type=submit]');
    if (!el || Date.now() - last < 300) return;
    const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value || document.cookie.split('; ').find(x => x.startsWith('csrftoken='))?.split('=')[1];
    if (!csrf) return;
    last = Date.now();
    // Prefer stable control identifiers; never read field values or answer content.
    const action = (el.id || el.getAttribute('name') || el.getAttribute('aria-label') || (el.tagName === 'A' ? 'link ' + new URL(el.href, location.href).pathname : el.textContent.trim())).slice(0,120);
    fetch('/activity/click/', {method:'POST',keepalive:true,headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify({path:location.pathname,action})}).catch(() => {});
  }, true);
})();
