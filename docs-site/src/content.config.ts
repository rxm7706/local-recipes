import { defineCollection, z } from 'astro:content';
import { i18nLoader } from '@astrojs/starlight/loaders';
import { docsSchema, i18nSchema } from '@astrojs/starlight/schema';

import { dossierLoader } from './loaders/dossier-loader';
import { shelfDocsLoader } from './loaders/shelf-docs-loader';

const EPIC_BLOCK_TYPES = new Set([
  'lede',
  'prose',
  'h3',
  'table',
  'callout',
  'finding',
  'stats',
  'quote',
  'relations',
  'lattice',
  'engines',
  'chips',
  'note',
  'verify',
  'ci_surfaces',
]);

const blockSchema = z
  .object({
    type: z.string(),
  })
  .passthrough()
  .superRefine((block, ctx) => {
    if (!EPIC_BLOCK_TYPES.has(block.type)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: `unknown dossier block type ${JSON.stringify(block.type)}`,
      });
    }
  });

const sectionSchema = z
  .object({
    id: z.string(),
    blocks: z.array(blockSchema).optional(),
  })
  .passthrough();

type Stat = { label?: unknown; check?: unknown };

/**
 * Loader validates block types; keep the collection schema loose for YAML shape drift -- but every section carries
 * `measured:`, the day its prose was last checked against the tree (Story 43.5), and every stat, in the hero and in
 * every stats block, carries `check:`, so the measurer counts it (Story 51.1, CAP-46: a typed figure fails the build);
 * each refused naming the section (and the stat's label).
 */
const dossierSchema = z
  .object({ title: z.string(), sections: z.array(sectionSchema) })
  .passthrough()
  .superRefine((doc, ctx) => {
    const refuseTyped = (stats: unknown, where: string, path: (string | number)[]) => {
      ((Array.isArray(stats) ? stats : []) as Stat[]).forEach((stat, index) => {
        if (!stat?.check) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: [...path, index, 'check'],
            message: `dossier stat ${JSON.stringify(stat?.label)} in ${where} has no check: (a typed figure)`,
          });
        }
      });
    };
    refuseTyped(doc.stats, 'the hero', ['stats']);
    doc.sections.forEach((section, index) => {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(String(section.measured ?? ''))) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['sections', index, 'measured'],
          message: `dossier section ${JSON.stringify(section.id)} has no measured: date (YYYY-MM-DD)`,
        });
      }
      (section.blocks ?? []).forEach((block, b) => {
        if (block.type === 'stats') {
          const where = `section ${JSON.stringify(section.id)}`;
          refuseTyped(block.stats, where, ['sections', index, 'blocks', b, 'stats']);
        }
      });
    });
  });

export const collections = {
  docs: defineCollection({
    loader: shelfDocsLoader(),
    schema: docsSchema(),
  }),
  i18n: defineCollection({ loader: i18nLoader(), schema: i18nSchema() }),
  dossier: defineCollection({
    loader: dossierLoader(),
    schema: dossierSchema,
  }),
};
