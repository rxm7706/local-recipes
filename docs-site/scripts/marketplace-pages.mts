/**
 * `pyforge.steward.marketplace_pages` for the Pages build and check.
 *
 * The same boolean `pyforge.core.flags.read_boolean` returns for this key:
 * `DISABLED` is off; an overlay variant wins; otherwise `defaultVariant`.
 * An unknown environment reads off (a bad environment never reads on).
 * A missing or unreadable flag tree reads off, so a fixture repo with no
 * `src/platform/config/` does not throw. A malformed overlay reads off too.
 */

import fs from 'node:fs';
import path from 'node:path';

/** `pyforge.steward.marketplace_pages`. Dev on, staging and production off, default off. */
export const MARKETPLACE_FLAG = 'pyforge.steward.marketplace_pages';

type FlagEntry = { state?: string; defaultVariant?: string };

function readJson(file: string): { present: boolean; value: unknown } {
  let text: string;
  try {
    text = fs.readFileSync(file, 'utf8');
  } catch (exc) {
    if ((exc as NodeJS.ErrnoException).code === 'ENOENT') {
      return { present: false, value: undefined };
    }
    return { present: true, value: undefined };
  }
  try {
    return { present: true, value: JSON.parse(text) as unknown };
  } catch {
    return { present: true, value: undefined };
  }
}

export function marketplacePagesEnabled(
  repoRoot: string,
  envName: string = process.env.PYFORGE_ENVIRONMENT || 'dev',
): boolean {
  if (!['dev', 'staging', 'production'].includes(envName)) {
    return false;
  }
  const flagsFile = readJson(path.join(repoRoot, 'src/platform/config/flags.json'));
  if (!flagsFile.present || flagsFile.value === undefined) {
    return false;
  }
  const flags = flagsFile.value as { flags?: Record<string, FlagEntry> };
  const entry = flags.flags?.[MARKETPLACE_FLAG];
  if (!entry || entry.state === 'DISABLED') {
    return false;
  }
  const overlaysFile = readJson(path.join(repoRoot, 'src/platform/config/flag-overlays.json'));
  if (overlaysFile.present && overlaysFile.value === undefined) {
    return false;
  }
  if (overlaysFile.present && overlaysFile.value !== undefined && typeof overlaysFile.value === 'object') {
    const overlays = overlaysFile.value as Record<string, Record<string, string>>;
    const variant = overlays[envName]?.[MARKETPLACE_FLAG];
    if (variant === 'on') {
      return true;
    }
    if (variant === 'off') {
      return false;
    }
  }
  return entry.defaultVariant === 'on';
}
