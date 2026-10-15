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

/**
 * Loader validates block types; keep the collection schema loose for YAML shape drift -- but every section carries
 * `measured:`, the day its prose was last checked against the tree (Story 43.5), refused naming the section.
 */
const dossierSchema = z
  .object({ title: z.string(), sections: z.array(sectionSchema) })
  .passthrough()
  .superRefine((doc, ctx) => {
    doc.sections.forEach((section, index) => {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(String(section.measured ?? ''))) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['sections', index, 'measured'],
          message: `dossier section ${JSON.stringify(section.id)} has no measured: date (YYYY-MM-DD)`,
        });
      }
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
