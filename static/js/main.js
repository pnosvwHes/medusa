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

  // Mobile menu toggle (with safety check)
  // const menuBtn = document.getElementById("mobile-menu-button");
  // const menu = document.getElementById("mobile-menu");

  // if (menuBtn && menu) {
  //   menuBtn.addEventListener("click", function () {
  //     menu.classList.toggle("hidden");
  //   });
  // }
});
