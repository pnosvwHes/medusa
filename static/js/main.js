// main.js
document.addEventListener("DOMContentLoaded", function () {
  
  $("select").select2({
    theme: "tailwindcss-3",
    width: "100%",
    placeholder: "انتخاب کنید...",
    allowClear: true,
  });

  
  if (typeof feather !== "undefined") feather.replace();

  
  if (typeof Calendar !== "undefined") {
    $(".datepicker").each(function () {
      const input = this;
      Calendar.setup({
        inputField: input.id,
        button: input.id,
        ifFormat: "%Y/%m/%d", 
        showsTime: false,
      });
    });
  }
});
