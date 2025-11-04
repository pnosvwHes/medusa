document.addEventListener("DOMContentLoaded", function () {
  function getJToday() {
    const g = new Date();
    const j = jalaali.toJalaali(g.getFullYear(), g.getMonth() + 1, g.getDate());
    return { jy: j.jy, jm: j.jm, jd: j.jd };
  }

  function jDaysInMonth(jy, jm) {
    return jalaali.jalaaliMonthLength(jy, jm);
  }

  const monthNames = [
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
  ];

  const weekNames = ["ش", "ی", "د", "س", "چ", "پ", "ج"];

  function buildCalendar(jy, jm, jd, input) {
    const daysInMonth = jDaysInMonth(jy, jm);
    const gFirst = jalaali.toGregorian(jy, jm, 1);
    const firstDay = new Date(gFirst.gy, gFirst.gm - 1, gFirst.gd).getDay();
    const empty = firstDay === 6 ? 0 : firstDay + 1;

    let html = `
      <div class='text-center font-bold mb-2'>${monthNames[jm - 1]} ${jy}</div>
      <div class='jalali-weekdays grid text-center text-sm font-medium mb-1'>
        ${weekNames.map((d) => `<div>${d}</div>`).join("")}
      </div>
      <div class='jalali-days grid text-center text-sm'>
    `;

    for (let i = 0; i < empty; i++) html += `<div></div>`;
    for (let d = 1; d <= daysInMonth; d++) {
      const isToday = d === jd;
      html += `<div class="cursor-pointer select-none rounded p-1 hover:bg-blue-100 ${
        isToday ? "bg-blue-500 text-white" : ""
      }" data-day="${d}">${d}</div>`;
    }
    html += "</div>";

    const calendar = $(`
      <div class="jalali-calendar bg-white border rounded-lg shadow-lg p-3 absolute z-50">
        ${html}
      </div>
    `);

    // 👇 فیکس CSS grid
    calendar.find(".jalali-weekdays, .jalali-days").css({
      display: "grid",
      "grid-template-columns": "repeat(7, 1fr)",
      gap: "0.25rem",
    });

    $("body").append(calendar);
    const offset = input.offset();
    calendar.css({
      top: offset.top + input.outerHeight() + 4,
      left: offset.left,
    });

    calendar.on("click", "[data-day]", function () {
      const day = $(this).data("day");
      const g = jalaali.toGregorian(jy, jm, day);
      const pad = (n) => (n < 10 ? "0" + n : n);
      input.val(`${jy}/${pad(jm)}/${pad(day)}`);
      calendar.remove();
    });

    $(document).on("click.jalaliClose", function (e) {
      if (
        !calendar.is(e.target) &&
        calendar.has(e.target).length === 0 &&
        !input.is(e.target)
      ) {
        calendar.remove();
        $(document).off("click.jalaliClose");
      }
    });
  }

  $(".datepicker").each(function () {
    const input = $(this);
    input.attr("readonly", true).css("cursor", "pointer");
    input.on("click", function () {
      $(".jalali-calendar").remove();
      const { jy, jm, jd } = getJToday();
      buildCalendar(jy, jm, jd, input);
    });
  });

  $("select").select2({
    theme: "tailwindcss-3",
    width: "100%",
    placeholder: "انتخاب کنید...",
    allowClear: true,
  });

  feather.replace();
});
