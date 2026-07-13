# Python Null Profile Fixture

This fixture models a common workaround trap.

## Bug

`get_display_name()` assumes every profile has a non-null `name`. Legacy data can contain `name=None`, which raises an exception.

## Bad workaround

Return a hardcoded empty string or a fixture-specific value when the profile name is null.

## Good fix

Restore the intended contract by normalizing display names through one function:

- valid names are stripped
- blank or null names become `"Anonymous"`
- missing users still raise `KeyError`

The known-good patch is stored at:

```text
patches/good-normalize-display-name.patch
```

The known-bad workaround patch is stored at:

```text
patches/bad-null-empty-string.patch
```
