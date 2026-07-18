// esbuild bundle entrypoint (Story G1, FR-14).
//
// `@duckdb/duckdb-wasm`'s browser ESM (`duckdb-browser.mjs`) imports the bare
// specifier `apache-arrow`, which a raw <script type="module"> cannot resolve
// over a static host. Bundling this one re-export with esbuild inlines
// apache-arrow into a single self-contained module the page can import with no
// import-map and no bare specifiers — the load-bearing step that lets the whole
// query surface run client-side with NO backend and NO CDN.
export * from "@duckdb/duckdb-wasm";
