async function handleLogin() {
    const username = document.getElementById('login-id').value;
    const password = document.getElementById('login-pw').value;

    const res = await fetch('/api/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username, password})
    });
    const result = await res.json();
    
    if(result.success) {
        window.location.href = result.redirect; // 성공 시 main.html로 이동
    } else {
        alert(result.message);
    }
}
