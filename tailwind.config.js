module.exports = {
  content: ["./templates/**/*.html", "./static/**/*.js", "./static/**/*.css"],
  safelist: [
    {
      pattern: /select2.*/, // همه کلاس‌های شروع شده با select2
    },
  ],
  theme: {
    extend: {
      colors: {
        formdata: "#cef3e6ff",
        formreport: "#0448b4ff",
      },
    },
  },
  plugins: [],
};
