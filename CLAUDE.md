# CLAUDE.md

## GitHub account — use the personal account (`castorrr`)

This repo lives under `~/personal` and belongs to the personal GitHub account
**`castorrr`** (`castorrr/castorrr.github.io`). Always use `castorrr` for
pushing and for creating PRs here — never the machine's default `gh` account
`troyricafort`.

- **Push** already uses the personal identity: the remote is
  `git@github-personal:…`, and the `github-personal` SSH alias uses
  `~/.ssh/id_ed25519_personal`, which authenticates as `castorrr`. Leave it
  as-is; don't route pushes through the default `~/.ssh/id_ed25519` key
  (that one is `troyricafort`).
- **PRs**: `gh` defaults to the active account `troyricafort`, which is not a
  collaborator, so `gh pr create` fails with
  `GraphQL: must be a collaborator`. Switch first:

  ```bash
  gh auth switch --user castorrr   # create the PR as the personal account
  gh pr create ...
  gh auth switch --user troyricafort   # restore the default active account
  ```

The automated `chore: update claude activity …` data commits go straight to
`main`; other code changes land via PR.
