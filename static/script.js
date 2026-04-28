document.addEventListener("DOMContentLoaded", function () {
    // LOADING ANIMATION
    const form = document.querySelector("form");
    const loader = document.getElementById("loader");
    
    if (form && loader) {
        form.addEventListener("submit", () => {
            loader.style.display = "flex";
        });
    }

    // ===============================
    // CHARTS (RESULT PAGE)
    // ===============================
    const resultsElement = document.getElementById("results-data");

    if (resultsElement) {

        const results = JSON.parse(resultsElement.textContent);

        const scoreCanvas = document.getElementById("scoreChart");
        const selectionCanvas = document.getElementById("selectionChart");

        if (scoreCanvas) {
            new Chart(scoreCanvas, {
                type: 'bar',
                data: {
                    labels: results.map(r => r.file),
                    datasets: [{
                        label: 'Score',
                        data: results.map(r => r.final_score),
                        backgroundColor: "#4cc9f0"
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            labels: { color: "#ffffff" }
                        }
                    },
                    scales: {
                        x: {
                            ticks: { color: "#ffffff" },
                            grid: { color: "rgba(255,255,255,0.1)" }
                        },
                        y: {
                            ticks: { color: "#ffffff" },
                            grid: { color: "rgba(255,255,255,0.1)" }
                        }
                    }
                }
            });
        }

        if (selectionCanvas) {
            new Chart(selectionCanvas, {
                type: 'doughnut',
                data: {
                    labels: ['Selected', 'Rejected'],
                    datasets: [{
                        data: [
                            results.filter(r => r.decision === "Selected").length,
                            results.filter(r => r.decision === "Rejected").length
                        ],
                        backgroundColor: [
                            "#00e676",
                            "#ff5252"
                        ]
                    }]
                },
                options: {
                    plugins: {
                        legend: {
                            labels: { color: "#ffffff" }
                        }
                    }
                }
            });
        }
    }


    // ===============================
    // DRAG & DROP (HOME PAGE SAFE)
    // ===============================
    const dropArea = document.getElementById("drop-area");
    const fileInput = document.querySelector("input[type='file']");
    const fileCount = document.getElementById("file-count");

    if (dropArea && fileInput) {

        dropArea.addEventListener("click", () => fileInput.click());

        dropArea.addEventListener("dragover", e => {
            e.preventDefault();
            dropArea.classList.add("drag-over");
        });

        dropArea.addEventListener("dragleave", () => {
            dropArea.classList.remove("drag-over");
        });

        dropArea.addEventListener("drop", e => {
            e.preventDefault();
            dropArea.classList.remove("drag-over");

            fileInput.files = e.dataTransfer.files;
            updateFileCount();
        });

        fileInput.addEventListener("change", updateFileCount);

        function updateFileCount() {
            fileCount.innerText = fileInput.files.length + " file(s) selected";
        }
    }

});

// ===============================
// DOWNLOAD BUTTON HANDLER (FIXED)
// ===============================
document.addEventListener("click", function(e) {
    if (e.target.classList.contains("download-btn")) {

        const candidateData = JSON.parse(e.target.dataset.candidate);

        fetch("/download_report", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(candidateData)
        })
        .then(res => res.blob())
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");

            a.href = url;
            a.download = "resume_report.pdf";
            a.click();

            window.URL.revokeObjectURL(url);
        });
    }
});

function downloadAllReports() {
    const results = JSON.parse(document.getElementById("results-data").textContent);

    fetch("/download_all_reports", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(results)
    })
    .then(res => res.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "all_reports.zip";
        a.click();
    });
}

function downloadAllReports() {
    const btn = document.querySelector(".download-all-btn");
    const originalText = btn.innerText;

    btn.innerText = "⏳ Preparing ZIP...";
    btn.disabled = true;

    const results = JSON.parse(document.getElementById("results-data").textContent);

    fetch("/download_all_reports", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(results)
    })
    .then(res => res.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "all_reports.zip";
        a.click();

        btn.innerText = originalText;
        btn.disabled = false;
    });
}

function toggleTheme() {
    document.body.classList.toggle("light-mode");
}