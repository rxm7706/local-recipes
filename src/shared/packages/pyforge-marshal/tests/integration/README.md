# tests/integration

Integration tests that drive the real CLI, `git` and subprocesses: the CLI
contract and idempotence harness, `marshal init`/`homes`/`preflight`/`teardown`
in a throwaway repo, the `local-recipes` empty-plan oracle, the seed egress
counter, the performance gates, the dispatch structure-graph layer against the
real `codegraph` binary, and the live PKCE login against compose Keycloak.
Cases dominated by real git/subprocess calls are marked `slow` and stay out of
the default `pyforge-marshal-test` task.
