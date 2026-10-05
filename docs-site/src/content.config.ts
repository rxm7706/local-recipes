import { defineCollection } from 'astro:content';
import { docsSchema } from '@astrojs/starlight/schema';

import { shelfDocsLoader } from './loaders/shelf-docs-loader';

export const collections = {
  docs: defineCollection({
    loader: shelfDocsLoader(),
    schema: docsSchema(),
  }),
};
