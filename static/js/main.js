// main.js
document.addEventListener("DOMContentLoaded", function () {
  // فعالسازی Select2
  $("select").select2({
    theme: "tailwindcss-3",
    width: "100%",
    placeholder: "انتخاب کنید...",
    allowClear: true,
  });

  // Feather icons
  if (typeof feather !== "undefined") feather.replace();

  // فعالسازی دیت‌پیکر admin برای inputهای تاریخ
  if (typeof Calendar !== "undefined") {
    $(".datepicker").each(function () {
      const input = this;
      Calendar.setup({
        inputField: input.id,
        button: input.id,
        ifFormat: "%Y/%m/%d", // فرمت شمسی در ویرایش فاکتور
        showsTime: false,
      });
    });
  }
});
