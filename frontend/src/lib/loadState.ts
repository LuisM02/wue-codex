export function settledFailureMessage(
  labels: string[],
  results: PromiseSettledResult<unknown>[],
): string | null {
  const failures = results.flatMap((result, index) => {
    if (result.status === "fulfilled") return [];
    if (
      result.reason instanceof Error
      && "status" in result.reason
      && result.reason.status === 404
    ) return [];
    const reason = result.reason instanceof Error ? result.reason.message : String(result.reason);
    return [{ label: labels[index] ?? "saved data", reason }];
  });
  if (!failures.length) return null;

  const labelText = failures.map((failure) => failure.label).join(", ");
  const reasons = [...new Set(failures.map((failure) => failure.reason))].join(" · ");
  return `Could not load saved ${labelText}. ${reasons}`;
}
