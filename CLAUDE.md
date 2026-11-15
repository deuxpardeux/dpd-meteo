# Agent instructions for dpd-meteo

## Code graph and workflow maps (Deux par Deux)

Before reading more than three files, query Graphify first via the
`code_catalog.jsonl` asset on the `graphify-latest` release in
`deuxpardeux/dpd-tools`, then open only the files it names:

```bash
gh release download graphify-latest --repo deuxpardeux/dpd-tools --pattern code_catalog.jsonl --dir /tmp/graphify --clobber
rg -i 'dpd-meteo/' /tmp/graphify/code_catalog.jsonl
```

See dpd-tools `.claude/skills/graphify-query/SKILL.md` and `bridge/GRAPHIFY.md`.
The catalog refreshes at 06:35 and 18:35 UTC; sibling rows use `repo` and
`repo/path` labels. The dependency graph itself covers dpd-tools only.
If the release is unavailable or a file is absent, use a scoped local file
index or GitHub path search. Do not install Graphify MCP on W10.

Before changing any workflow or the routing, read the Archify map source first
in `deuxpardeux/dpd-tools`: `maps/build/build_maps.py`,
`maps/sources/workflows/`, `maps/sources/agents/`, `maps/sources/coverage/`, and
`maps/config/fleet.yaml` (dpd-tools PRs #1695/#1707).
