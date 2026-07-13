# Short Namespace Variant

The default marketplace plugin name is `causal-repair`, so commands are namespaced like:

```text
/causal-repair:cr
```

If you want the namespace itself to be short, use a variant where `.claude-plugin/plugin.json` has:

```json
{
  "name": "cr"
}
```

Then the same alias skills and commands become:

```text
/cr:cr
/cr:fix
/cr:review
/cr:goal
```

This repository does not switch the default marketplace name to `cr` because `causal-repair` is clearer for discovery and installation.
