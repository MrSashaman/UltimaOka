console.log("WELCOME TO ULTIMAOKA DASHBOARD");

const btn = document.getElementById('myButton');
const msg = document.getElementById('message');

btn.addEventListener('click', function() {
    msg.textContent = "В разработке";
    btn.style.backgroundColor = "red";
    
    alert("В РАЗРАБОТКЕ");
});

    function updateUsers() {
        const count = Math.floor(Math.random() * 5);
        document.getElementById('RandomNum').innerText = count.toLocaleString(); 
    }

    setInterval(updateUsers, 5000);

    updateUsers();