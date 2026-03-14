# App spec schema

The MAS can compile an app spec JSON into backlog items.

## Supported top-level keys

- `app_name`
- `package_name`
- `screens`
- `features`
- `data_models`
- `integrations`
- `ads`
- `billing`
- `notes`

## Example

See `examples/app_spec.example.json`.

## Workflow

Compile spec only:

```bash
python mas_android_adk.py --app-spec examples/app_spec.example.json --compile-spec
```

Run autonomous mode against the compiled spec:

```bash
python mas_android_adk.py --app-spec examples/app_spec.example.json --autonomous
```

## Recommendation

Keep the framework locked to Kivy for now. Put all app identity and service IDs in `.env`, then use the spec to drive the backlog and Android build loop.
