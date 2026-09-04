"""Automated standards compliance and architectural governance test suite.

Proactively validates repository code against:
1. .agents/skills/coding-standards/SKILL.md
2. .agents/skills/zero-trust-security/SKILL.md
3. .agents/skills/architecture-standards/SKILL.md
"""

import ast
import re
from pathlib import Path
from typing import Final

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent.parent
_SRC_DIR: Final[Path] = _REPO_ROOT / "src"
_TESTS_DIR: Final[Path] = _REPO_ROOT / "tests"

_BANNED_EXACT_IDENTIFIERS: Final[frozenset[str]] = frozenset(
    {
        "exc",
        "req",
        "res",
        "err",
        "msg",
        "kw",
        "fw",
        "loc",
        "cid",
        "tok",
        "tok1",
        "tok2",
        "orch_result",
        "eval_result",
        "carrier_ref",
        "bank_ref",
        "std_payload",
    }
)

_BANNED_PREFIX_SUFFIX_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^(req_|res_|err_|msg_|kw_|fw_|cid_|loc_|_req_|_res_|_err_|_msg_|_req$|_res$|_err$|_msg$|_kw$|_fw$|_cid$|_loc$)"
)

_VENDOR_MODEL_NAMES_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b(ollama|whisper|llama|gpt-?4|openai|claude|chatgpt)\b",
    re.IGNORECASE,
)


def test_all_src_modules_define_all() -> None:
    """Verifies that every Python module in src/ explicitly defines __all__."""
    missing_all_modules: list[str] = []

    for file_path in sorted(_SRC_DIR.rglob("*.py")):
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        has_all_export = any(
            (
                isinstance(statement, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id == "__all__"
                    for target in statement.targets
                )
            )
            or (
                isinstance(statement, ast.AnnAssign)
                and isinstance(statement.target, ast.Name)
                and statement.target.id == "__all__"
            )
            for statement in tree.body
        )
        if not has_all_export:
            relative_path = file_path.relative_to(_REPO_ROOT)
            missing_all_modules.append(str(relative_path))

    assert not missing_all_modules, (
        f"The following {len(missing_all_modules)} module(s) in src/ are missing __all__:\n"
        + "\n".join(f"  - {module}" for module in missing_all_modules)
    )


def test_module_constants_annotated_with_final() -> None:
    """Verifies that all module-level UPPER_CASE constants are annotated with typing.Final."""
    unannotated_constants: list[str] = []

    for directory_path in [_SRC_DIR, _TESTS_DIR]:
        for file_path in sorted(directory_path.rglob("*.py")):
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
            for statement in tree.body:
                if isinstance(statement, ast.Assign):
                    for target in statement.targets:
                        if (
                            isinstance(target, ast.Name)
                            and target.id.isupper()
                            and target.id not in ("__ALL__",)
                        ):
                            relative_path = file_path.relative_to(_REPO_ROOT)
                            unannotated_constants.append(
                                f"{relative_path}:{statement.lineno}: Constant '{target.id}' "
                                f"assigned without Final annotation"
                            )
                elif (
                    isinstance(statement, ast.AnnAssign)
                    and isinstance(statement.target, ast.Name)
                    and statement.target.id.isupper()
                    and statement.target.id not in ("__ALL__",)
                ):
                    annotation_text = ast.unparse(statement.annotation)
                    if "Final" not in annotation_text:
                        relative_path = file_path.relative_to(_REPO_ROOT)
                        unannotated_constants.append(
                            f"{relative_path}:{statement.lineno}: Constant "
                            f"'{statement.target.id}' annotated as '{annotation_text}' "
                            f"without typing.Final"
                        )

    assert not unannotated_constants, (
        f"Found {len(unannotated_constants)} constant(s) missing typing.Final annotation:\n"
        + "\n".join(f"  - {item}" for item in unannotated_constants)
    )


def test_no_cryptic_abbreviations() -> None:
    """Verifies that no banned abbreviations are used in variables, parameters, or attributes."""
    abbreviation_violations: list[str] = []

    for directory_path in [_SRC_DIR, _TESTS_DIR]:
        for file_path in sorted(directory_path.rglob("*.py")):
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    all_parameters = list(node.args.args) + list(node.args.kwonlyargs)
                    for parameter in all_parameters:
                        param_name = parameter.arg
                        if (
                            param_name in _BANNED_EXACT_IDENTIFIERS
                            or _BANNED_PREFIX_SUFFIX_PATTERN.search(param_name)
                        ):
                            relative_path = file_path.relative_to(_REPO_ROOT)
                            abbreviation_violations.append(
                                f"{relative_path}:{node.lineno}: Parameter '{param_name}' "
                                f"in function '{node.name}' uses a banned abbreviation"
                            )
                elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    var_name = node.id
                    if (
                        var_name in _BANNED_EXACT_IDENTIFIERS
                        or _BANNED_PREFIX_SUFFIX_PATTERN.search(var_name)
                    ):
                        relative_path = file_path.relative_to(_REPO_ROOT)
                        abbreviation_violations.append(
                            f"{relative_path}:{node.lineno}: Variable assignment '{var_name}' "
                            f"uses a banned abbreviation"
                        )

    assert not abbreviation_violations, (
        f"Found {len(abbreviation_violations)} cryptic abbreviation violation(s):\n"
        + "\n".join(f"  - {item}" for item in abbreviation_violations)
    )


