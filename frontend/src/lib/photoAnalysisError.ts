import { ApiError } from "../services/apiClient";

/** Keep the rejection reason; distinguish input corrections from service faults. */
export function photoAnalysisError(reason: unknown): string {
  const detail = reason instanceof Error ? reason.message : "Photo analysis could not complete.";
  if (!(reason instanceof ApiError)) {
    return `${detail} Check that WUE is running and reachable before retrying.`;
  }
  if (reason.status === 422) {
    return `${detail} Check the named view, visible part boundaries, and entered dimensions before retrying. WUE has not generated a generic replacement.`;
  }
  if (reason.status === 409) {
    return `${detail} Complete the required photos, recognition, or measurements before retrying.`;
  }
  if (reason.status === 503 || reason.status === 504) {
    return `${detail} Check WUE's local AI service and retry when it is ready. Manually selecting a furniture type does not restore photo reconstruction.`;
  }
  if (reason.status === 502) {
    return `${detail} The AI service returned an unusable result; retry or report this message. Existing saved drawings have not been replaced by this failure.`;
  }
  return detail;
}
