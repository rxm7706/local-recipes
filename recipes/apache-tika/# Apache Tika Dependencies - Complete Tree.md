# Apache Tika Dependencies - Complete Tree

## Overview
- **Total packages**: 61
- **External (non-Tika)**: 37 packages
- **Already on conda-forge or created**: slf4j-api, commons-io

## Dependency Tree by Level

### LEVEL 3 (Leaf nodes - no dependencies needed first)
These have no/minimal dependencies and should be created FIRST:

| Package | Version | Notes |
|---------|---------|-------|
| commons-codec:commons-codec | 1.17.1 | Apache Commons |
| commons-io:commons-io | 2.18.0 | Apache Commons |
| org.apache.commons:commons-lang3 | 3.16.0 | Apache Commons |
| org.apache.commons:commons-math3 | 3.6.1 | Apache Commons |
| org.apache.james:apache-mime4j-core | 0.8.12 | Email parsing |
| org.apache.james:apache-mime4j-dom | 0.8.12 | Email parsing |
| org.apache.poi:poi | 5.4.0 | Excel/Office base |
| org.apache.ant:ant | 1.8.1 | Build tool |

### LEVEL 2 (Depend on Level 3)
| Package | Version | Dependencies |
|---------|---------|--------------|
| com.adobe.xmp:xmpcore | 6.1.11 | - |
| com.github.virtuald:curvesapi | 1.08 | - |
| com.pff:java-libpst | 0.9.3 | - |
| info.picocli:picocli | 4.7.6 | - |
| org.apache.commons:commons-collections4 | 4.4 | - |
| org.apache.commons:commons-compress | 1.27.1 | commons-codec |
| org.apache.pdfbox:jempbox | 1.8.17 | - |
| org.apache.pdfbox:pdfbox-io | 3.2.3 | commons-io |
| org.apache.pdfbox:xmpbox | 3.0.5 | - |
| org.apache.poi:poi-ooxml-lite | 5.4.0 | poi |
| org.apache.poi:poi-scratchpad | 5.4.0 | poi |
| org.apache.xmlbeans:xmlbeans | 5.3.0 | - |
| org.slf4j:slf4j-api | 2.0.17 | slf4j-api|

### LEVEL 1 (Depend on Level 2)
| Package | Version | Key Dependencies |
|---------|---------|-----------------|
| com.drewnoakes:metadata-extractor | 2.19.0 | xmpcore |
| com.epam:parso | 2.0.14 | slf4j-api |
| com.googlecode.plist:dd-plist | 1.28 | - |
| org.apache.pdfbox:fontbox | 3.0.5 | commons-io |
| org.apache.pdfbox:jbig2-imageio | 3.0.4 | - |
| org.apache.pdfbox:pdfbox | 3.0.5 | fontbox, pdfbox-io, bcprov |
| org.apache.pdfbox:pdfbox-tools | 3.0.5 | pdfbox, picocli |
| org.apache.poi:poi-ooxml | 5.4.0 | poi, poi-ooxml-lite, xmlbeans |
| org.bouncycastle:bcprov-jdk18on | 1.79 | - |
| org.codelibs:jhighlight | 1.1 | - |
| org.jsoup:jsoup | 1.18.3 | - |
| org.ow2.asm:asm | 9.7.1 | - |
| org.tallison:jmatio | 1.5 | - |

### LEVEL 0 (Apache Tika modules)
| Package | Version |
|---------|---------|
| org.apache.tika:tika-core | 3.2.3 |
| org.apache.tika:tika-parser-*-module | 3.2.3 |
| org.apache.tika:tika-parsers-standard-package | 3.2.3 |

## Build Order (Bottom-Up)

1. **Wave 1** (No deps): commons-codec, commons-lang3, commons-math3, asm, jsoup, bcprov-jdk18on, dd-plist, jhighlight, jmatio, picocli, curvesapi, xmpcore, xmlbeans
2. **Wave 2** (Need Wave 1): commons-compress, commons-collections4, poi, fontbox, pdfbox-io, jempbox, xmpbox, poi-ooxml-lite, poi-scratchpad
3. **Wave 3** (Need Wave 2): pdfbox, metadata-extractor, poi-ooxml, apache-mime4j-core/dom, java-libpst
4. **Wave 4** (Need Wave 3): pdfbox-tools, jbig2-imageio
5. **Wave 5**: Tika modules
EOF

