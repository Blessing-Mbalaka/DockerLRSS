(function (root) {
  function next(value) {
    const input = String(value || '').trim().toUpperCase();
    if (!input) return 'A';
    if (!/^[A-Z]{1,10}$/.test(input)) return null;
    const letters = input.split('');
    let index = letters.length - 1;
    while (index >= 0 && letters[index] === 'Z') {
      letters[index] = 'A';
      index -= 1;
    }
    if (index >= 0) letters[index] = String.fromCharCode(letters[index].charCodeAt(0) + 1);
    else letters.unshift('A');
    return letters.length <= 10 ? letters.join('') : null;
  }
  root.LMSSetLetters = {next: next};
})(typeof window !== 'undefined' ? window : globalThis);
