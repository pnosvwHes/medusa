document.addEventListener("DOMContentLoaded", function () {
  // Persian datepicker
  $(".datepicker").persianDatepicker({
    format: "YYYY/MM/DD",
    autoClose: true,
    initialValue: false,
  });

  // Select2
  $("select").select2({
    theme: "tailwindcss-3",
    width: "100%",
    minimumResultsForSearch: 8,
    placeholder: "انتخاب کنید ....",
    allowClear: true,
  });

  // Feather icons
  feather.replace();

  // Mobile menu toggle
  document
    .getElementById("mobile-menu-button")
    .addEventListener("click", function () {
      document.getElementById("mobile-menu").classList.toggle("hidden");
    });
});
