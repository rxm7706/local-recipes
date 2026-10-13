"""The #2721 backport: pwnlib refuses MIPS PLT emulation on unicorn 2.1.3 and 2.1.4."""
import types

import unicorn as U
from pwnlib.elf import plt

bad = (U.UC_VERSION_MAJOR, U.UC_VERSION_MINOR, U.UC_VERSION_PATCH) in {(2, 1, 3), (2, 1, 4)}
for arch, guarded in (("mips", bad), ("mips64", bad), ("amd64", False)):
    stub = types.SimpleNamespace(arch=arch)
    try:
        plt.prepare_unicorn_and_context(stub, {}, 0, b"")
    except OSError as exc:
        assert guarded, f"guard fired for {arch} on unicorn {U.__version__}: {exc}"
        assert "unicorn/issues/2134" in str(exc), exc
        print(f"{arch}: guard raised on unicorn {U.__version__}, as expected")
    except Exception as exc:  # past the guard: the stub has no ELF data
        assert not guarded, f"guard did not fire for {arch} on unicorn {U.__version__}: {exc!r}"
        print(f"{arch}: no guard on unicorn {U.__version__}, as expected")
    else:
        raise AssertionError(f"prepare_unicorn_and_context returned for a stub {arch} ELF")
