"""Scope normalization for mempalace-router."""

from mempalace_router.config import Targets


class ScopeError(ValueError):
    """Raised when scope normalization fails."""

    def __init__(self, code: str, message: str):
        """Initialize ScopeError with code and message.

        Args:
            code: Error code (e.g., 'unknown_target', 'cross_company_scope')
            message: Human-readable error message
        """
        super().__init__(message)
        self.code = code


def normalize_scope(scope: list[str] | None, targets: Targets) -> tuple[list[str], list[str]]:
    """Normalize a scope into an ordered list of target names.

    Args:
        scope: List of target names to include, or None/[].
        targets: The Targets configuration object.

    Returns:
        Tuple of (ordered_targets, notes) where:
        - ordered_targets[0] is always targets.local.name
        - company (if any) is second
        - notes contains 'local added to scope' if local was omitted by caller

    Raises:
        ScopeError: If scope contains unknown targets or multiple distinct companies.
    """
    notes: list[str] = []

    # Handle None or empty list
    if not scope:
        return ([targets.local.name], [])

    # Check for unknown targets
    for name in scope:
        if name not in targets.by_name:
            raise ScopeError("unknown_target", f"Unknown target: {name}")

    # Remove duplicates while preserving order
    seen = set()
    unique_scope = []
    for name in scope:
        if name not in seen:
            unique_scope.append(name)
            seen.add(name)

    # Check if local is in scope
    local_name = targets.local.name
    if local_name not in unique_scope:
        # Add local and record note
        unique_scope.insert(0, local_name)
        notes.append("local added to scope")
    else:
        # Move local to front if it's not already
        unique_scope.remove(local_name)
        unique_scope.insert(0, local_name)

    # Collect distinct companies (excluding local)
    companies_in_scope = set()
    for name in unique_scope:
        if name != local_name:
            target = targets.by_name[name]
            if target.kind == "company":
                companies_in_scope.add(target.company)

    # Check for multiple companies
    if len(companies_in_scope) > 1:
        raise ScopeError("cross_company_scope", f"Cannot mix multiple companies: {companies_in_scope}")

    # Build ordered result: local first, then company targets, then others
    result = [local_name]
    company_targets = []
    other_targets = []

    for name in unique_scope[1:]:  # Skip local (already first)
        target = targets.by_name[name]
        if target.kind == "company":
            company_targets.append(name)
        else:
            other_targets.append(name)

    # Append company targets first, then others
    result.extend(company_targets)
    result.extend(other_targets)

    return (result, notes)
