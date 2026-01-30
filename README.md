# Awa

**Awa** is an Awesome-style application recommendation list template and static webpage generator.

## Usage

1. Define your content in YAML files under `data/*.yml` according to the provided schema.
2. Create HTML templates using Jinja2 and place them in `templates/*.html.j2`.
3. Run `scripts/render.py` to render the pages.
   Generated files will be written to `docs/*.html`.

## License

- **Content**
  Files under `data/**`, `docs/**`, and textual content rendered from `templates/*.html.j2` are licensed under **CC BY-NC-SA 4.0**
  (the license stated on the generated pages shall prevail).
- **Code and assets**
  Templates, schemas, scripts, and all other non-content materials are licensed under **MPL-2.0**.

## References

- SPDX License List — CC0-1.0
- Tocas UI — MIT
- Python dependencies — see `pyproject.toml`
