"""Version-gated PyInstaller CArchive/PYZ inspection and patching.

The module never imports code from a target executable. It decodes marshal data
for CPython 3.11, compares structural fingerprints, and rewrites only PYZ.pyz.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import marshal
import struct
import types
from typing import Iterable, Mapping
import zlib

COOKIE_MAGIC = b"MEI\x0c\x0b\x0a\x0b\x0e"
COOKIE_STRUCT = struct.Struct("!8sIIII64s")
TOC_HEADER_STRUCT = struct.Struct("!iIIIBc")
PYZ_HEADER = b"PYZ\0"
MAGIC = importlib.util.MAGIC_NUMBER
SUPPORTED_PYTHON_VERSION = 311


@dataclass(frozen=True)
class CArchiveEntry:
    record_length: int
    position: int
    compressed_size: int
    raw_size: int
    compressed: bool
    typecode: bytes
    name: str
    name_field: bytes


@dataclass(frozen=True)
class CArchive:
    raw: bytes
    prefix: bytes
    tail: bytes
    archive_start: int
    cookie_offset: int
    package_length: int
    toc_offset: int
    toc_size: int
    python_version: int
    python_library: bytes
    entries: tuple[CArchiveEntry, ...]

    def entry(self, name: str) -> CArchiveEntry:
        matches = [entry for entry in self.entries if entry.name == name]
        if len(matches) != 1:
            raise ValueError(f"expected exactly one CArchive entry {name!r}, found {len(matches)}")
        return matches[0]

    def entry_blob(self, name: str) -> bytes:
        entry = self.entry(name)
        start = self.archive_start + entry.position
        end = start + entry.compressed_size
        return self.raw[start:end]

    def entry_data(self, name: str) -> bytes:
        entry = self.entry(name)
        blob = self.entry_blob(name)
        data = zlib.decompress(blob) if entry.compressed else blob
        if len(data) != entry.raw_size:
            raise ValueError(
                f"CArchive entry {name!r} decoded to {len(data)} bytes, expected {entry.raw_size}"
            )
        return data


@dataclass(frozen=True)
class PyzArchive:
    raw: bytes
    python_magic: bytes
    toc_offset: int
    toc: dict[str, tuple[int, int, int]]
    raw_blobs: dict[str, bytes]

    def code(self, name: str) -> types.CodeType:
        if name not in self.toc:
            raise ValueError(f"PYZ module {name!r} is absent")
        try:
            value = marshal.loads(zlib.decompress(self.raw_blobs[name]))
        except (ValueError, TypeError, zlib.error) as error:
            raise ValueError(f"cannot decode PYZ module {name!r}: {error}") from error
        if not isinstance(value, types.CodeType):
            raise ValueError(f"PYZ module {name!r} did not contain a code object")
        return value


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compile_source(source: bytes | str, filename: str) -> types.CodeType:
    """Compile source without inheriting this tool's future-import flags."""
    return compile(source, filename, "exec", flags=0, dont_inherit=True, optimize=0)


def parse_carchive(data: bytes) -> CArchive:
    cookie_offset = data.rfind(COOKIE_MAGIC)
    if cookie_offset < 0 or cookie_offset + COOKIE_STRUCT.size > len(data):
        raise ValueError("missing or truncated PyInstaller archive cookie")
    magic, package_length, toc_offset, toc_size, python_version, python_library = COOKIE_STRUCT.unpack(
        data[cookie_offset : cookie_offset + COOKIE_STRUCT.size]
    )
    if magic != COOKIE_MAGIC:
        raise ValueError("invalid PyInstaller archive cookie")
    if python_version != SUPPORTED_PYTHON_VERSION:
        raise ValueError(
            f"unsupported PyInstaller Python version {python_version}; expected {SUPPORTED_PYTHON_VERSION}"
        )
    archive_start = cookie_offset + COOKIE_STRUCT.size - package_length
    if archive_start < 0:
        raise ValueError("invalid PyInstaller package length")
    toc_start = archive_start + toc_offset
    toc_end = toc_start + toc_size
    if toc_start < archive_start or toc_end > cookie_offset:
        raise ValueError("CArchive TOC lies outside the embedded package")

    entries: list[CArchiveEntry] = []
    cursor = toc_start
    while cursor < toc_end:
        header_end = cursor + TOC_HEADER_STRUCT.size
        if header_end > toc_end:
            raise ValueError("truncated CArchive TOC entry")
        record_length, position, compressed_size, raw_size, compressed, typecode = TOC_HEADER_STRUCT.unpack(
            data[cursor:header_end]
        )
        if record_length < TOC_HEADER_STRUCT.size or cursor + record_length > toc_end:
            raise ValueError("invalid CArchive TOC record length")
        name_field = data[header_end : cursor + record_length]
        try:
            name = name_field.rstrip(b"\0").decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("CArchive entry name is not UTF-8") from error
        if position + compressed_size > toc_offset:
            raise ValueError(f"CArchive entry {name!r} overlaps the TOC")
        entries.append(
            CArchiveEntry(
                record_length=record_length,
                position=position,
                compressed_size=compressed_size,
                raw_size=raw_size,
                compressed=bool(compressed),
                typecode=typecode,
                name=name,
                name_field=name_field,
            )
        )
        cursor += record_length
    if cursor != toc_end:
        raise ValueError("CArchive TOC did not end on a record boundary")

    archive = CArchive(
        raw=data,
        prefix=data[:archive_start],
        tail=data[cookie_offset + COOKIE_STRUCT.size :],
        archive_start=archive_start,
        cookie_offset=cookie_offset,
        package_length=package_length,
        toc_offset=toc_offset,
        toc_size=toc_size,
        python_version=python_version,
        python_library=python_library,
        entries=tuple(entries),
    )
    archive.entry("PYZ.pyz")
    return archive


