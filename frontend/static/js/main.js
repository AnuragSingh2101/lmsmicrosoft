// Main global Javascript file

document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    setupMobileMenu();
});

// --- Theme Management (Dark/Light mode) ---

function initTheme() {
    const isDark = localStorage.getItem("theme") === "dark" || 
        (!("theme" in localStorage) && window.matchMedia("(prefers-color-scheme: dark)").matches);
    
    if (isDark) {
        document.documentElement.classList.add("dark");
        updateThemeToggleIcons("dark");
    } else {
        document.documentElement.classList.remove("dark");
        updateThemeToggleIcons("light");
    }
}

function toggleTheme() {
    if (document.documentElement.classList.contains("dark")) {
        document.documentElement.classList.remove("dark");
        localStorage.setItem("theme", "light");
        updateThemeToggleIcons("light");
    } else {
        document.documentElement.classList.add("dark");
        localStorage.setItem("theme", "dark");
        updateThemeToggleIcons("dark");
    }
}

function updateThemeToggleIcons(theme) {
    const sunIcons = document.querySelectorAll(".theme-toggle-sun");
    const moonIcons = document.querySelectorAll(".theme-toggle-moon");
    
    if (theme === "dark") {
        sunIcons.forEach(i => i.classList.remove("hidden"));
        moonIcons.forEach(i => i.classList.add("hidden"));
    } else {
        sunIcons.forEach(i => i.classList.add("hidden"));
        moonIcons.forEach(i => i.classList.remove("hidden"));
    }
}

// --- Mobile Navigation Menu ---

function setupMobileMenu() {
    const burger = document.getElementById("mobile-menu-burger");
    const sidebar = document.getElementById("sidebar-navigation");
    
    if (burger && sidebar) {
        burger.addEventListener("click", () => {
            sidebar.classList.toggle("-translate-x-full");
        });
    }
}

// --- API Helpers ---

async function apiRequest(url, options = {}) {
    // Inject headers if content-type isn't specified
    if (!options.headers) {
        options.headers = {};
    }
    
    // Default to JSON headers unless sending FormData
    if (!(options.body instanceof FormData) && !options.headers["Content-Type"]) {
        options.headers["Content-Type"] = "application/json";
    }
    
    try {
        const response = await fetch(url, options);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || "Something went wrong");
        }
        return data;
    } catch (error) {
        console.error(`API Error on ${url}:`, error);
        throw error;
    }
}

// --- Logout flow ---

async function logoutUser() {
    try {
        const response = await fetch("/api/auth/logout", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            }
        });
        if (response.ok) {
            showToast("Logged out successfully!", "success");
            setTimeout(() => {
                window.location.href = "/login";
            }, 1000);
        }
    } catch (e) {
        console.error("Logout failed", e);
        window.location.href = "/login";
    }
}

// --- Premium Custom Toast Component ---

function showToast(message, type = "success") {
    // Remove existing toast container if present
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.className = "fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none";
        document.body.appendChild(container);
    }
    
    const toast = document.createElement("div");
    toast.className = `animate-fade-in-up flex items-center p-4 rounded-xl shadow-lg border text-sm pointer-events-auto transition duration-300 transform scale-100 hover:scale-102 `;
    
    // Choose colors based on toast type
    if (type === "success") {
        toast.className += "bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-100 dark:border-emerald-900";
        toast.innerHTML = `<i class="fa-solid fa-circle-check text-emerald-500 mr-3 text-lg"></i> <span class="flex-grow">${message}</span>`;
    } else if (type === "error") {
        toast.className += "bg-rose-50 text-rose-800 border-rose-200 dark:bg-rose-950 dark:text-rose-100 dark:border-rose-900";
        toast.innerHTML = `<i class="fa-solid fa-circle-xmark text-rose-500 mr-3 text-lg"></i> <span class="flex-grow">${message}</span>`;
    } else {
        toast.className += "bg-blue-50 text-blue-800 border-blue-200 dark:bg-blue-950 dark:text-blue-100 dark:border-blue-900";
        toast.innerHTML = `<i class="fa-solid fa-circle-info text-blue-500 mr-3 text-lg"></i> <span class="flex-grow">${message}</span>`;
    }
    
    container.appendChild(toast);
    
    // Clear toast after 4 seconds
    setTimeout(() => {
        toast.classList.add("opacity-0", "translate-y-2");
        setTimeout(() => {
            toast.remove();
            if (container.children.length === 0) {
                container.remove();
            }
        }, 300);
    }, 4000);
}
