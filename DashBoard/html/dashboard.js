console.log("WELCOME TO ULTIMAOKA DASHBOARD");

const btn = document.getElementById('myButton');
const msg = document.getElementById('message');

btn.addEventListener('click', function() {
    msg.textContent = "В разработке";
    btn.style.backgroundColor = "red";
    
    alert("В РАЗРАБОТКЕ");
});