console.log("Smart Airport platform loaded.");

setTimeout(() => {
    const alerts = document.querySelectorAll(".alert");

    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.display = "none";
        }, 4000);
    });
}, 100);
