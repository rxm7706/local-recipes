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

/** Loader validates block types; keep the collection schema loose for YAML shape drift. */
const dossierSchema = z.object({ title: z.string() }).passthrough();

const pagesOneGenerator = process.env.PYFORGE_PAGES_ONE_GENERATOR === '1';

export const collections = {
  docs: defineCollection({
    loader: shelfDocsLoader(),
    schema: docsSchema(),
  }),
  i18n: defineCollection({ loader: i18nLoader(), schema: i18nSchema() }),
  ...(pagesOneGenerator
    ? {
        dossier: defineCollection({
          loader: dossierLoader(),
          schema: dossierSchema,
        }),
      }
    : {}),
};
