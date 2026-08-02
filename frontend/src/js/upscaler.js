/**
 * Texture upscaler UI helpers.
 */

export function previewFile(file, imgEl) {
  if (!file || !imgEl) return;
  const url = URL.createObjectURL(file);
  imgEl.src = url;
  imgEl.onload = () => URL.revokeObjectURL(url);
}
