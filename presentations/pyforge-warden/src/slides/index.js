import manifest from './manifest.json';

// Each slide's inner HTML is authored at 1920×1080 and imported as a raw
// string, then paired with its metadata (label, speaker notes, background).
const fragments = import.meta.glob('./fragments/*.html', {
  query: '?raw',
  import: 'default',
  eager: true,
});

export const SLIDE_WIDTH = 1920;
export const SLIDE_HEIGHT = 1080;

export const slides = manifest.map((meta, index) => {
  const key = `./fragments/${meta.id}.html`;
  const html = fragments[key];
  if (html == null) {
    throw new Error(`Missing slide fragment for "${meta.id}" (${key})`);
  }
  return { ...meta, index, number: index + 1, html };
});
