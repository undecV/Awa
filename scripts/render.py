"""Render HTML pages from templates and data files."""

import logging
import re
from datetime import datetime
from pathlib import Path

import bbcode
import frontmatter
import yaml
from jinja2 import (
    ChoiceLoader,
    DictLoader,
    Environment,
    FileSystemLoader,
    select_autoescape,
)
from markupsafe import Markup
from minify_html import minify
from rich.console import Console
from rich.logging import RichHandler

from .check_spdx import is_foss

console = Console()
print = console.print  # noqa: A001

logger = logging.getLogger(__name__)
rich_formatter = logging.Formatter("%(message)s")
rich_handler = RichHandler()
rich_handler.setFormatter(rich_formatter)
logger.addHandler(rich_handler)

LOG_LEVEL = logging.DEBUG
logger.setLevel(LOG_LEVEL)
for handler in logger.handlers:
    handler.setLevel(LOG_LEVEL)
ENCODING = "utf-8"

logger.debug("Logging now has Super Cow Powers!")


bbcode_parser = bbcode.Parser()
bbcode_parser.add_simple_formatter("s", "<del>%(value)s</del>")
bbcode_parser.add_simple_formatter("del", "<del>%(value)s</del>")


def is_licenses_foss(licenses: list[str]) -> bool:
    """Determine if all licenses in a list are open source."""
    is_foss_list = []
    for license_id in licenses:
        is_license_foss: bool
        match license_id:
            case "FOSS":
                is_license_foss = True
            case "Proprietary":
                is_license_foss = False
            case _:
                is_license_foss = is_foss(license_id)
        is_foss_list.append(is_license_foss)
    return all(is_foss_list)


def sanitize_id(value: str) -> str:
    """Sanitize a string into a safe identifier."""
    if not value:
        return ""

    value = value.strip().lower()
    value = re.sub(r'[<>#"%{}|\\^~\[\]`;/?:@=&]', "", value)
    value = re.sub(r"\s+", "_", value)
    return value


def normalize_nodes(
    nodes: list[dict[str, any]], *, parent: dict[str, any] | None = None
) -> list[dict[str, any]]:
    """Normalize a list of nodes."""
    for node in nodes:
        # Only the "application" type can be omitted.
        node_type = node.get("type", "application")
        for bbcode_field in ("comment", "note"):
            if node.get(bbcode_field):
                # bbcode.render_html returns safe HTML
                node[bbcode_field] = Markup(  # noqa: S704
                    bbcode_parser.format(node[bbcode_field])
                )

        if "id" not in node or not node["id"]:
            match node_type:
                case "folder":
                    base = node["name"]
                case "application":
                    base = "-".join((node["publisher"], node["name"]))
                case "reference":
                    base = "-".join(
                        (
                            node["publisher"],
                            node["name"],
                            "ref",
                            parent["id"],
                        )
                    )
                case _:
                    message = f'Unknown node type: "{node_type}".'
                    raise ValueError(message)
            node["id"] = sanitize_id(base)

        node["type"] = node_type

        match node_type:
            case "application":
                node["is_foss"] = is_licenses_foss(node.get("licenses"))

        if node.get("contents"):
            node["contents"] = normalize_nodes(node["contents"], parent=node)

    return nodes


def main() -> None:
    """Main entry point for the script."""
    root = Path(__file__).resolve().parents[1]
    templates_dir = root / "templates"
    docs_dir = root / "docs"
    data_dir = root / "data"

    logger.info("Project root: %r", root)
    logger.info("Project templates: %r", templates_dir)
    logger.info("Project docs: %r", docs_dir)
    logger.info("Project data: %r", data_dir)

    pages: dict[str, str] = {}
    page_specs: dict[str, dict[str, any]] = {}

    page_paths: list[Path] = templates_dir.glob("*.html.j2")
    for page_path in page_paths:
        logger.info("Processing page: %r", page_path)
        post = frontmatter.load(page_path)

        # Virtual name used by DictLoader; keep stable + unique.
        virtual_name = f"__pages__/{page_path.name}"
        logger.info("Page virtual template name: %r", virtual_name)

        pages[virtual_name] = post.content
        page_specs[virtual_name] = {
            "template_path": page_path,
            "metadata": post.metadata,
        }

    loader = ChoiceLoader(
        [
            DictLoader(pages),
            FileSystemLoader(str(templates_dir)),
        ]
    )
    environment = Environment(
        loader=loader,
        autoescape=select_autoescape(
            enabled_extensions=("html", "htm", "xml", "j2"),
            default_for_string=True,
            default=True,
        ),
    )

    for virtual_name, spec in page_specs.items():
        page_path: Path = spec["template_path"]
        metadata: dict[str, any] = spec["metadata"]

        data_file = Path(metadata.get("data"))
        data_path = (page_path.parent / data_file).resolve()
        contents = yaml.safe_load(data_path.read_text(encoding=ENCODING))
        context = {
            "contents": normalize_nodes(contents["contents"]),
            "page": {
                "template": str(page_path.relative_to(root)),
                "data": str(data_path.relative_to(root))
                if data_path.is_relative_to(root)
                else str(data_path),
            },
            "now": datetime.now().astimezone(),
        }

        stem = re.sub(r"\.html\.j2$", "", page_path.name)
        output_path = docs_dir / f"{stem}.html"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        template = environment.get_template(virtual_name)
        rendered = template.render(context)
        minified = minify(rendered, minify_css=True, minify_js=True)

        output_path.write_text(minified, encoding=ENCODING)
        logger.info("Wrote output: %r", output_path)


if __name__ == "__main__":
    main()
