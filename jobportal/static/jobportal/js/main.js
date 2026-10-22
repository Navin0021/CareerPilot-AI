
document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("search-form");

    if (!form) {
        return;
    }

    form.addEventListener("submit", function () {
        const button = form.querySelector("button[type='submit']");

        if (button) {
            button.textContent = "Searching...";
        }
    });
});
