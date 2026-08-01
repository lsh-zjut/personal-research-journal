(() => {
  const config = window.journalCalendar;
  if (!config) return;

  const grid = document.querySelector("#calendar-grid");
  const title = document.querySelector("#calendar-title");
  const selected = parseISO(config.selectedDate);
  const today = new Date();
  const recorded = new Set(config.entryDates);
  let visible = new Date(selected.getFullYear(), selected.getMonth(), 1);

  function parseISO(value) {
    const [year, month, day] = value.split("-").map(Number);
    return new Date(year, month - 1, day);
  }

  function iso(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function sameDay(first, second) {
    return first.getFullYear() === second.getFullYear()
      && first.getMonth() === second.getMonth()
      && first.getDate() === second.getDate();
  }

  function render() {
    title.textContent = `${visible.getFullYear()} 年 ${visible.getMonth() + 1} 月`;
    grid.replaceChildren();
    const weekday = (visible.getDay() + 6) % 7;
    const start = new Date(visible.getFullYear(), visible.getMonth(), 1 - weekday);

    for (let index = 0; index < 42; index += 1) {
      const day = new Date(start);
      day.setDate(start.getDate() + index);
      const value = iso(day);
      const button = document.createElement("button");
      button.type = "button";
      button.className = "calendar-day";
      button.textContent = day.getDate();
      button.setAttribute("aria-label", value);
      if (day.getMonth() !== visible.getMonth()) button.classList.add("outside");
      if (sameDay(day, today)) button.classList.add("today");
      if (sameDay(day, selected)) button.classList.add("selected");
      if (recorded.has(value)) button.classList.add("has-entry");
      button.addEventListener("click", () => {
        window.location.href = `${config.indexUrl}?date=${encodeURIComponent(value)}`;
      });
      grid.append(button);
    }
  }

  document.querySelector("#prev-month").addEventListener("click", () => {
    visible = new Date(visible.getFullYear(), visible.getMonth() - 1, 1);
    render();
  });
  document.querySelector("#next-month").addEventListener("click", () => {
    visible = new Date(visible.getFullYear(), visible.getMonth() + 1, 1);
    render();
  });
  render();
})();
