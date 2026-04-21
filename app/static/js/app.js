const sidebarToggle = document.querySelector("[data-toggle-sidebar]");
const sidebar = document.getElementById("sidebar");

if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", () => {
        sidebar.classList.toggle("open");
    });
}

const dropzones = document.querySelectorAll("[data-dropzone]");

dropzones.forEach((dropzone) => {
    const fileSummary = dropzone.querySelector("[data-file-summary]");
    const fileInputs = dropzone.querySelectorAll("input[type='file']");

    const updateSummary = () => {
        const selected = [];
        fileInputs.forEach((input) => {
            if (input.files && input.files.length > 0) {
                selected.push(`${input.files.length} ${input.dataset.fileLabel || "file"} selected`);
            }
        });
        if (fileSummary) {
            fileSummary.textContent = selected.length ? selected.join(" • ") : "No files selected yet.";
        }
    };

    fileInputs.forEach((input) => {
        input.addEventListener("change", updateSummary);
    });

    ["dragenter", "dragover"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.add("dragover");
        });
    });

    ["dragleave", "drop"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.remove("dragover");
        });
    });
});

const loadingForms = document.querySelectorAll("[data-loading-form]");

loadingForms.forEach((form) => {
    form.addEventListener("submit", () => {
        const loadingIndicator = form.querySelector("[data-loading-indicator]");
        if (loadingIndicator) {
            loadingIndicator.hidden = false;
        }
    });
});

const statusPollTargets = document.querySelectorAll("[data-status-poll]");

statusPollTargets.forEach((target) => {
    const url = target.dataset.statusPoll;
    if (!url) {
        return;
    }

    const statusCopy = target.querySelector("[data-status-copy]");
    const intervalId = window.setInterval(async () => {
        try {
            const response = await fetch(url, { headers: { Accept: "application/json" } });
            if (!response.ok) {
                return;
            }
            const payload = await response.json();
            if (statusCopy) {
                if (payload.status === "queued") {
                    statusCopy.textContent = "Your project is queued and about to start processing...";
                } else if (payload.status === "processing") {
                    statusCopy.textContent = "Generating video and captions in the background...";
                } else if (payload.status === "uploading") {
                    statusCopy.textContent = "Uploading media links and finalizing your project...";
                } else if (payload.error_message) {
                    statusCopy.textContent = payload.error_message;
                }
            }

            if (payload.is_ready) {
                window.clearInterval(intervalId);
                window.location.href = payload.preview_url;
            }
            if (payload.status === "failed") {
                window.clearInterval(intervalId);
            }
        } catch (error) {
            console.error("Status polling failed", error);
        }
    }, 4000);
});
