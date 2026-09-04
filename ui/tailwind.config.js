/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "Helvetica Neue", "Arial", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "Liberation Mono", "monospace"],
      },
      colors: {
        // Classification (meaning only)
        cls: { exact: "#15803d", equivalent: "#0f766e", potential: "#b45309", mismatch: "#b91c1c", missing: "#c2410c" },
        // Severity
        sev: { blocker: "#7f1d1d", major: "#b91c1c", minor: "#b45309", info: "#1d4ed8" },
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
    },
  },
  plugins: [],
};
