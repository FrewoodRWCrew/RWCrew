// Copy a text to the clipboard and report how it went (it can be refused,
// e.g. on a page that isn't served over HTTPS).

export async function copyToClipboard(value: string, onSuccess: () => void, onError: () => void) {
  try {
    await navigator.clipboard.writeText(value);
    onSuccess();
  } catch {
    onError();
  }
}
