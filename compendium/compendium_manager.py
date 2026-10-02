import json
import os
import re
import unicodedata
import weakref
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from settings.settings_manager import WWSettingsManager


class CompendiumEventBus:
    _instance = None

    def __init__(self):
        self.updated_listeners: list[Callable[[str], None]] = []
        self._weak_refs: weakref.WeakSet = weakref.WeakSet()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def add_updated_listener(self, callback: Callable[[str], None]):
        self.updated_listeners.append(callback)
        if hasattr(callback, '__self__'):
                self._weak_refs.add(callback.__self__)

    def remove_updated_listener(self, callback: Callable[[str], None]):
        """Safely remove a listener."""
        if callback in self.updated_listeners:
            self.updated_listeners.remove(callback)

    def notify_updated(self, project_name: str):
        self._cleanup_dead_listeners()
        for callback in self.updated_listeners:
            try:
                callback(project_name)
            except Exception as e:
                print(f"Error in compendium updated listener: {e}")
                self.remove_updated_listener(callback)

    def _cleanup_dead_listeners(self):
        """Remove listeners whose objects have been garbage collected."""
        to_remove = []
        for cb in self.updated_listeners:
            if hasattr(cb, '__self__') and cb.__self__ is None:
                to_remove.append(cb)
        for cb in to_remove:
            self.remove_updated_listener(cb)

