# Apache Tika 3.2.3 Conda-Forge Recipe - Complete Guide

## Overview

This recipe builds Apache Tika 3.2.3 for conda-forge with **68 package outputs**:
- 63 individual dependency packages
- 5 Tika packages (core, parsers, app, all-app, metapackage)

All dependency versions are from `tika-parent-3.2.3.pom` and all SHA256 checksums have been verified directly from Maven Central.

## Quick Start

```bash
# Clone/copy the recipe
cd apache-tika-all-recipe

# Build with conda-build
conda-build . --channel conda-forge

# Or with boa (faster)
conda mambabuild . --channel conda-forge
```

## Files in This Recipe

```
apache-tika-all-recipe/
├── meta.yaml           # Main recipe (66 source JARs, 68 outputs)
├── tika.sh             # Unix CLI wrapper (uber-jar)
├── tika-modular.sh     # Unix CLI wrapper (modular)
├── tika.bat            # Windows CLI wrapper  
├── LICENSE             # Apache 2.0
└── APACHE_TIKA_CONDA_FORGE_COMPLETE.md  # This file
```

## Output Packages

### Tika Packages
| Package | Description |
|---------|-------------|
| **apache-tika-core** | Core library |
| **apache-tika-parsers** | Parser packages |
| **apache-tika-app** | Modular app (uses individual packages) |
| **apache-tika-all-app** | Standalone uber-jar with CLI |
| **apache-tika** | Metapackage (depends on apache-tika-app) |

### Individual Dependency Packages (63 packages)
All dependencies are available as individual conda packages with proper dependency chains.

## Dependency Versions (from tika-parent-3.2.3.pom)

| Package | Version | SHA256 (first 16 chars) |
|---------|---------|-------------------------|
| slf4j-api | 2.0.17 | 7b751d952061954d... |
| commons-io | 2.20.0 | df90bba0fe3cb586... |
| commons-lang3 | 3.18.0 | 4eeeae8d20c078ab... |
| commons-codec | 1.19.0 | 5c3881e4f556855e... |
| commons-collections4 | 4.5.0 | 00f93263c267be20... |
| commons-compress | 1.28.0 | e1522945218456f3... |
| commons-logging | 1.3.5 | 6d7a744e4027649f... |
| commons-csv | 1.14.1 | 32be0e1e76673092... |
| commons-cli | 1.10.0 | 1b273d92160b9fa6... |
| commons-exec | 1.5.0 | d52d35801747902... |
| guava | 33.4.8-jre | f3d7f57f67fd622f... |
| jackson-core | 2.20.0 | bc0cf46075877201... |
| jackson-annotations | 2.20 | 959a2ffb2d591436... |
| jackson-databind | 2.20.0 | a70e146a6bf2cba4... |
| pdfbox | 3.0.5 | f0e5d3a1e573c707... |
| fontbox | 3.0.5 | e8a62be2df27a0d4... |
| pdfbox-io | 3.0.5 | 6df3f3b4db4fd55e... |
| log4j-api | 2.24.3 | 5b4a0a0cd0e751de... |
| log4j-core | 2.24.3 | 7eb4084596ae25bd... |
| bcprov-jdk18on | 1.81 | 249f396412b0c0ce... |
| xmlbeans | 5.2.2 | 0fb2fa9e43800f04... |
| jsoup | 1.21.2 | f05496e255734759... |
| **tika-core** | **3.2.3** | 4b697ae09a76b501... |
| **tika-app** | **3.2.3** | 80c20c085e2c0976... |
| **tika-parsers** | **3.2.3** | 6c780c1bd3ef42d7... |

## Build Output

The recipe produces 68 conda packages:

- 63 individual dependency packages (slf4j-api, commons-io, guava, pdfbox, etc.)
- **apache-tika-core** - Core library
- **apache-tika-parsers** - Parser packages  
- **apache-tika-app** - Modular app using individual packages
- **apache-tika-all-app** - Standalone uber-jar
- **apache-tika** - Metapackage

## Usage After Installation

```bash
# Install modular version (uses individual packages)
conda install apache-tika -c conda-forge
tika --help

# Or install standalone uber-jar
conda install apache-tika-all-app -c conda-forge
tika-all --help

# Use CLI
tika --detect myfile.pdf
tika --text myfile.docx
tika --metadata myfile.jpg

# Install just core library for embedding
conda install apache-tika-core -c conda-forge
```

## Verification Commands

```bash
# Verify checksums manually (example for commons-io)
curl -sL https://repo1.maven.org/maven2/commons-io/commons-io/2.20.0/commons-io-2.20.0.jar | sha256sum
# Expected: df90bba0fe3cb586b7f164e78fe8f8f4da3f2dd5c27fa645f888100ccc25dd72

# Verify tika-app
curl -sL https://repo1.maven.org/maven2/org/apache/tika/tika-app/3.2.3/tika-app-3.2.3.jar | sha256sum
# Expected: 80c20c085e2c0976bbd55969e5bf90dda2b7155db31068639fbc871d0369e7e7
```

## Key Version Changes from Tika 3.0.0 to 3.2.3

| Dependency | 3.0.0 | 3.2.3 |
|------------|-------|-------|
| commons-io | 2.18.0 | 2.20.0 |
| commons-codec | 1.17.1 | 1.19.0 |
| commons-compress | 1.27.1 | 1.28.0 |
| commons-lang3 | 3.17.0 | 3.18.0 |
| guava | 33.3.1-jre | 33.4.8-jre |
| jackson | 2.18.0 | 2.20.0 |
| pdfbox | 3.0.3 | 3.0.5 |
| log4j | 2.24.1 | 2.24.3 |
| bcprov | 1.78.1 | 1.81 |
| jsoup | 1.18.1 | 1.21.2 |

## Troubleshooting

### SHA256 Mismatch Error
If you get a SHA256 mismatch, the JAR may have been updated on Maven Central. Re-fetch the checksum:
```bash
curl -sL "https://repo1.maven.org/maven2/GROUP/ARTIFACT/VERSION/ARTIFACT-VERSION.jar" | sha256sum
```

### Build Timeout
The tika-app JAR is ~54 MB. If download times out, increase timeout:
```bash
conda-build . --channel conda-forge --timeout 600
```

### Java Version
Tika 3.2.3 requires Java 17+. The recipe specifies `openjdk >=17` as a runtime dependency.

## Source

- Tika: https://github.com/apache/tika
- tika-parent-3.2.3.pom: https://repo1.maven.org/maven2/org/apache/tika/tika-parent/3.2.3/tika-parent-3.2.3.pom

## Maintainer

rxm7706

## License

Apache-2.0