def parse_pyz(data: bytes) -> PyzArchive:
    if len(data) < 12 or data[:4] != PYZ_HEADER:
        raise ValueError("invalid or truncated PYZ archive")
    python_magic = data[4:8]
    if python_magic != MAGIC:
        raise ValueError(
            f"PYZ interpreter magic mismatch: {python_magic.hex()} != {MAGIC.hex()}"
        )
    (toc_offset,) = struct.unpack("!i", data[8:12])
    if toc_offset < 12 or toc_offset > len(data):
        raise ValueError("PYZ TOC offset lies outside the archive")
    value = marshal.loads(data[toc_offset:])
    try:
        toc_value = dict(value)
    except (TypeError, ValueError) as error:
        raise ValueError("PYZ TOC is not a mapping or key/value sequence") from error

    toc: dict[str, tuple[int, int, int]] = {}
    raw_blobs: dict[str, bytes] = {}
    for name, entry in toc_value.items():
        if not isinstance(name, str) or not isinstance(entry, tuple) or len(entry) != 3:
            raise ValueError("invalid PYZ TOC entry")
        kind, position, size = entry
        if not all(isinstance(item, int) for item in entry):
            raise ValueError(f"invalid PYZ offsets for {name!r}")
        if position < 12 or size < 0 or position + size > toc_offset:
            raise ValueError(f"PYZ module {name!r} lies outside the data area")
        toc[name] = (kind, position, size)
        raw_blobs[name] = data[position : position + size]
    return PyzArchive(data, python_magic, toc_offset, toc, raw_blobs)


def _fingerprint_value(value):
    if isinstance(value, types.CodeType):
        return (
            "code",
            value.co_name,
            value.co_qualname,
            value.co_argcount,
            value.co_posonlyargcount,
            value.co_kwonlyargcount,
            value.co_nlocals,
            value.co_stacksize,
            value.co_flags,
            value.co_code.hex(),
            _fingerprint_value(value.co_consts),
            value.co_names,
            value.co_varnames,
            value.co_freevars,
            value.co_cellvars,
            value.co_exceptiontable.hex(),
        )
    if isinstance(value, tuple):
        return tuple(_fingerprint_value(item) for item in value)
    if isinstance(value, frozenset):
        return ("frozenset", tuple(sorted(repr(_fingerprint_value(item)) for item in value)))
    return (type(value).__name__, repr(value))


def code_fingerprint(code: types.CodeType) -> str:
    return sha256(repr(_fingerprint_value(code)).encode("utf-8"))


def build_pyz(
    modules: Mapping[str, tuple[int, bytes]],
    *,
    python_magic: bytes,
) -> bytes:
    if len(python_magic) != 4:
        raise ValueError("Python bytecode magic must be four bytes")
    chunks: list[bytes] = []
    toc: dict[str, tuple[int, int, int]] = {}
    position = 12
    for name, (kind, marshalled) in modules.items():
        blob = zlib.compress(marshalled)
        chunks.append(blob)
        toc[name] = (kind, position, len(blob))
        position += len(blob)
    return PYZ_HEADER + python_magic + struct.pack("!i", position) + b"".join(chunks) + marshal.dumps(toc)


def patch_pyz(
    data: bytes,
    replacements: Mapping[str, types.CodeType],
    *,
    expected_fingerprints: Mapping[str, str],
) -> bytes:
    archive = parse_pyz(data)
    for name, expected in expected_fingerprints.items():
        if name not in archive.toc:
            raise ValueError(f"version gate failed: required PYZ module {name!r} is absent")
        actual = code_fingerprint(archive.code(name))
        if actual.lower() != expected.lower():
            raise ValueError(
                f"version gate failed: {name} fingerprint mismatch: {actual} != {expected.lower()}"
            )
    missing_gates = sorted(set(replacements).intersection(archive.toc) - set(expected_fingerprints))
    if missing_gates:
        raise ValueError(
            "refusing to replace existing modules without fingerprints: " + ", ".join(missing_gates)
        )

    chunks: list[bytes] = []
    toc: dict[str, tuple[int, int, int]] = {}
    position = 12
    for name, (kind, _old_position, _old_size) in archive.toc.items():
        if name in replacements:
            blob = zlib.compress(marshal.dumps(replacements[name]))
        else:
            blob = archive.raw_blobs[name]
        chunks.append(blob)
        toc[name] = (kind, position, len(blob))
        position += len(blob)
    for name, code in replacements.items():
        if name in toc:
            continue
        blob = zlib.compress(marshal.dumps(code))
        chunks.append(blob)
        toc[name] = (0, position, len(blob))
        position += len(blob)

    return PYZ_HEADER + archive.python_magic + struct.pack("!i", position) + b"".join(chunks) + marshal.dumps(toc)