class CompendiumManager:
    """Manages compendium data loading, retrieval, and reference parsing for a project."""

    SCHEMA_VERSION = 2
    CANON_STATUSES = ("Confirmado", "Rumor", "Planejado", "Descartado", "Contraditório")
    UNIVERSE_CATEGORIES = (
        ("Personagens", ("personagens", "characters"), ("Protagonistas", "Antagonistas", "Coadjuvantes", "Figurantes")),
        ("Worldbuilding", ("worldbuilding",), ("O mundo / planeta", "Países", "Continentes", "Regiões", "Lugares")),
        ("Organizações", ("organizações", "organizations", "organisations"), ("Política", "Facções", "Governos", "Guildas", "Religiões", "Exércitos")),
        ("Seres", ("seres", "species"), ("Raças", "Espécies", "Etnias", "Culturas", "Linhagens")),
        ("Sistemas e poderes", ("sistemas e poderes", "sistemas", "systems"), ("Magia", "Tecnologia", "Sistema de energia")),
        ("Itens e artefatos", ("itens e artefatos", "items", "artifacts"), ("Armas", "Relíquias", "Objetos")),
        ("Histórias e eventos", ("histórias e eventos", "events"), ()),
        ("Conceitos & lore", ("conceitos & lore", "lore", "concepts"), ()),
        ("Criaturas", ("criaturas", "creatures"), ()),
        ("Narrativa", ("narrativa", "narrative"), ()),
    )
    NOTEBOOK_FIELD_ALIASES = {
        "idade": "idade",
        "arquétipo": "arquetipo",
        "aparência": "aparencia",
        "aparencia fisica": "aparencia",
        "aparência física": "aparencia",
        "características": "caracteristicas",
        "caracteristicas fisicas": "caracteristicas",
        "características físicas": "caracteristicas",
        "deficiencia fisica": "caracteristicas",
        "deficiência física": "caracteristicas",
        "o conflito": "conflito",
        "conflito": "conflito",
        "vestimenta": "vestimenta",
        "personalidade": "personalidade",
        "ações principais": "acoes_principais",
        "história": "historia",
        "origem": "origem",
        "poderes": "habilidades",
        "habilidades": "habilidades",
        "limitações": "limites",
        "limites": "limites",
        "função": "funcao",
        "função narrativa": "funcao",
        "localização": "localizacao",
        "geografia": "geografia",
        "cultura": "cultura",
    }

    def __init__(self, project_name: str | None = None, event_bus: CompendiumEventBus | None = None):
        """
        Initialize the CompendiumManager with an optional project name.

        Args:
            project_name (str, optional): The name of the project. If None, uses a global compendium file.
        """
        self.project_name = project_name
        self.event_bus = event_bus
        self._filepath = self._get_filepath()
        self._ensure_file_exists()

    def _get_filepath(self) -> str:
        """
        Build the compendium file path based on the project name.

        Returns:
            str: Path to the compendium JSON file.
        """
        if self.project_name:
            return WWSettingsManager.get_project_relpath(self.project_name, "compendium.json")
        return os.path.join(os.getcwd(), "compendium.json")

    def _ensure_file_exists(self) -> None:
        """Ensure the compendium file exists, creating a default one if necessary."""
        if not os.path.exists(self._filepath):
            os.makedirs(os.path.dirname(self._filepath), exist_ok=True)
            self._save_data(self._default_data())

    def _default_data(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "universe": {"name": "", "relationships": []},
            "categories": [
                {
                    "name": name,
                    "entries": [],
                    "subcategories": [{"name": subcategory, "entries": []} for subcategory in subcategories],
                }
                for name, _aliases, subcategories in self.UNIVERSE_CATEGORIES
            ],
            "extensions": {"entries": {}},
        }

    def default_entry_metadata(self) -> dict[str, Any]:
        return {
            "details": "",
            "notebook": {},
            "tags": [],
            "relationships": [],
            "images": [],
            "canon": "Confirmado",
        }

    def _normalise_data(self, data: dict[str, Any]) -> bool:
        """Migrate legacy notes into a stable, relational universe data model."""
        changed = False
        if data.get("schema_version") != self.SCHEMA_VERSION:
            data["schema_version"] = self.SCHEMA_VERSION
            changed = True
        if not isinstance(data.get("universe"), dict):
            data["universe"] = {}
            changed = True
        data["universe"].setdefault("name", "")
        data["universe"].setdefault("relationships", [])
        data.setdefault("categories", [])
        data.setdefault("extensions", {"entries": {}})
        data["extensions"].setdefault("entries", {})

        category_names = {str(category.get("name", "")).casefold() for category in data["categories"]}
        for category_name, aliases, default_subcategories in self.UNIVERSE_CATEGORIES:
            category = next(
                (item for item in data["categories"] if str(item.get("name", "")).casefold() in aliases),
                None,
            )
            if category is None:
                category = {"name": category_name, "entries": [], "subcategories": []}
                data["categories"].append(category)
                changed = True
            category.setdefault("entries", [])
            category.setdefault("subcategories", [])
            subcategory_names = {str(item.get("name", "")).casefold() for item in category["subcategories"]}
            for subcategory_name in default_subcategories:
                if subcategory_name.casefold() not in subcategory_names:
                    category["subcategories"].append({"name": subcategory_name, "entries": []})
                    changed = True

        changed = self._migrate_legacy_universe(data) or changed

        entry_ids: dict[str, str] = {}
        for category in data["categories"]:
            entry_containers = [category, *category.get("subcategories", [])]
            for container in entry_containers:
                for entry in container.get("entries", []):
                    entry_name = entry.get("name", "")
                    if "uuid" not in entry:
                        entry["uuid"] = str(uuid4())
                        changed = True
                    if entry_name:
                        entry_ids[entry_name.casefold()] = entry["uuid"]
                        metadata = data["extensions"]["entries"].setdefault(
                            entry_name, self.default_entry_metadata()
                        )
                        for key, value in self.default_entry_metadata().items():
                            metadata.setdefault(key, value.copy() if isinstance(value, (list, dict)) else value)
                        if metadata.get("canon") not in self.CANON_STATUSES:
                            metadata["canon"] = "Confirmado"
                            changed = True

        indexed_relationships = [
            relationship for relationship in data["universe"].get("relationships", [])
            if isinstance(relationship, dict)
        ]
        relationships_by_key = {
            (relationship.get("source_id"), relationship.get("target_id"), relationship.get("type")): relationship
            for relationship in indexed_relationships
        }
        for source_name, metadata in data["extensions"]["entries"].items():
            source_id = entry_ids.get(source_name.casefold())
            for relationship in metadata.get("relationships", []):
                if not isinstance(relationship, dict):
                    continue
                target_name = relationship.get("name", "")
                target_id = entry_ids.get(target_name.casefold())
                relationship_type = relationship.get("type", "")
                key = (source_id, target_id, relationship_type)
                if source_id and target_name:
                    indexed_relationship = {
                        "source_id": source_id,
                        "target_id": target_id,
                        "target_name": target_name,
                        "type": relationship_type,
                        "canon": relationship.get("canon", metadata.get("canon", "Confirmado")),
                    }
                    if key in relationships_by_key:
                        if relationships_by_key[key] != indexed_relationship:
                            relationships_by_key[key].update(indexed_relationship)
                            changed = True
                    else:
                        indexed_relationships.append(indexed_relationship)
                        relationships_by_key[key] = indexed_relationship
                        changed = True
        data["universe"]["relationships"] = indexed_relationships
        return changed

    @staticmethod
    def _category_by_name(data, name):
        return next(
            (category for category in data.get("categories", [])
             if str(category.get("name", "")).casefold() == name.casefold()),
            None,
        )

    @staticmethod
    def _subcategory_by_name(category, name):
        return next(
            (subcategory for subcategory in category.get("subcategories", [])
             if str(subcategory.get("name", "")).casefold() == name.casefold()),
            None,
        )

    def _move_entries(self, source, target, destinations, classifier):
        """Move legacy direct entries into existing factory subcategories."""
        changed = False
        for entry in list(source.get("entries", [])):
            destination_name = classifier(entry.get("name", ""))
            destination = self._subcategory_by_name(target, destination_name)
            if destination is None:
                continue
            destination.setdefault("entries", []).append(entry)
            source["entries"].remove(entry)
            changed = True
        return changed

    def _legacy_content_to_notebook(self, content):
        """Turn labelled legacy prose into individual notebook fields without losing text."""
        content = str(content or "").strip()
        if not content:
            return {}
        field_pattern = re.compile(
            r"(?:^|\n)\s*(?:[-*]\s*)?(?:\*{1,2})?([^:\n*]{2,80})(?:\*{1,2})?\s*:\s*"
            r"(.*?)(?=(?:\n\s*(?:[-*]\s*)?(?:\*{1,2})?[^:\n*]{2,80}(?:\*{1,2})?\s*:\s*)|\Z)",
            re.DOTALL,
        )
        notebook = {}
        matched_spans = []
        for match in field_pattern.finditer(content):
            label = " ".join(match.group(1).split()).strip("* ")
            value = match.group(2).strip()
            if not label or not value:
                continue
            normalised_label = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode().casefold()
            key = self.NOTEBOOK_FIELD_ALIASES.get(label.casefold()) or self.NOTEBOOK_FIELD_ALIASES.get(normalised_label)
            if not key:
                key = re.sub(r"[^a-z0-9]+", "_", normalised_label).strip("_") or "detalhe"
            while key in notebook:
                key += "_extra"
            notebook[key] = value
            matched_spans.append(match.span())
        remaining = field_pattern.sub("", content).strip(" \\n*-")
        if remaining:
            notebook = {"descricao": remaining, **notebook}
        return notebook or {"descricao": content}

    def _populate_notebook_from_legacy_content(self, data, entries):
        metadata_by_name = data.setdefault("extensions", {}).setdefault("entries", {})
        for entry in entries:
            name = entry.get("name", "")
            content = entry.get("content", "")
            if not name or not content:
                continue
            metadata = metadata_by_name.setdefault(name, self.default_entry_metadata())
            existing = metadata.get("notebook", {})
            only_legacy_description = set(existing) == {"descricao"} and existing.get("descricao", "").strip() == content.strip()
            if not existing or only_legacy_description:
                metadata["notebook"] = self._legacy_content_to_notebook(content)

    def _migrate_legacy_universe(self, data):
        """Migrate legacy categories into the standard Juvion hierarchy."""
        legacy_names = {
            "worldbuilding e lugares",
            "sistema de magia & forças singulares",
            "relíquias e armas sagradas",
            "mitologia e história",
        }
        if not any(str(category.get("name", "")).casefold() in legacy_names for category in data.get("categories", [])):
            return False

        changed = False
        characters = self._category_by_name(data, "Personagens")
        if characters and characters.get("entries"):
            changed = self._move_entries(
                characters,
                characters,
                (),
                lambda name: "Coadjuvantes",
            ) or changed

        world_legacy = self._category_by_name(data, "Worldbuilding e Lugares")
        worldbuilding = self._category_by_name(data, "Worldbuilding")
        if world_legacy and worldbuilding:
            changed = self._move_entries(
                world_legacy,
                worldbuilding,
                (),
                lambda name: "Lugares",
            ) or changed

        magic_legacy = self._category_by_name(data, "Sistema de Magia & Forças Singulares")
        systems = self._category_by_name(data, "Sistemas e poderes")
        if magic_legacy and systems:
            changed = self._move_entries(
                magic_legacy,
                systems,
                (),
                lambda name: "Sistema de energia" if "forças singulares" in name.casefold() else "Magia",
            ) or changed

        relic_legacy = self._category_by_name(data, "Relíquias e Armas Sagradas")
        items = self._category_by_name(data, "Itens e artefatos")
        if relic_legacy and items:
            changed = self._move_entries(
                relic_legacy,
                items,
                (),
                lambda name: "Relíquias",
            ) or changed

        history_legacy = self._category_by_name(data, "Mitologia e História")
        history = self._category_by_name(data, "Histórias e eventos")
        if history_legacy and history:
            history.setdefault("entries", []).extend(history_legacy.get("entries", []))
            history_legacy["entries"] = []
            changed = True

        migrated_entries = []
        for category_name in ("Personagens", "Worldbuilding", "Sistemas e poderes", "Itens e artefatos", "Histórias e eventos"):
            category = self._category_by_name(data, category_name)
            if category:
                migrated_entries.extend(category.get("entries", []))
                for subcategory in category.get("subcategories", []):
                    migrated_entries.extend(subcategory.get("entries", []))
        self._populate_notebook_from_legacy_content(data, migrated_entries)

        for category in list(data.get("categories", [])):
            if str(category.get("name", "")).casefold() in legacy_names:
                data["categories"].remove(category)
                changed = True
        return changed

    def _load_data(self) -> dict[str, Any]:
        """
        Load compendium data from the project-specific file, converting legacy formats if needed.

        Returns:
            dict: Compendium data with a 'categories' key containing a list of category objects.
        """
        if not os.path.exists(self._filepath):
            self._ensure_file_exists()

        try:
            with open(self._filepath, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {self._filepath}: {e}. Initializing empty compendium.")
            data = self._default_data()
            self._save_data(data)
        except Exception as e:
            print(f"Error loading compendium data from {self._filepath}: {e}")
            data = self._default_data()
            self._save_data(data)

        # Convert legacy dict format to list of categories
        data.setdefault("categories", [])
        data.setdefault("extensions", {"entries": {}})
        changed = False
        if isinstance(data["categories"], dict):
            new_categories = [
                {"name": cat, "entries": [
                    {"name": name, "content": content, "uuid": str(uuid4())}
                    for name, content in entries.items()
                ]} for cat, entries in data["categories"].items()
            ]
            data["categories"] = new_categories
            changed = True
        changed = self._normalise_data(data) or changed
        if changed:
            self._save_data(data)

        return data

    def load_data(self) -> dict[str, Any]:
        return self._load_data()

    def _save_data(self, compendium_data: dict[str, Any]) -> None:
        """
        Save compendium data to the file.

        Args:
            compendium_data (dict): The compendium data to save.
        """
        try:
            self._normalise_data(compendium_data)
            os.makedirs(os.path.dirname(self._filepath), exist_ok=True)
            with open(self._filepath, "w", encoding="utf-8") as f:
                json.dump(compendium_data, f, indent=2)
            if self.event_bus:
                self.event_bus.notify_updated(self.project_name)
        except Exception as e:
            print(f"Error saving compendium data to {self._filepath}: {e}")

    def save_data(self, compendium_data: dict[str, Any]) -> None:
        self._save_data(compendium_data)

    def get_category(self, category: str) -> list[dict[str, str]]:
        data = self._load_data()
        categories = data.get("categories", [])
        for cat in categories:
            if cat.get("name") == category:
                entries = list(cat.get("entries", []))
                for subcategory in cat.get("subcategories", []):
                    entries.extend(subcategory.get("entries", []))
                return entries
        return []

    def get_characters(self) -> list[str]:
        character_dicts = self.get_category("Personagens") or self.get_category("Characters")
        characters = [d['name'] for d in character_dicts]
        characters.sort()
        return characters

    def get_entry_index(self) -> list[dict[str, str]]:
        """Return a compact index for manuscript links and writing suggestions."""
        entries = []
        for category in self._load_data().get("categories", []):
            category_name = category.get("name", "")
            containers = [(category_name, "", category)]
            containers.extend(
                (category_name, subcategory.get("name", ""), subcategory)
                for subcategory in category.get("subcategories", [])
            )
            for current_category, subcategory_name, container in containers:
                for entry in container.get("entries", []):
                    name = str(entry.get("name", "")).strip()
                    if name:
                        entries.append({
                            "name": name,
                            "content": str(entry.get("content", "")),
                            "category": current_category,
                            "subcategory": subcategory_name,
                        })
        return entries

    def add_entry(self, name: str, category_name: str, subcategory_name: str = "", content: str = "") -> bool:
        """Create a universe entry from a manuscript selection without replacing existing data."""
        name = " ".join(name.split()).strip()
        if not name:
            return False
        data = self._load_data()
        target_category = next(
            (category for category in data.get("categories", [])
             if category.get("name", "").casefold() == category_name.casefold()),
            None,
        )
        if target_category is None:
            return False
        target_container = target_category
        if subcategory_name:
            target_container = next(
                (subcategory for subcategory in target_category.get("subcategories", [])
                 if subcategory.get("name", "").casefold() == subcategory_name.casefold()),
                None,
            )
            if target_container is None:
                return False
        for existing in self.get_entry_index():
            if existing["name"].casefold() == name.casefold():
                return False

        target_container.setdefault("entries", []).append({
            "name": name,
            "content": content.strip(),
            "uuid": str(uuid4()),
        })
        metadata = self.default_entry_metadata()
        if content.strip():
            metadata["notebook"] = {"descricao": content.strip()}
        data.setdefault("extensions", {}).setdefault("entries", {})[name] = metadata
        self._save_data(data)
        return True

    def get_text(self, category: str, entry: str) -> str:
        """
        Retrieve the text content for a given category and entry.

        Args:
            category (str): The category name.
            entry (str): The entry name within the category.

        Returns:
            str: The content of the entry, or a placeholder if not found.
        """
        data = self._load_data()
        categories = data.get("categories", [])
        for cat in categories:
            if cat.get("name") == category:
                containers = [cat, *cat.get("subcategories", [])]
                for container in containers:
                    for e in container.get("entries", []):
                        if e.get("name") == entry:
                            return e.get("content", f"[No content for {entry} in category {category}]")
        return f"[No content for {entry} in category {category}]"

    def parse_references(self, message: str) -> list[str]:
        """
        Parse compendium references from a message by matching entry names.

        Args:
            message (str): The text to search for references.

        Returns:
            list: A list of entry names found in the message.
        """
        filename = self._get_filepath()
        refs = []
        if os.path.exists(filename):
            try:
                with open(filename, encoding="utf-8") as f:
                    compendium = json.load(f)
                names = []
                cats = compendium.get("categories", [])
                if isinstance(cats, dict):
                    names = list(cats.keys())
                elif isinstance(cats, list):
                    for cat in cats:
                        for entry in cat.get("entries", []):
                            names.append(entry.get("name", ""))
                        for subcategory in cat.get("subcategories", []):
                            for entry in subcategory.get("entries", []):
                                names.append(entry.get("name", ""))
                for name in names:
                    if name and re.search(r'\b' + re.escape(name) + r'\b', message, re.IGNORECASE):
                        refs.append(name)
            except Exception as e:
                print(f"Error parsing compendium references from {filename}: {e}")
        return refs

    def add_character(self, name, description) -> None:
        """Add a new character to the compendium.json file."""
        compendium_data = self._load_data()

        # Find or create Characters category
        characters_cat = None
        for cat in compendium_data.get("categories", []):
            if cat.get("name", "").casefold() in {"characters", "personagens"}:
                characters_cat = cat
                break
        if not characters_cat:
            characters_cat = {"name": "Personagens", "entries": [], "subcategories": []}
            compendium_data["categories"].append(characters_cat)

        # Check if character already exists
        for entry in characters_cat.get("entries", []):
            if entry.get("name") == name:
                entry["content"] = description
                break
        else:
            # Add new character entry
            characters_cat["entries"].append({"name": name, "content": description})

        # Ensure extensions section exists
        if "extensions" not in compendium_data:
            compendium_data["extensions"] = {"entries": {}}
        elif "entries" not in compendium_data["extensions"]:
            compendium_data["extensions"]["entries"] = {}

        # Add minimal extended data
        if name not in compendium_data["extensions"]["entries"]:
            compendium_data["extensions"]["entries"][name] = self.default_entry_metadata()

        self._save_data(compendium_data)

    def upsert_data(self, compendium_data: dict[str, Any]) -> None:
        """ Merge compendium_data with the existing compendium content. """
        existing_data = self._load_data()

        # Merge categories
        existing_categories = {cat["name"]: cat for cat in existing_data.get("categories", [])}
        new_categories = compendium_data.get("categories", [])
        for new_cat in new_categories:
            if new_cat["name"] in existing_categories:
                existing_entries = {entry["name"]: entry for entry in existing_categories[new_cat["name"]].get("entries", [])}
                for new_entry in new_cat.get("entries", []):
                    if new_entry["name"] in existing_entries:
                        existing_entries[new_entry["name"]].update(new_entry)
                    else:
                        existing_categories[new_cat["name"]]["entries"].append(new_entry)
            else:
                existing_data["categories"].append(new_cat)

        # Merge extensions
        existing_extensions = existing_data.get("extensions", {}).get("entries", {})
        new_extensions = compendium_data.get("extensions", {}).get("entries", {})
        for key, value in new_extensions.items():
            if key in existing_extensions:
                existing_extensions[key].update(value)
            else:
                existing_extensions[key] = value

        existing_data["extensions"] = {"entries": existing_extensions}

        compendium_data.update(existing_data)
        self._save_data(compendium_data)
