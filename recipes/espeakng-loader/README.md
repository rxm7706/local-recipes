# espeakng-loader (conda build)

Resolves the eSpeak NG shared library and data directory from the active conda
prefix, keeping upstream's public API (`get_library_path`, `get_data_path`,
`load_library`, `make_library_available`).

Unlike the PyPI wheels, it ships no bundled binaries and depends on the
`espeak-ng` conda package instead.
