 function showTab(tab) {
        document.getElementById('login-panel').classList.remove('active');
        document.getElementById('signup-panel').classList.remove('active');
        document.getElementById('tab-login').classList.remove('active');
        document.getElementById('tab-signup').classList.remove('active');

        document.getElementById(tab + '-panel').classList.add('active');
        document.getElementById('tab-' + tab).classList.add('active');
    }