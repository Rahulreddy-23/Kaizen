/** Mirror the calculator API bounds before changing its URL or claiming success. */
export function businessValueError(key: string, value: string): string | null {
  const number = Number(value);
  if (!value.trim() || !Number.isFinite(number)) return "Enter a finite number.";
  if (["reviewers", "skus_per_project", "projects_per_year"].includes(key) && !Number.isInteger(number)) return "Enter a whole number.";
  if (["baseline_minutes_per_sku", "reviewers", "skus_per_project"].includes(key) ? number <= 0 : number < 0) return "Enter a valid positive value for this field.";
  if (key === "target_reduction_pct" && number > 100) return "Enter a percentage from 0 to 100.";
  return null;
}