def test_test_suite_mirroring_symmetry() -> None:
    """Verifies 1:1 test file mirroring between src/ and tests/ (Section 6.1)."""
    unmirrored_source_modules: list[str] = []

    for source_file in sorted(_SRC_DIR.rglob("*.py")):
        relative_source = source_file.relative_to(_SRC_DIR)
        if relative_source == Path("__init__.py") or relative_source.name == "__init__.py":
            continue

        expected_test_path = _TESTS_DIR / relative_source.parent / f"test_{relative_source.name}"
        if not expected_test_path.exists():
            source_rel = source_file.relative_to(_REPO_ROOT)
            test_rel = expected_test_path.relative_to(_REPO_ROOT)
            unmirrored_source_modules.append(f"{source_rel} -> missing {test_rel}")

    assert not unmirrored_source_modules, (
        f"Found {len(unmirrored_source_modules)} source file(s) missing corresponding test files:\n"
        + "\n".join(f"  - {item}" for item in unmirrored_source_modules)
    )


def test_no_magic_http_status_codes() -> None:
    """Verifies that HTTPStatus enum is used instead of raw integer status codes."""
    magic_number_violations: list[str] = []

    for directory_path in [_SRC_DIR, _TESTS_DIR]:
        for file_path in sorted(directory_path.rglob("*.py")):
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Compare):
                    is_status_comparison = (
                        isinstance(node.left, ast.Attribute) and node.left.attr == "status_code"
                    ) or (
                        isinstance(node.left, ast.Name)
                        and node.left.id in ("status_code", "http_status")
                    )

                    if is_status_comparison:
                        for comparator in node.comparators:
                            if isinstance(comparator, ast.Constant) and isinstance(
                                comparator.value, int
                            ):
                                relative_path = file_path.relative_to(_REPO_ROOT)
                                magic_number_violations.append(
                                    f"{relative_path}:{node.lineno}: status_code compared with "
                                    f"raw integer {comparator.value} instead of HTTPStatus"
                                )
                elif isinstance(node, ast.Call):
                    for keyword in node.keywords:
                        if (
                            keyword.arg == "status_code"
                            and isinstance(keyword.value, ast.Constant)
                            and isinstance(keyword.value.value, int)
                        ):
                            relative_path = file_path.relative_to(_REPO_ROOT)
                            code_val = keyword.value.value
                            magic_number_violations.append(
                                f"{relative_path}:{node.lineno}: Call keyword "
                                f"status_code={code_val} uses raw integer instead of HTTPStatus"
                            )

    assert not magic_number_violations, (
        f"Found {len(magic_number_violations)} raw HTTP status code integer(s):\n"
        + "\n".join(f"  - {item}" for item in magic_number_violations)
    )


def test_model_agnostic_docstrings() -> None:
    """Verifies that third-party AI vendor/model names are not hardcoded in docstrings/comments."""
    vendor_occurrences: list[str] = []

    for directory_path in [_SRC_DIR, _TESTS_DIR]:
        for file_path in sorted(directory_path.rglob("*.py")):
            if file_path == Path(__file__).resolve():
                continue
            content = file_path.read_text(encoding="utf-8")
            for line_number, line_text in enumerate(content.splitlines(), start=1):
                match = _VENDOR_MODEL_NAMES_PATTERN.search(line_text)
                if match:
                    relative_path = file_path.relative_to(_REPO_ROOT)
                    vendor_occurrences.append(
                        f"{relative_path}:{line_number} [{match.group(0)}]: {line_text.strip()}"
                    )

    assert not vendor_occurrences, (
        f"Found {len(vendor_occurrences)} third-party vendor name(s) in code/comments:\n"
        + "\n".join(f"  - {item}" for item in vendor_occurrences)
    )


def test_direct_enum_comparisons() -> None:
    """Verifies that StrEnum comparisons do not use redundant .value access."""
    redundant_value_comparisons: list[str] = []

    for directory_path in [_SRC_DIR, _TESTS_DIR]:
        for file_path in sorted(directory_path.rglob("*.py")):
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Compare):
                    has_value_attribute = False
                    if isinstance(node.left, ast.Attribute) and node.left.attr == "value":
                        has_value_attribute = True
                    for comparator in node.comparators:
                        if isinstance(comparator, ast.Attribute) and comparator.attr == "value":
                            has_value_attribute = True
                    if has_value_attribute:
                        relative_path = file_path.relative_to(_REPO_ROOT)
                        redundant_value_comparisons.append(
                            f"{relative_path}:{node.lineno}: Redundant .value comparison"
                        )

    assert not redundant_value_comparisons, (
        f"Found {len(redundant_value_comparisons)} redundant .value comparison(s):\n"
        + "\n".join(f"  - {item}" for item in redundant_value_comparisons)
    )


def test_flat_control_flow_in_source() -> None:
    """Verifies flat control flow (no elif or else after return/raise statements in src/)."""
    flat_control_flow_violations: list[str] = []

    for file_path in sorted(_SRC_DIR.rglob("*.py")):
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.If)
                and node.body
                and isinstance(node.body[-1], (ast.Return, ast.Raise))
                and node.orelse
            ):
                relative_path = file_path.relative_to(_REPO_ROOT)
                flat_control_flow_violations.append(
                    f"{relative_path}:{node.lineno}: If-block terminating with "
                    f"return/raise has superfluous elif/else at line {node.orelse[0].lineno}"
                )

    assert not flat_control_flow_violations, (
        f"Found {len(flat_control_flow_violations)} flat control flow violation(s):\n"
        + "\n".join(f"  - {item}" for item in flat_control_flow_violations)
    )