def _rebuild_carchive(archive: CArchive, replacement_pyz: bytes) -> bytes:
    data_parts: list[bytes] = []
    toc_parts: list[bytes] = []
    position = 0
    for entry in archive.entries:
        if entry.name == "PYZ.pyz":
            raw_data = replacement_pyz
            blob = zlib.compress(raw_data) if entry.compressed else raw_data
        else:
            blob = archive.entry_blob(entry.name)
            raw_data = archive.entry_data(entry.name)
        data_parts.append(blob)
        toc_parts.append(
            TOC_HEADER_STRUCT.pack(
                entry.record_length,
                position,
                len(blob),
                len(raw_data),
                int(entry.compressed),
                entry.typecode,
            )
            + entry.name_field
        )
        position += len(blob)

    toc = b"".join(toc_parts)
    package_length = position + len(toc) + COOKIE_STRUCT.size
    cookie = COOKIE_STRUCT.pack(
        COOKIE_MAGIC,
        package_length,
        position,
        len(toc),
        archive.python_version,
        archive.python_library,
    )
    return archive.prefix + b"".join(data_parts) + toc + cookie + archive.tail


def patch_executable(
    data: bytes,
    *,
    replacements: Mapping[str, types.CodeType],
    expected_exe_sha256: str,
    expected_module_fingerprints: Mapping[str, str],
) -> tuple[bytes, dict[str, object]]:
    input_hash = sha256(data)
    if input_hash.lower() != expected_exe_sha256.lower():
        raise ValueError(
            f"version gate failed: executable SHA-256 mismatch: {input_hash} != {expected_exe_sha256.lower()}"
        )
    archive = parse_carchive(data)
    original_pyz = archive.entry_data("PYZ.pyz")
    patched_pyz = patch_pyz(
        original_pyz,
        replacements,
        expected_fingerprints=expected_module_fingerprints,
    )
    output = _rebuild_carchive(archive, patched_pyz)
    reparsed = parse_carchive(output)
    reparsed_pyz = parse_pyz(reparsed.entry_data("PYZ.pyz"))
    for name, code in replacements.items():
        if code_fingerprint(reparsed_pyz.code(name)) != code_fingerprint(code):
            raise ValueError(f"post-write verification failed for {name}")

    report: dict[str, object] = {
        "input_sha256": input_hash,
        "output_sha256": sha256(output),
        "python_version": archive.python_version,
        "python_library": archive.python_library.rstrip(b"\0").decode("utf-8", errors="replace"),
        "input_size": len(data),
        "output_size": len(output),
        "archive_tail_size": len(archive.tail),
        "input_pyz_sha256": sha256(original_pyz),
        "output_pyz_sha256": sha256(patched_pyz),
        "replaced_modules": list(replacements),
        "module_fingerprints": {
            name: code_fingerprint(reparsed_pyz.code(name)) for name in replacements
        },
    }
    return output, report


def iter_code_objects(code: types.CodeType, path: str = "") -> Iterable[tuple[str, types.CodeType]]:
    current = f"{path}/{code.co_qualname}"
    yield current, code
    for constant in code.co_consts:
        if isinstance(constant, types.CodeType):
            yield from iter_code_objects(constant, current)


def compare_code_objects(left: types.CodeType, right: types.CodeType) -> list[dict[str, object]]:
    """Return the leaf code-object differences, excluding parent containers."""
    left_map = dict(iter_code_objects(left))
    right_map = dict(iter_code_objects(right))
    changed = {
        path
        for path in set(left_map) | set(right_map)
        if path not in left_map
        or path not in right_map
        or code_fingerprint(left_map[path]) != code_fingerprint(right_map[path])
    }
    leaves = sorted(
        path for path in changed if not any(other.startswith(path + "/") for other in changed)
    )
    result: list[dict[str, object]] = []
    for path in leaves:
        left_code = left_map.get(path)
        right_code = right_map.get(path)
        result.append(
            {
                "path": path,
                "left_name": left_code.co_name if left_code else None,
                "right_name": right_code.co_name if right_code else None,
                "left_fingerprint": code_fingerprint(left_code) if left_code else None,
                "right_fingerprint": code_fingerprint(right_code) if right_code else None,
                "left_names": list(left_code.co_names) if left_code else None,
                "right_names": list(right_code.co_names) if right_code else None,
                "left_constants": [
                    repr(value) for value in left_code.co_consts if not isinstance(value, types.CodeType)
                ] if left_code else None,
                "right_constants": [
                    repr(value) for value in right_code.co_consts if not isinstance(value, types.CodeType)
                ] if right_code else None,
            }
        )
    return result
