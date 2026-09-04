"""Business-case calculator driven by actual run metrics. Baselines from the brief are configurable defaults;
per-row effort assumptions are explicit. If the tool does not reach the target, it says so."""

from dataclasses import dataclass, field

from kaizen.models import Run


@dataclass(frozen=True)
class BusinessAssumptions:
    baseline_minutes_per_sku: float = 60.0  # brief: 1 hour / SKU / reviewer
    hourly_rate: float = 37.5  # brief
    skus_per_project: int = 100  # brief
    projects_per_year: int = 20  # brief
    reviewers: int = 2  # facilitator + independent reviewer
    minutes_per_validation_row: float = 1.5  # reviewer reads evidence and decides
    minutes_per_cleared_row: float = 0.1  # reviewer skims an auto-cleared row
    target_reduction_pct: float = 50.0  # brief target


@dataclass
class BusinessCase:
    skus: int
    rows: int
    auto_cleared: int
    needs_validation: int
    estimated_minutes_per_sku: float
    minutes_saved_per_sku: float
    reduction_pct: float
    hours_saved_per_project: float
    annual_savings: float
    meets_target: bool
    baseline_minutes_per_sku: float
    hourly_rate: float
    skus_per_project: int
    projects_per_year: int
    reviewers: int
    assumptions: list[str] = field(default_factory=list)
    per_sku: dict[str, dict[str, float]] = field(default_factory=dict)
    # projection: strong fuzzy pairings (no discrepancy, score ≥ 0.95) that a reviewer typically confirms once
    # and saves as relationships; after that the next run auto-clears them
    confirmable_rows: int = 0
    needs_validation_after_confirmation: int = 0
    estimated_minutes_per_sku_after_confirmation: float = 0.0
    reduction_pct_after_confirmation: float = 0.0
    hours_saved_per_project_after_confirmation: float = 0.0
    annual_savings_after_confirmation: float = 0.0
    meets_target_after_confirmation: bool = False

    def to_dict(self) -> dict:
        return self.__dict__


REVIEWABLE_ROLES = ("item", "change")


def reviewable(run: Run):
    """Rows a reviewer actually works through: item comparisons and revision changes. Header, reference,
    coverage and exempt rows are shown but not counted as effort."""
    return [r for r in run.results if r.role in REVIEWABLE_ROLES]


def business_case(run: Run, a: BusinessAssumptions = BusinessAssumptions()) -> BusinessCase:
    skus = len(run.groups)
    rev = reviewable(run)
    rows = len(rev)
    needs = sum(1 for r in rev if r.requires_validation)
    cleared = rows - needs
    per_sku: dict[str, dict[str, float]] = {}
    for g in run.groups:
        rs = [r for r in rev if r.sku == g.sku]
        n = sum(1 for r in rs if r.requires_validation)
        c = len(rs) - n
        per_sku[g.sku] = {"rows": len(rs), "needs_validation": n, "auto_cleared": c, "estimated_minutes": round(n * a.minutes_per_validation_row + c * a.minutes_per_cleared_row, 1)}
    def estimate(n_needs: int, n_cleared: int):
        est_ = (n_needs * a.minutes_per_validation_row + n_cleared * a.minutes_per_cleared_row) / skus if skus else 0.0
        saved_ = a.baseline_minutes_per_sku - est_
        reduction_ = round(100 * saved_ / a.baseline_minutes_per_sku, 1) if a.baseline_minutes_per_sku else 0.0
        hours_ = round(saved_ * a.skus_per_project * a.reviewers / 60, 1)
        return round(est_, 2), round(saved_, 2), reduction_, hours_, round(hours_ * a.hourly_rate * a.projects_per_year, 2)

    est, saved, reduction, hours_project, annual = estimate(needs, cleared)
    confirmable = sum(1 for r in rev if r.requires_validation and r.classification.value == "POTENTIAL" and not r.discrepancies and (r.score or 0) >= 0.95)
    est2, _, reduction2, hours2, annual2 = estimate(needs - confirmable, cleared + confirmable)
    assumptions = [
        f"Baseline {a.baseline_minutes_per_sku:g} minutes per SKU per reviewer, {a.reviewers} reviewers (brief).",
        f"{a.minutes_per_validation_row:g} minutes per row needing validation; {a.minutes_per_cleared_row:g} minutes per auto-cleared row (skim).",
        f"Project = {a.skus_per_project} SKUs; {a.projects_per_year} projects per year; ${a.hourly_rate:g}/hour (brief).",
        "Rows and validation counts come from this run; nothing is assumed about accuracy.",
        f"Projection (not a measurement): {confirmable} POTENTIAL rows are strong pairings (score ≥ 0.95, no discrepancy); once a reviewer confirms them as relationships the next run auto-clears them.",
    ]
    return BusinessCase(skus, rows, cleared, needs, est, saved, reduction, hours_project, annual, reduction >= a.target_reduction_pct, a.baseline_minutes_per_sku, a.hourly_rate, a.skus_per_project, a.projects_per_year, a.reviewers, assumptions, per_sku, confirmable, needs - confirmable, est2, reduction2, hours2, annual2, reduction2 >= a.target_reduction_pct)
