import { defineCollection, z } from 'astro:content';
import { i18nLoader } from '@astrojs/starlight/loaders';
import { docsSchema, i18nSchema } from '@astrojs/starlight/schema';

import { dossierLoader } from './loaders/dossier-loader';
import { shelfDocsLoader } from './loaders/shelf-docs-loader';

const EPIC_BLOCK_TYPES = [
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
] as const;

const blockSchema = z
  .object({
    type: z.enum(EPIC_BLOCK_TYPES),
  })
  .passthrough();

const sectionSchema = z
  .object({
    id: z.string(),
    blocks: z.array(blockSchema).optional(),
  })
  .passthrough();

const dossierSchema = z
  .object({
    title: z.string(),
    sections: z.array(sectionSchema),
  })
  .passthrough();

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
