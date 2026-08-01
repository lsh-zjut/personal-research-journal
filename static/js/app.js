document.querySelectorAll("[data-confirm]").forEach((button) => {
  button.addEventListener("click", (event) => {
    if (!window.confirm(button.dataset.confirm)) event.preventDefault();
  });
});

const dateInput = document.querySelector("[data-date-navigate]");
if (dateInput) {
  dateInput.addEventListener("change", () => {
    if (dateInput.value) window.location.href = `/?date=${encodeURIComponent(dateInput.value)}`;
  });
}

const imageInput = document.querySelector("#image-input");
const fileSummary = document.querySelector("#file-summary");
const uploadZone = document.querySelector("#upload-zone");

function updateFileSummary() {
  if (!imageInput || !fileSummary) return;
  const files = Array.from(imageInput.files);
  fileSummary.textContent = files.length ? `已选择 ${files.length} 张图片` : "";
}

if (imageInput && uploadZone) {
  imageInput.addEventListener("change", updateFileSummary);
  ["dragenter", "dragover"].forEach((eventName) => {
    uploadZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      uploadZone.classList.add("dragging");
    });
  });
  ["dragleave", "drop"].forEach((eventName) => {
    uploadZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      uploadZone.classList.remove("dragging");
    });
  });
  uploadZone.addEventListener("drop", (event) => {
    if (event.dataTransfer.files.length) {
      imageInput.files = event.dataTransfer.files;
      updateFileSummary();
    }
  });
}

window.setTimeout(() => {
  document.querySelectorAll(".flash").forEach((flash) => flash.remove());
}, 3600);
