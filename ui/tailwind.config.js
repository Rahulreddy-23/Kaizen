/** @type {import('tailwindcss').Config} */
// Tokens are defined once here and mirrored as CSS variables in src/index.css (docs/design/DESIGN.md).
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Geist Variable", "Geist", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Helvetica Neue", "Arial", "sans-serif"],
        mono: ["Geist Mono", "ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      colors: {
        canvas: "#F4F6F9",
        surface: { DEFAULT: "#FFFFFF", 2: "#EDF1F6", 3: "#E3E9F1" },
        line: { DEFAULT: "#DCE3EC", 2: "#B8C4D4" },
        ink: { DEFAULT: "#0F1F35", 2: "#3D4F66", 3: "#5C6E86", 4: "#5C6E86" },
        brand: { 50: "#F3F6FB", 100: "#E8EEF8", 200: "#C9D6EC", 300: "#9DB3DA", 500: "#1F5AB0", 600: "#194890", 700: "#12305F", 800: "#0D2347", 900: "#091A35" },
        accent: { 50: "#FFF6EE", 100: "#FDEBDD", 200: "#F9CFAE", 400: "#F5924A", 500: "#F07822", 600: "#D9660F", 700: "#B5540C" },
        ok: { DEFAULT: "#1E7F4F", soft: "#E3F4EA", strong: "#155F3A" },
        warn: { DEFAULT: "#B7791F", soft: "#FBF1DC", strong: "#8A5A12" },
        bad: { DEFAULT: "#C13A2B", soft: "#FBE7E4", strong: "#8F2A1F" },
        // Classification and severity are meaning; never reuse these for decoration.
        cls: { exact: "#1E7F4F", equivalent: "#0E7C86", potential: "#B7791F", mismatch: "#C13A2B", missing: "#7E3AA6" },
        sev: { blocker: "#7A1F1F", major: "#C13A2B", minor: "#B7791F", info: "#194890" },
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
        xs: ["0.75rem", { lineHeight: "1rem" }],
        sm: ["0.8125rem", { lineHeight: "1.125rem" }],
        base: ["0.875rem", { lineHeight: "1.25rem" }],
        md: ["1rem", { lineHeight: "1.5rem" }],
        lg: ["1.125rem", { lineHeight: "1.625rem" }],
        xl: ["1.25rem", { lineHeight: "1.75rem" }],
        "2xl": ["1.375rem", { lineHeight: "1.75rem", letterSpacing: "-0.01em" }],
        "3xl": ["1.75rem", { lineHeight: "2.125rem", letterSpacing: "-0.015em" }],
        "4xl": ["2.375rem", { lineHeight: "2.5rem", letterSpacing: "-0.02em" }],
      },
      borderRadius: { sm: "6px", DEFAULT: "8px", md: "10px", lg: "12px", xl: "16px" },
      boxShadow: {
        pop: "0 12px 32px -12px rgba(15,31,53,0.28), 0 2px 6px rgba(15,31,53,0.08)",
        lift: "0 6px 18px -8px rgba(15,31,53,0.22), 0 1px 3px rgba(15,31,53,0.06)",
        ring: "0 0 0 2px #FFFFFF, 0 0 0 4px #F07822",
      },
      transitionTimingFunction: {
        out: "cubic-bezier(0.16, 1, 0.3, 1)",
        inout: "cubic-bezier(0.77, 0, 0.175, 1)",
      },
      keyframes: {
        rise: { from: { opacity: "0", transform: "translateY(6px)" }, to: { opacity: "1", transform: "translateY(0)" } },
        pop: { from: { opacity: "0", transform: "scale(0.97)" }, to: { opacity: "1", transform: "scale(1)" } },
        fade: { from: { opacity: "0" }, to: { opacity: "1" } },
        shimmer: { from: { backgroundPosition: "200% 0" }, to: { backgroundPosition: "-200% 0" } },
        fill: { from: { transform: "scaleX(0)" }, to: { transform: "scaleX(1)" } },
      },
      animation: {
        rise: "rise 220ms cubic-bezier(0.16, 1, 0.3, 1) both",
        pop: "pop 180ms cubic-bezier(0.16, 1, 0.3, 1) both",
        fade: "fade 160ms ease-out both",
        shimmer: "shimmer 1.6s linear infinite",
        fill: "fill 600ms cubic-bezier(0.16, 1, 0.3, 1) both",
      },
      maxWidth: { page: "1440px" },
    },
  },
  plugins: [],
};
