# Example Recipes

Working example recipes demonstrating various conda-forge patterns.

## Examples

| Example | Description | Format |
|---------|-------------|--------|
| `python-simple/` | Basic Python noarch package | v1 |
| `python-compiled/` | Python with C extension | v1 |
| `rust-cli/` | Rust command-line tool | v1 |
| `c-library/` | CMake-based C library | v1 |
| `multi-output/` | Library + Python bindings | v1 |

## Usage

### Build an Example

```bash
# Using rattler-build
rattler-build build -r examples/python-simple/recipe.yaml -c conda-forge

# Using conda-build (for meta.yaml examples)
conda-build examples/python-simple -c conda-forge
```

### Use as Template

```bash
# Copy and customize
cp -r examples/python-simple recipes/my-package
# Edit recipe.yaml with your package details
```

## Example Details

### python-simple

A minimal Python noarch package demonstrating:
- CFEP-25 python_min compliance
- pip_check in tests
- Proper license handling

### python-compiled

Python package with C extension showing:
- Compiler requirements
- Cross-compilation support
- NumPy API usage

### rust-cli

Rust CLI application with:
- Cargo license bundling
- Cross-platform support
- Binary testing

### c-library

CMake-based C library showing:
- run_exports for ABI
- Header installation
- Library testing

### multi-output

Split package demonstrating:
- Shared cache section
- Subpackage pinning
- Separate tests per output