cat dependency-tree.md

Output
# Apache Tika Dependencies - Complete Tree

## Overview
- **Total packages**: 61
- **External (non-Tika)**: 37 packages
- **Already on conda-forge or created**: slf4j-api, commons-io

## Dependency Tree by Level

### LEVEL 3 (Leaf nodes - no dependencies needed first)
These have no/minimal dependencies and should be created FIRST:

| Package | Version | Notes |
|---------|---------|-------|
| commons-codec:commons-codec | 1.17.1 | Apache Commons |
| commons-io:commons-io | 2.18.0 | Apache Commons|
| org.apache.commons:commons-lang3 | 3.16.0 | Apache Commons |
| org.apache.commons:commons-math3 | 3.6.1 | Apache Commons |
| org.apache.james:apache-mime4j-core | 0.8.12 | Email parsing |
| org.apache.james:apache-mime4j-dom | 0.8.12 | Email parsing |
| org.apache.poi:poi | 5.4.0 | Excel/Office base |
| org.apache.ant:ant | 1.8.1 | Build tool |

### LEVEL 2 (Depend on Level 3)
| Package | Version | Dependencies |
|---------|---------|--------------|
| com.adobe.xmp:xmpcore | 6.1.11 | - |
| com.github.virtuald:curvesapi | 1.08 | - |
| com.pff:java-libpst | 0.9.3 | - |
| info.picocli:picocli | 4.7.6 | - |
| org.apache.commons:commons-collections4 | 4.4 | - |
| org.apache.commons:commons-compress | 1.27.1 | commons-codec |
| org.apache.pdfbox:jempbox | 1.8.17 | - |
| org.apache.pdfbox:pdfbox-io | 3.2.3 | commons-io |
| org.apache.pdfbox:xmpbox | 3.0.5 | - |
| org.apache.poi:poi-ooxml-lite | 5.4.0 | poi |
| org.apache.poi:poi-scratchpad | 5.4.0 | poi |
| org.apache.xmlbeans:xmlbeans | 5.3.0 | - |
| org.slf4j:slf4j-api | 2.0.17 | Apache Commons |

### LEVEL 1 (Depend on Level 2)
| Package | Version | Key Dependencies |
|---------|---------|-----------------|
| com.drewnoakes:metadata-extractor | 2.19.0 | xmpcore |
| com.epam:parso | 2.0.14 | slf4j-api |
| com.googlecode.plist:dd-plist | 1.28 | - |
| org.apache.pdfbox:fontbox | 3.0.5 | commons-io |
| org.apache.pdfbox:jbig2-imageio | 3.0.4 | - |
| org.apache.pdfbox:pdfbox | 3.0.5 | fontbox, pdfbox-io, bcprov |
| org.apache.pdfbox:pdfbox-tools | 3.0.5 | pdfbox, picocli |
| org.apache.poi:poi-ooxml | 5.4.0 | poi, poi-ooxml-lite, xmlbeans |
| org.bouncycastle:bcprov-jdk18on | 1.79 | - |
| org.codelibs:jhighlight | 1.1 | - |
| org.jsoup:jsoup | 1.18.3 | - |
| org.ow2.asm:asm | 9.7.1 | - |
| org.tallison:jmatio | 1.5 | - |

### LEVEL 0 (Apache Tika modules)
| Package | Version |
|---------|---------|
| org.apache.tika:tika-core | 3.2.3 |
| org.apache.tika:tika-parser-*-module | 3.2.3 |
| org.apache.tika:tika-parsers-standard-package | 3.2.3 |

## Build Order (Bottom-Up)

1. **Wave 1** (No deps): commons-codec, commons-lang3, commons-math3, asm, jsoup, bcprov-jdk18on, dd-plist, jhighlight, jmatio, picocli, curvesapi, xmpcore, xmlbeans
2. **Wave 2** (Need Wave 1): commons-compress, commons-collections4, poi, fontbox, pdfbox-io, jempbox, xmpbox, poi-ooxml-lite, poi-scratchpad
3. **Wave 3** (Need Wave 2): pdfbox, metadata-extractor, poi-ooxml, apache-mime4j-core/dom, java-libpst
4. **Wave 4** (Need Wave 3): pdfbox-tools, jbig2-imageio
5. **Wave 5**: Tika modules
